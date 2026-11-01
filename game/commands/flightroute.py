"""Route of a flight (WEB-04.4), shared by the web editor and Qt.

The rules of `QFlightWaypointTab`, `QFlightWaypointList` and
`QPredefinedWaypointSelectionComboBox`, and of the waypoint drag on the map. A change of
route moves the times of the flight: callers keep the package TOT and the screens in
step (`game/server/flightroute/routes.py`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, fields, replace
from datetime import datetime
from enum import Enum, unique
from typing import Any, Iterable, Optional, TYPE_CHECKING

from dcs import Point

from game.ato.flightplans.custom import CustomFlightPlan, CustomLayout
from game.ato.flightplans.flightplan import Layout
from game.ato.flightplans.planningerror import PlanningError
from game.ato.flightplans.standard import StandardLayout
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.flighttype import FlightType
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.loadouts import Loadout
from game.theater.controlpoint import ControlPointType
from game.theater.player import Player
from game.threatzones import ThreatZones
from game.utils import Distance, feet, meters
from .errors import CommandError
from .packageflights import ESCORT_TASKS, plannable_tasks

if TYPE_CHECKING:
    from game import Game
    from game.ato.flight import Flight

MIN_ALTITUDE_FT = 0
MAX_ALTITUDE_FT = 40000

#: Target *points* are the exact location of a unit, whereas the target area is only
#: the center of the objective: the latter can move. Landing and divert are changed
#: in the flight settings, takeoff is where the plane is. Moving the bullseye reference
#: only makes it wrong.
FIXED_WAYPOINT_TYPES = frozenset(
    {
        FlightWaypointType.BULLSEYE,
        FlightWaypointType.DIVERT,
        FlightWaypointType.LANDING_POINT,
        FlightWaypointType.TAKEOFF,
        FlightWaypointType.TARGET_POINT,
    }
)

#: On the list of a flight plan but not flown.
NOT_FLOWN_WAYPOINT_TYPES = frozenset(
    {FlightWaypointType.BULLSEYE, FlightWaypointType.DIVERT}
)

#: Waypoint types whose altitude the bulk setter must not touch. Their altitude is
#: tied to something other than the en-route cruise band, so overwriting it with a
#: cruise MSL would break the flight plan:
#:   * Takeoff / pattern / landing points are tied to the airfield.
#:   * Divert and cargo-stop points are alternate landing fields.
#:   * Target points carry the target's own elevation (used for attack geometry).
#:   * Pickup / dropoff zones are ground-level helo landing zones.
#:   * Refuel / recovery-tanker points are tied to the tanker's orbit altitude.
#:   * Bullseye is a fixed map reference, not a flown waypoint.
BULK_ALTITUDE_SKIP_TYPES = frozenset(
    {
        FlightWaypointType.TAKEOFF,
        FlightWaypointType.DESCENT_POINT,
        FlightWaypointType.LANDING_POINT,
        FlightWaypointType.DIVERT,
        FlightWaypointType.CARGO_STOP,
        FlightWaypointType.TARGET_POINT,
        FlightWaypointType.TARGET_GROUP_LOC,
        FlightWaypointType.TARGET_SHIP,
        FlightWaypointType.PICKUP_ZONE,
        FlightWaypointType.DROPOFF_ZONE,
        FlightWaypointType.REFUEL,
        FlightWaypointType.RECOVERY_TANKER,
        FlightWaypointType.BULLSEYE,
    }
)

DEGRADE_REFUSAL = (
    "This change turns the route into a custom flight plan, which no longer respects "
    "the TOTs of the package: confirm it first."
)


def require_waypoint(flight: Flight, index: int) -> FlightWaypoint:
    """The waypoint at this place of the flight plan (0 is the departure), or a 404."""
    waypoints = flight.flight_plan.waypoints
    if not 0 <= index < len(waypoints):
        raise CommandError("This waypoint no longer exists.", status_code=404)
    return waypoints[index]


def is_movable(waypoint: FlightWaypoint) -> bool:
    return waypoint.waypoint_type not in FIXED_WAYPOINT_TYPES


def is_flown(waypoint: FlightWaypoint) -> bool:
    return waypoint.waypoint_type not in NOT_FLOWN_WAYPOINT_TYPES


def _follow_primary_flight(flight: Flight, waypoint: FlightWaypoint) -> None:
    """The waypoints the package shares follow the ones of its primary flight."""
    package = flight.package
    wpts = package.waypoints
    if flight is not package.primary_flight or not wpts:
        return
    if waypoint.waypoint_type is FlightWaypointType.JOIN:
        wpts.join = waypoint.position
    elif waypoint.waypoint_type is FlightWaypointType.SPLIT:
        wpts.split = waypoint.position
    elif waypoint.waypoint_type is FlightWaypointType.REFUEL:
        wpts.refuel = waypoint.position
    elif "INGRESS" in waypoint.waypoint_type.name:
        wpts.ingress = waypoint.position
        wpts.initial = wpts.get_initial_point(
            waypoint.position, package.target.position
        )
    else:
        return
    for other in package.flights:
        if other is flight:
            continue
        for wpt in other.flight_plan.iter_waypoints():
            if wpt.waypoint_type == waypoint.waypoint_type or (
                "INGRESS" in wpt.waypoint_type.name
                and "INGRESS" in waypoint.waypoint_type.name
            ):
                wpt.position = waypoint.position.new_in_same_map(
                    waypoint.position.x, waypoint.position.y
                )
                break


def move_waypoint(flight: Flight, waypoint: FlightWaypoint, position: Point) -> None:
    """Moves a waypoint, and the package's along with its primary flight."""
    if not is_movable(waypoint):
        raise CommandError(f"{waypoint.display_name.strip()} cannot be moved.")
    waypoint.position = position
    _follow_primary_flight(flight, waypoint)


def _altitude(altitude_ft: float) -> Distance:
    if not MIN_ALTITUDE_FT <= altitude_ft <= MAX_ALTITUDE_FT:
        raise CommandError(
            f"An altitude is between {MIN_ALTITUDE_FT} and {MAX_ALTITUDE_FT} ft."
        )
    return feet(altitude_ft)


def set_waypoint_altitude(waypoint: FlightWaypoint, altitude_ft: float) -> None:
    waypoint.alt = _altitude(altitude_ft)


def is_bulk_editable(waypoint: FlightWaypoint) -> bool:
    # Skip pattern waypoints and any AGL/ground-referenced point (takeoff and landing
    # are RADIO, alt 0) so the bulk set only moves the en-route legs.
    if waypoint.waypoint_type in BULK_ALTITUDE_SKIP_TYPES:
        return False
    return waypoint.alt_type != "RADIO"


def default_bulk_altitude(flight: Flight) -> int:
    """The highest en-route altitude already planned, 0 without any."""
    return max(
        (
            round(waypoint.alt.feet)
            for waypoint in flight.flight_plan.waypoints
            if is_bulk_editable(waypoint)
        ),
        default=0,
    )


def set_en_route_altitude(flight: Flight, altitude_ft: float) -> None:
    """One MSL altitude for every en-route waypoint (see `is_bulk_editable`)."""
    altitude = _altitude(altitude_ft)
    for waypoint in flight.flight_plan.waypoints:
        if is_bulk_editable(waypoint):
            waypoint.alt = altitude


def _probe(layout: Layout) -> Layout:
    """A copy to try a layout's own rules on: only its lists of waypoints change."""
    lists: dict[str, Any] = {
        field.name: list(getattr(layout, field.name))
        for field in fields(layout)
        if isinstance(getattr(layout, field.name), list)
    }
    return replace(layout, **lists)


def deletion_degrades(flight: Flight, waypoint: FlightWaypoint) -> bool:
    """Whether deleting this waypoint turns the plan into a custom flight plan."""
    plan = flight.flight_plan
    return not plan.is_custom and not _probe(plan.layout).delete_waypoint(waypoint)


def _degrade_to_custom(flight: Flight) -> CustomLayout:
    """The layout of the flight, as a custom flight plan.

    It no longer respects the TOTs of the package.
    """
    if not flight.flight_plan.is_custom:
        try:
            flight.degrade_to_custom_flight_plan()
        except PlanningError as ex:
            raise CommandError(f"Could not change the route: {ex}") from ex
    plan = flight.flight_plan
    assert isinstance(plan, CustomFlightPlan)
    return plan.layout


def delete_waypoint(
    flight: Flight, waypoint: FlightWaypoint, allow_degrade: bool
) -> None:
    """Removes a waypoint, degrading the plan to a custom one if it must be."""
    plan = flight.flight_plan
    if waypoint is plan.waypoints[0]:
        raise CommandError("The first waypoint of a route cannot be deleted.")
    if plan.layout.delete_waypoint(waypoint):
        return
    if not plan.is_custom and not allow_degrade:
        raise CommandError(DEGRADE_REFUSAL)
    _degrade_to_custom(flight).custom_waypoints.remove(waypoint)


def _insert_nav_after(layout: Layout, index: int) -> bool:
    waypoints = layout.waypoints
    waypoint = waypoints[index]
    following = waypoints[index + 1] if index + 1 < len(waypoints) else None
    if isinstance(layout, CustomLayout):
        # The first waypoint is the departure, out of the custom ones.
        layout.custom_waypoints.insert(
            index, StandardLayout.get_midpoint(waypoint, following)
        )
        return True
    return isinstance(layout, StandardLayout) and layout.add_waypoint(
        waypoint, following
    )


def can_insert_nav_after(flight: Flight, index: int) -> bool:
    return _insert_nav_after(_probe(flight.flight_plan.layout), index)


def insert_nav_after(flight: Flight, index: int) -> None:
    """Inserts a NAV point halfway to the next waypoint, where the plan allows one."""
    require_waypoint(flight, index)
    if not _insert_nav_after(flight.flight_plan.layout, index):
        raise CommandError(
            "A NAV point cannot follow this waypoint: select a different one."
        )


def add_rtb_waypoint(flight: Flight, allow_degrade: bool) -> None:
    """Adds a landing at the arrival base. The plan is custom from then on."""
    if not flight.flight_plan.is_custom and not allow_degrade:
        raise CommandError(DEGRADE_REFUSAL)
    rtb = WaypointBuilder(flight).land(flight.arrival)
    _degrade_to_custom(flight).custom_waypoints.append(rtb)


def predefined_waypoints(
    game: Game,
    player: Player,
    include_frontlines: bool = True,
    include_airbases: bool = True,
    include_enemy: bool = True,
    include_friendly: bool = True,
) -> list[FlightWaypoint]:
    """What "Add waypoint" offers: front lines, strike targets, bases of the theater."""
    # Importing mission generation at module level would import the commands back.
    from game.missiongenerator.frontlineconflictdescription import (
        FrontLineConflictDescription,
    )

    waypoints: list[FlightWaypoint] = []

    if include_frontlines:
        for front_line in game.theater.conflicts():
            position = FrontLineConflictDescription.frontline_position(
                front_line, game.theater, game.settings
            )[0]
            name = f"Frontline {front_line.name} [CAS]"
            waypoints.append(
                FlightWaypoint(
                    name,
                    FlightWaypointType.CUSTOM,
                    position,
                    meters(800),
                    "RADIO",
                    pretty_name=name,
                    description="Frontline",
                )
            )

    for tgo in game.theater.ground_objects:
        for target_idx, target in enumerate(tgo.strike_targets):
            name = f"[{tgo.obj_name}] : {target.name} #{target_idx}"
            friendly = tgo.is_friendly(to_player=player)
            waypoints.append(
                FlightWaypoint(
                    name,
                    (
                        FlightWaypointType.CUSTOM
                        if friendly
                        else FlightWaypointType.TARGET_POINT
                    ),
                    target.position,
                    meters(0),
                    "RADIO",
                    pretty_name=name,
                    targets=[target],
                    obj_name=tgo.obj_name,
                    description=(
                        f"{'Friendly' if friendly else 'Enemy'} unit: {target.name}"
                    ),
                )
            )

    if include_airbases:
        for cp in game.theater.controlpoints:
            friendly = cp.captured == player
            if (friendly and not include_friendly) or (
                not friendly and not include_enemy
            ):
                continue
            if cp.cptype == ControlPointType.AIRCRAFT_CARRIER_GROUP:
                pretty_name = f"{cp.name} (Aircraft Carrier Group)"
            elif cp.cptype == ControlPointType.LHA_GROUP:
                pretty_name = f"{cp.name} (LHA Group)"
            else:
                pretty_name = f"{cp.name} (Airbase)"
            waypoints.append(
                FlightWaypoint(
                    cp.name,
                    FlightWaypointType.CUSTOM,
                    cp.position,
                    meters(0),
                    "RADIO",
                    pretty_name=pretty_name,
                    description=(
                        f"Position of {cp.name} "
                        f"[{'Friendly' if friendly else 'Enemy'} Airbase]"
                    ),
                )
            )

    return waypoints


def select_predefined_waypoints(
    waypoints: Iterable[FlightWaypoint], name: str, same_location: bool
) -> list[FlightWaypoint]:
    """The waypoint of this name, and with `same_location` the others of its object."""
    available = list(waypoints)
    first = next((w for w in available if w.pretty_name == name), None)
    if first is None:
        return []
    selected = [first]
    if same_location and first.obj_name:
        selected.extend(
            w for w in available if w is not first and w.obj_name == first.obj_name
        )
    return selected


def add_predefined_waypoint(
    game: Game, flight: Flight, name: str, same_location: bool
) -> None:
    """Adds a predefined waypoint at the end of the route, as a custom waypoint."""
    selected = select_predefined_waypoints(
        predefined_waypoints(game, flight.coalition.player), name, same_location
    )
    if not selected:
        raise CommandError(f"{name} is no longer available.", status_code=404)
    flight.flight_plan.layout.custom_waypoints.extend(selected)


def recreation_tasks(game: Game, flight: Flight) -> list[FlightType]:
    """The tasks a route can be recreated as, its current one first."""
    tasks = plannable_tasks(
        flight.package.target, game.settings, flight.coalition.player
    )
    return [flight.flight_type] + [t for t in tasks if t is not flight.flight_type]


def recreate_route(game: Game, flight: Flight, task: FlightType) -> None:
    """Plans the route again for this task, which resets its changes.

    Loadouts the player did not customize follow the task. Refused if only escorts
    would remain (`QPackageDialog.package_valid`, checked when the Qt dialog is saved).
    """
    if task not in recreation_tasks(game, flight):
        raise CommandError(f"{task} cannot be flown against this target.")
    if task in ESCORT_TASKS and all(
        other.flight_type in ESCORT_TASKS
        for other in flight.package.flights
        if other is not flight
    ):
        raise CommandError("A package cannot contain only escort flights.")
    original = flight.flight_type
    flight.set_flight_type(task)
    try:
        flight.recreate_flight_plan(dump_debug_info=True)
    except PlanningError as ex:
        flight.set_flight_type(original)
        logging.exception("Could not recreate flight")
        raise CommandError(f"Could not recreate the route: {ex}") from ex
    for member in flight.iter_members():
        if not member.loadout.is_custom:
            member.loadout = Loadout.default_for(flight)


@unique
class WaypointTimeKind(Enum):
    TAKEOFF = "takeoff"
    TOT = "tot"
    DEPART = "depart"
    #: From the travel time since the previous waypoint.
    ESTIMATED = "estimated"


@dataclass(frozen=True)
class WaypointTime:
    time: datetime
    kind: WaypointTimeKind

    def __str__(self) -> str:
        prefix = "Depart " if self.kind is WaypointTimeKind.DEPART else ""
        return f"{prefix}{self.time:%H:%M:%S}"


def waypoint_times(flight: Flight) -> list[Optional[WaypointTime]]:
    """The time of each waypoint of the plan, None when it has none yet."""
    plan = flight.flight_plan
    times: list[Optional[WaypointTime]] = []
    previous: Optional[tuple[FlightWaypoint, datetime]] = None
    for waypoint in plan.waypoints:
        current: Optional[WaypointTime] = None
        if waypoint.waypoint_type == FlightWaypointType.TAKEOFF:
            current = WaypointTime(plan.takeoff_time(), WaypointTimeKind.TAKEOFF)
        elif (tot := plan.tot_for_waypoint(waypoint)) is not None:
            current = WaypointTime(tot, WaypointTimeKind.TOT)
        elif (depart := plan.depart_time_for_waypoint(waypoint)) is not None:
            current = WaypointTime(depart, WaypointTimeKind.DEPART)
        elif previous is not None:
            current = WaypointTime(
                previous[1] + plan.travel_time_between_waypoints(previous[0], waypoint),
                WaypointTimeKind.ESTIMATED,
            )
        times.append(current)
        if current is not None:
            previous = (waypoint, current.time)
    return times


def _air_defenses_covering(flight: Flight, position: Point) -> list[str]:
    opponent = flight.coalition.opponent
    names: dict[str, None] = {}
    for cp in opponent.game.theater.control_points_for(opponent.player):
        for tgo in cp.ground_objects:
            if not tgo.has_aa:
                continue
            distance = meters(tgo.position.distance_to_point(position))
            if any(
                distance < ThreatZones.air_defense_range(group, opponent.game.settings)
                for group in tgo.groups
            ):
                names[tgo.obj_name] = None
    return list(names)


def threat_warning(flight: Flight, index: int, waypoint: FlightWaypoint) -> str | None:
    """Why this waypoint is inside an enemy threat zone, None if it is not."""
    if not is_flown(waypoint):
        return None
    zones = flight.coalition.opponent.threat_zone
    point = ThreatZones.dcs_to_shapely_point(waypoint.position)
    if zones.threatened_by_air_defense(point):
        names = _air_defenses_covering(flight, waypoint.position)
        rings = ", ".join(names) if names else "enemy air defenses"
        return f"Waypoint {index} is inside the threat ring of {rings}."
    if zones.threatened_by_aircraft(point):
        return f"Waypoint {index} is within reach of enemy aircraft."
    return None

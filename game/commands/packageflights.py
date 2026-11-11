"""Flights of a package and auto-create (WEB-04.1), shared by the web editor and Qt.

The rules of `QFlightCreator`, `QPackageDialog.add_flight` and `QAutoCreateDialog`.
They must plan exactly what the Qt dialogs planned: `tests/flightplans` (W16) runs its
scenarios through these functions against unchanged references.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, TYPE_CHECKING

from game.ato.flight import Flight
from game.ato.flightmember import apply_default_player_laser_code
from game.ato.flightplans.planningerror import PlanningError
from game.ato.flightroster import FlightRoster
from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.commander.missionproposals import ProposedFlight, ProposedMission
from game.commander.packagefulfiller import PackageFulfiller
from game.profiling import MultiEventTracer
from .errors import CommandError
from .packages import cancel_or_abort_flight, coalition_of

if TYPE_CHECKING:
    from game import Game
    from game.ato.package import Package
    from game.ato.starttype import StartType
    from game.coalition import Coalition
    from game.dcs.aircrafttype import AircraftType
    from game.settings import Settings
    from game.sim import GameUpdateEvents
    from game.squadrons import AirWing, Squadron
    from game.theater import ControlPoint, MissionTarget
    from game.theater.player import Player

#: A package of these flights only is refused (`QPackageDialog.package_valid`).
ESCORT_TASKS = frozenset({FlightType.ESCORT, FlightType.SEAD_ESCORT})

#: Tasks the auto-create form offers as the main flight of the package.
AUTO_CREATE_PRIMARY_TASKS = frozenset(
    {
        FlightType.STRIKE,
        FlightType.OCA_AIRCRAFT,
        FlightType.OCA_RUNWAY,
        FlightType.DEAD,
        FlightType.ANTISHIP,
        FlightType.BAI,
        FlightType.CAS,
        FlightType.ARMED_RECON,
        FlightType.AIR_ASSAULT,
    }
)

#: Optional flights of the auto-create form with their default size, in form order.
AUTO_CREATE_SUPPORT_TASKS: dict[FlightType, int] = {
    FlightType.TARCAP: 2,
    FlightType.ESCORT: 2,
    FlightType.SEAD_ESCORT: 2,
    FlightType.SEAD: 2,
    FlightType.SEAD_SWEEP: 2,
    FlightType.ARMED_RECON: 2,
    FlightType.REFUELING: 1,
    FlightType.RECOVERY: 1,
}

#: A CAS package does not take these flights.
AUTO_CREATE_EXCLUDED_WITH_CAS = frozenset(
    {FlightType.ESCORT, FlightType.SEAD_ESCORT, FlightType.SEAD}
)

AUTO_CREATE_MIN_COUNT = 1
AUTO_CREATE_MAX_COUNT = 4


def plannable_tasks(
    target: MissionTarget, settings: Settings, player: Player
) -> list[FlightType]:
    """The tasks a flight against this target can have."""
    return [
        task
        for task in target.mission_types(for_player=player)
        # Air Assault only exists with the CTLD plugin.
        if task is not FlightType.AIR_ASSAULT or settings.plugin_option("ctld")
    ]


def can_fly_now(squadron: Squadron, task: FlightType) -> bool:
    """Whether a new flight of this task can come from this squadron."""
    return bool(
        squadron.capable_of(task)
        and squadron.untasked_aircraft
        and squadron.location.runway_is_operational()
    )


def squadrons_for(
    air_wing: AirWing, task: FlightType, aircraft: AircraftType
) -> list[Squadron]:
    """The squadrons of this aircraft type that can fly this task now."""
    return [s for s in air_wing.squadrons_for(aircraft) if can_fly_now(s, task)]


def max_flight_size(squadron: Squadron) -> int:
    return min(squadron.untasked_aircraft, squadron.aircraft.max_group_size)


def new_flight_start_type(
    settings: Settings, squadron: Squadron, task: FlightType, has_players: bool
) -> StartType:
    """A base that dictates its start type wins over the task's default."""
    required = squadron.location.required_aircraft_start_type
    if required is not None:
        return required
    return settings.start_type_for(task, has_players=has_players)


def default_loadout(aircraft: AircraftType, task: FlightType) -> Loadout:
    """The loadout a new flight gets: the first default of the task the aircraft has,
    else its first loadout."""
    loadouts: dict[str, Loadout] = {}
    for loadout in Loadout.iter_for_aircraft(aircraft):
        loadouts.setdefault(loadout.name, loadout)
    for name in Loadout.default_loadout_names_for(task):
        if name in loadouts:
            return loadouts[name]
    for first in loadouts.values():
        return first
    return Loadout.empty_loadout()


def new_flight_error(
    squadron: Squadron,
    size: int,
    divert: Optional[ControlPoint] = None,
    custom_name: Optional[str] = None,
) -> Optional[str]:
    """Why this flight cannot be created, or None."""
    if divert is not None and divert.captured != squadron.player:
        return f"{divert.name} is not owned by your coalition."
    available = squadron.untasked_aircraft
    if not available:
        return f"{squadron} has no aircraft available."
    if size > available:
        return f"{squadron} has only {available} aircraft available."
    if size <= 0:
        return "Flight must have at least one aircraft."
    if custom_name and "|" in custom_name:
        return "Cannot include | in flight name"
    return None


def build_flight(
    game: Game,
    package: Package,
    squadron: Squadron,
    task: FlightType,
    roster: FlightRoster,
    start_type: StartType,
    divert: Optional[ControlPoint] = None,
    custom_name: Optional[str] = None,
    loadout: Optional[Loadout] = None,
) -> Flight:
    """A new flight, not in the package yet. It takes the roster's pilots."""
    flight = Flight(
        package,
        squadron,
        # A bit of a hack to work around the old API. Not actually relevant because
        # the roster is passed explicitly. Needs a refactor.
        roster.max_size,
        task,
        start_type,
        divert,
        custom_name=custom_name,
        roster=roster,
    )
    if loadout is None:
        loadout = default_loadout(flight.unit_type, task)
    for member in flight.iter_members():
        apply_default_player_laser_code(member, game.settings, game.laser_code_registry)
        member.loadout = loadout
    return flight


def plan_flight_in_package(package: Package, flight: Flight, now: datetime) -> None:
    """The flight joins the package and gets its flight plan.

    Raises:
        CommandError: the flight cannot be planned. It left the package again.
    """
    package.add_flight(flight)
    try:
        flight.recreate_flight_plan()
    except PlanningError as ex:
        package.remove_flight(flight)
        raise CommandError(f"Could not create the flight: {ex}") from ex
    if package.auto_asap:
        package.set_tot_asap(now)


def add_flight(
    game: Game,
    package: Package,
    task: FlightType,
    squadron: Squadron,
    size: int,
    now: datetime,
    start_type: Optional[StartType] = None,
) -> Flight:
    """Adds a planned flight (the "Add Flight" form), with the task's default loadout.

    `start_type` None is the default for the task and pilots. A base that dictates
    its start type always wins, whatever was asked.

    An escort needs a flight to escort, which the web editor checks here because it
    has no save step (see `QPackageDialog.package_valid`).
    """
    coalition = coalition_of(game, package)
    if squadron.player != coalition.player:
        raise CommandError("This squadron is not part of the package's coalition.")
    if task not in plannable_tasks(package.target, game.settings, coalition.player):
        raise CommandError(f"{task} cannot be flown against {package.target.name}.")
    if not squadron.capable_of(task):
        raise CommandError(f"{squadron} cannot fly {task}.")
    if not squadron.location.runway_is_operational():
        raise CommandError(f"{squadron.location.name} cannot launch aircraft now.")
    if task in ESCORT_TASKS and all(
        flight.flight_type in ESCORT_TASKS for flight in package.flights
    ):
        raise CommandError("Add the flight to escort first.")
    error = new_flight_error(squadron, size)
    if error is not None:
        raise CommandError(error)
    if size > squadron.aircraft.max_group_size:
        raise CommandError(
            f"A flight of {squadron.aircraft} has at most "
            f"{squadron.aircraft.max_group_size} aircraft."
        )

    roster = FlightRoster(squadron, initial_size=size)
    if start_type is None or squadron.location.required_aircraft_start_type:
        start_type = new_flight_start_type(
            game.settings, squadron, task, roster.player_count > 0
        )
    flight = build_flight(game, package, squadron, task, roster, start_type)
    plan_flight_in_package(package, flight, now)
    return flight


def remove_flight(
    game: Game,
    package: Package,
    flight: Flight,
    events: GameUpdateEvents,
    now: datetime,
) -> None:
    """The flight leaves the package, or aborts if it is under way.

    Refused if only escorts would remain: they go first, or the whole package.
    """
    if flight.state.cancelable and flight.flight_type not in ESCORT_TASKS:
        others = [other for other in package.flights if other is not flight]
        if others and all(other.flight_type in ESCORT_TASKS for other in others):
            raise CommandError(
                "A package cannot contain only escort flights: remove them first, "
                "or delete the package."
            )
    cancel_or_abort_flight(coalition_of(game, package), package, flight, events)
    if package.auto_asap:
        package.set_tot_asap(now)
    game.compute_unculled_zones(events)


def auto_create_primary_tasks(
    target: MissionTarget, player: Player
) -> list[FlightType]:
    return [
        task
        for task in target.mission_types(player)
        if task in AUTO_CREATE_PRIMARY_TASKS
    ]


def auto_create_default_count(target: MissionTarget) -> int:
    """Size of the main flight: half the targets, within the form's limits."""
    targets = len(target.strike_targets)
    if not targets:
        return AUTO_CREATE_MAX_COUNT
    return max(AUTO_CREATE_MIN_COUNT, min(AUTO_CREATE_MAX_COUNT, targets // 2))


def auto_create_aircraft(
    air_wing: AirWing, target: MissionTarget, task: FlightType
) -> dict[AircraftType, int]:
    """The aircraft the auto-planner can task now, best first, each with the largest
    flight one of its squadrons can fill.

    It asks the question `PackageBuilder.plan_flight` asks: a type whose squadrons
    are kept off auto-planning for this task, have no pilot left, or own nothing yet
    (aircraft on order are delivered next turn) is not offered, and no flight is
    offered larger than a squadron can fill.

    An escort has to match the main flight, known only once it is planned: both
    the escorts of a helicopter flight and those of a fixed wing flight are listed.
    """
    sizes: dict[AircraftType, int] = {}
    for size in range(AUTO_CREATE_MIN_COUNT, AUTO_CREATE_MAX_COUNT + 1):
        for heli in (False, True) if task in ESCORT_TASKS else (False,):
            for squadron in air_wing.best_squadrons_for(
                target, task, size, heli, this_turn=True, ignore_range=True
            ):
                # Sizes go up: the first pass sets the order, the last one the size.
                sizes[squadron.aircraft] = size
    return sizes


def plan_auto_package(
    game: Game,
    coalition: Coalition,
    target: MissionTarget,
    flights: Iterable[ProposedFlight],
    now: datetime,
) -> Optional[Package]:
    """A new ASAP package planned by the auto-planner, not in the ATO, or None when
    there are not enough aircraft or pilots."""
    fulfiller = PackageFulfiller(
        coalition, game.theater, game.db.flights, game.settings
    )
    with MultiEventTracer() as tracer:
        with tracer.trace("Auto-plan package"):
            package = fulfiller.plan_mission(
                ProposedMission(target, list(flights), asap=True),
                1,
                now,
                tracer,
                ignore_range=True,
            )
    if package is not None:
        package.set_tot_asap(now)
    return package


def _auto_create_error(
    flights: list[ProposedFlight], primary_tasks: list[FlightType]
) -> Optional[str]:
    """What the widgets of the Qt dialog made impossible."""
    if not flights or flights[0].task not in primary_tasks:
        return "Choose the main task of the package."
    primary, support = flights[0], flights[1:]
    if any(flight.task not in AUTO_CREATE_SUPPORT_TASKS for flight in support):
        return "This flight cannot be auto-created."
    if primary.task is FlightType.CAS and any(
        flight.task in AUTO_CREATE_EXCLUDED_WITH_CAS for flight in support
    ):
        return "A CAS package takes no Escort, SEAD Escort or SEAD flight."
    if any(
        not AUTO_CREATE_MIN_COUNT <= flight.num_aircraft <= AUTO_CREATE_MAX_COUNT
        for flight in flights
    ):
        return (
            f"A flight has {AUTO_CREATE_MIN_COUNT} to {AUTO_CREATE_MAX_COUNT} aircraft."
        )
    return None


def auto_create(
    game: Game, package: Package, flights: list[ProposedFlight], now: datetime
) -> Package:
    """Fills an empty package through the auto-planner. `flights[0]` is the main one.

    The planner builds its own package, which takes the place of the empty one in the
    ATO, with its id and name: the editor stays on the same package.
    """
    if package.flights:
        raise CommandError("Auto-create needs an empty package.")
    coalition = coalition_of(game, package)
    error = _auto_create_error(
        flights, auto_create_primary_tasks(package.target, coalition.player)
    )
    if error is not None:
        raise CommandError(error)
    planned = plan_auto_package(game, coalition, package.target, flights, now)
    if planned is None:
        raise CommandError(
            "Auto-create package failed due to insufficient aircraft and/or pilots."
        )
    planned.id = package.id
    planned.custom_name = package.custom_name
    planned.frequency = package.frequency
    packages = coalition.ato.packages
    packages[packages.index(package)] = planned
    return planned

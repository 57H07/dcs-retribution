"""Squadrons and pilots of the air wing (WEB-03).

The rules of the Qt `SquadronDialog`, shared with the web air wing screen. Aircraft
orders and expedited repairs have their own commands (`aircraftorders`, `repairs`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator, Optional, TYPE_CHECKING
from uuid import UUID

from game.ato.flightplans.custom import CustomFlightPlan
from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.squadrons.pilot import PilotStatus
from game.squadrons.transferparking import transfer_parking
from game.theater.controlpoint import ParkingType
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight
    from game.sim import GameUpdateEvents
    from game.squadrons import Pilot, Squadron
    from game.theater import ControlPoint


def find_squadron(game: Game, squadron_id: UUID) -> Optional[Squadron]:
    """The squadron of either coalition with this id, or None."""
    for coalition in game.coalitions:
        for squadron in coalition.air_wing.iter_squadrons():
            if squadron.id == squadron_id:
                return squadron
    return None


def find_pilot(squadron: Squadron, pilot_id: UUID) -> Optional[Pilot]:
    return next((p for p in squadron.current_roster if p.id == pilot_id), None)


# --- Tasks ---------------------------------------------------------------------


def flight_type_named(name: str) -> FlightType:
    """The `FlightType` with this value.

    Raises:
        CommandError: no such task.
    """
    try:
        return FlightType(name)
    except ValueError:
        raise CommandError(f"{name} is not a mission type.")


def _require_capable(squadron: Squadron, task: FlightType) -> None:
    if not squadron.capable_of(task):
        raise CommandError(
            f"The {squadron.aircraft.display_name} cannot fly {task.value}."
        )


def set_primary_task(squadron: Squadron, task: FlightType) -> None:
    """Raises CommandError when the aircraft cannot fly this task."""
    _require_capable(squadron, task)
    squadron.primary_task = task


def set_auto_assignable(squadron: Squadron, task: FlightType, enabled: bool) -> None:
    """Allows the autoplanner to use the squadron for this task, or not.

    Raises:
        CommandError: the aircraft cannot fly this task.
    """
    _require_capable(squadron, task)
    if enabled:
        squadron.auto_assignable_mission_types.add(task)
    else:
        squadron.auto_assignable_mission_types.discard(task)


# --- Liveries ------------------------------------------------------------------

LIVERY_SET_TEXT = "Use livery-set from squadron's yaml"
LIVERY_OVERRIDES_TEXT = "Use livery overrides"


@dataclass(frozen=True)
class LiveryChoice:
    label: str
    #: DCS livery id; None for the squadron's set and the faction's overrides.
    livery_id: Optional[str]
    use_livery_set: bool
    selected: bool


def livery_choices(squadron: Squadron) -> list[LiveryChoice]:
    """The liveries the squadron may use; empty when DCS knows none for this aircraft.

    Exactly one is selected, unless the list is empty. A livery unknown to the faction
    falls back on the default livery of the aircraft.
    """
    aircraft = squadron.aircraft
    faction = squadron.coalition.faction
    country = faction.country.shortname
    liveries = {
        livery
        for livery in aircraft.dcs_unit_type.iter_liveries()
        if livery.countries is None
        or country in livery.countries
        or country in ["BLUE", "RED"]
    }
    ids = {livery.id.lower() for livery in liveries}
    current = squadron.livery.lower() if squadron.livery else None
    if current not in ids:
        current = None
    use_set = bool(squadron.livery_set) and squadron.use_livery_set
    if current is None and not squadron.livery_set and aircraft.default_livery:
        current = aircraft.default_livery.lower()

    overrides = [x for x in faction.liveries_overrides.get(aircraft, []) if x in ids]
    choices: list[LiveryChoice] = []
    if squadron.livery_set:
        choices.append(LiveryChoice(LIVERY_SET_TEXT, None, True, False))
    if overrides:
        choices.append(LiveryChoice(LIVERY_OVERRIDES_TEXT, None, False, False))
    choices.extend(
        LiveryChoice(
            livery.name,
            livery.id,
            False,
            not use_set and current == livery.id.lower(),
        )
        for livery in sorted(liveries)
    )
    if not choices or any(c.selected for c in choices):
        return choices
    # The squadron's set, the overrides, or the first livery when nothing matched.
    first = choices[0]
    return [
        LiveryChoice(first.label, first.livery_id, first.use_livery_set, True),
        *choices[1:],
    ]


def apply_livery(
    squadron: Squadron, livery_id: Optional[str], use_livery_set: bool
) -> None:
    squadron.livery = livery_id
    squadron.use_livery_set = use_livery_set


def set_squadron_livery(
    squadron: Squadron, livery_id: Optional[str], use_livery_set: bool
) -> None:
    """Applies one of the `livery_choices` of the squadron.

    Raises:
        CommandError: not a choice of this squadron.
    """
    if not any(
        c.livery_id == livery_id and c.use_livery_set == use_livery_set
        for c in livery_choices(squadron)
    ):
        raise CommandError(f"{squadron.name} cannot use this livery.")
    apply_livery(squadron, livery_id, use_livery_set)


# --- Transfers -----------------------------------------------------------------


@dataclass(frozen=True)
class TransferDestination:
    control_point: ControlPoint
    #: Free parking slots for the squadron's aircraft, ignoring the squadron.
    room: int
    #: Why the squadron cannot go there now; None when it can.
    refusal: Optional[str]
    #: Other squadrons expected there that do not all fit.
    overflow: list[Squadron] = field(default_factory=list)


def room_at_base(squadron: Squadron) -> int:
    return squadron.location.unclaimed_parking(ParkingType().from_squadron(squadron))


def transfer_destinations(squadron: Squadron) -> list[TransferDestination]:
    """The friendly bases to offer, by name; a base without room says so."""
    size = squadron.expected_size_next_turn
    parking_type = ParkingType().from_squadron(squadron)
    destinations = []
    theater = squadron.coalition.game.theater
    for cp in sorted(theater.control_points_for(squadron.player), key=str):
        if cp == squadron.location or not cp.can_operate(squadron.aircraft):
            continue
        parking = transfer_parking(squadron, cp)
        if (
            squadron.destination is not cp
            and cp.unclaimed_parking(parking_type) < size
            and parking.room < size
        ):
            continue
        refusal = None
        if parking.room < squadron.owned_aircraft or parking.room == 0:
            if squadron.owned_aircraft == 0 and parking.room == 0:
                refusal = "no fitting slots found"
            else:
                missing = squadron.owned_aircraft - parking.room
                refusal = f"{missing} additional slots required"
        destinations.append(
            TransferDestination(cp, parking.room, refusal, parking.overflow)
        )
    return destinations


def _ferry_flights(squadron: Squadron) -> Iterator[Flight]:
    for package in squadron.coalition.ato.packages:
        for flight in package.flights:
            if flight.squadron == squadron and flight.flight_type is FlightType.FERRY:
                yield flight


def _relocate_instantly(
    squadron: Squadron, destination: ControlPoint, events: GameUpdateEvents
) -> None:
    """The `enable_transfer_cheat` setting: the squadron is there at once."""
    squadron.relocate_to(destination)
    for flight in squadron.flight_db.objects.values():
        if flight.squadron != squadron:
            continue
        if isinstance(flight.flight_plan, CustomFlightPlan):
            for waypoint in flight.flight_plan.waypoints:
                if waypoint.waypoint_type == FlightWaypointType.LANDING_POINT:
                    waypoint.control_point = destination
                    waypoint.position = destination.position
                    break
        flight.recreate_flight_plan()
        events.update_flight(flight)


def _plan_transfer(
    squadron: Squadron,
    destination: ControlPoint,
    now: datetime,
    events: GameUpdateEvents,
) -> None:
    found = next(
        (
            option
            for option in transfer_destinations(squadron)
            if option.control_point == destination
        ),
        None,
    )
    if found is None:
        raise CommandError(f"{squadron.name} cannot transfer to {destination.name}.")
    if found.refusal is not None:
        raise CommandError(
            f"{squadron.name} cannot transfer to {destination.name}: {found.refusal}."
        )
    if squadron.settings.enable_transfer_cheat:
        _relocate_instantly(squadron, destination, events)
        return
    previous_ferries = list(_ferry_flights(squadron))
    try:
        squadron.plan_relocation(destination, now)
    except RuntimeError as ex:
        raise CommandError(str(ex))
    for flight in previous_ferries:
        events.delete_flight(flight)
    for flight in _ferry_flights(squadron):
        events.new_flight(flight)


def transfer_squadron(
    squadron: Squadron,
    destination: Optional[ControlPoint],
    now: datetime,
    events: GameUpdateEvents,
) -> None:
    """Orders the squadron to a base next turn, or cancels the order.

    Args:
        destination: None or the current base cancels a transfer in progress.
        now: simulation time, for the TOT of the ferry flights.

    Raises:
        CommandError: not a destination of `transfer_destinations`, no room there,
            or no room to stay at the current base.
    """
    origin = squadron.location
    previous = squadron.destination
    if destination is None or destination == origin:
        if previous is None:
            return
        ferries = list(_ferry_flights(squadron))
        try:
            squadron.cancel_relocation()
        except RuntimeError as ex:
            raise CommandError(str(ex))
        for flight in ferries:
            events.delete_flight(flight)
    elif destination == previous:
        return
    else:
        _plan_transfer(squadron, destination, now, events)
        events.update_control_point(destination)
    events.update_control_point(origin)
    if previous is not None:
        events.update_control_point(previous)


# --- Pilots --------------------------------------------------------------------


def player_flag_refusal(squadron: Squadron, pilot: Pilot) -> Optional[str]:
    """Why this pilot cannot be switched between player and AI, or None."""
    if not squadron.aircraft.flyable:
        return f"The {squadron.aircraft.display_name} is not flyable."
    if not pilot.alive:
        return f"{pilot.name} is dead."
    if pilot.prisoner_of_war:
        return f"{pilot.name} is a prisoner of war."
    return None


def set_pilot_player(
    squadron: Squadron, pilot: Pilot, player: bool, events: GameUpdateEvents
) -> None:
    """Makes the pilot a player or an AI; their flights change client count.

    Raises:
        CommandError: see `player_flag_refusal`.
    """
    refusal = player_flag_refusal(squadron, pilot)
    if refusal is not None:
        raise CommandError(refusal)
    pilot.player = player
    for package in squadron.coalition.ato.packages:
        for flight in package.flights:
            if any(p is pilot for p in flight.roster.iter_pilots()):
                events.update_flight(flight)


def leave_refusal(squadron: Squadron, pilot: Pilot) -> Optional[str]:
    """Why the leave of this pilot cannot change, or None."""
    if pilot.status not in (PilotStatus.Active, PilotStatus.OnLeave):
        return f"{pilot.name} is not on active duty: {pilot.status.value.lower()}."
    if pilot.on_leave and not squadron.has_unfilled_pilot_slots:
        return f"{squadron.name} is full: {pilot.name} cannot return from leave."
    return None


def set_pilot_on_leave(squadron: Squadron, pilot: Pilot, on_leave: bool) -> None:
    """Sends the pilot on leave, or back from it.

    Raises:
        CommandError: see `leave_refusal`.
    """
    if on_leave == pilot.on_leave:
        return
    refusal = leave_refusal(squadron, pilot)
    if refusal is not None:
        raise CommandError(refusal)
    if on_leave:
        squadron.send_on_leave(pilot)
    else:
        squadron.return_from_leave(pilot)


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise CommandError("A pilot needs a name.")
    return cleaned


def rename_pilot(pilot: Pilot, name: str) -> None:
    """Raises CommandError for a dead pilot or an empty name."""
    if not pilot.alive:
        raise CommandError(f"{pilot.name} is dead.")
    pilot.name = _clean_name(name)


def new_pilot_refusal(squadron: Squadron) -> Optional[str]:
    """Why no player pilot can join this squadron, or None."""
    if not squadron.aircraft.flyable:
        return f"The {squadron.aircraft.display_name} is not flyable."
    if not squadron.has_unfilled_pilot_slots:
        return f"{squadron.name} is full."
    return None


def create_player_pilot(squadron: Squadron, name: str) -> Pilot:
    """Adds the player's own pilot to the squadron: their career starts now.

    Raises:
        CommandError: see `new_pilot_refusal`, or an empty name.
    """
    refusal = new_pilot_refusal(squadron)
    if refusal is not None:
        raise CommandError(refusal)
    return squadron.create_player_pilot(_clean_name(name))

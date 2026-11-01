"""General settings and pilots of a flight (WEB-04.2), shared by the web editor and Qt.

The rules of `qt_ui/windows/mission/flight/settings/` and `QCallsignWidget`. A change
that must keep the plan the engine makes for the same input goes through the same
engine calls as those widgets: `tests/flightplans` (W16) stays unchanged.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from game.ato.closestairfields import ClosestAirfields
from game.ato.flight import Flight
from game.ato.flightmember import apply_default_player_laser_code
from game.ato.flightplans.planningerror import PlanningError
from game.radio.CallsignContainer import Callsign, CallsignContainer
from game.theater import OffMapSpawn
from game.transfers import Airlift, airlift_squadrons, reassign_airlift
from game.utils import nautical_miles
from .errors import CommandError
from .packageflights import new_flight_start_type
from .squadrons import set_pilot_player

if TYPE_CHECKING:
    from game.ato.package import Package
    from game.ato.starttype import StartType
    from game.dcs.aircrafttype import AircraftType
    from game.sim import GameUpdateEvents
    from game.squadrons import Pilot, Squadron
    from game.theater import ControlPoint

#: What the Qt dialog allows for the number after a callsign name.
CALLSIGN_MIN_NUMBER = 1
CALLSIGN_MAX_NUMBER = 9

#: The offset field reads minutes and seconds.
MAX_TOT_OFFSET = timedelta(minutes=59, seconds=59)

#: A replacement flight is diverted within this range of the target.
DIVERT_LIMIT_NM = 150


def require_not_started(flight: Flight) -> None:
    """A flight under way can only be aborted."""
    if not flight.state.cancelable:
        raise CommandError("This flight is under way: it can only be aborted.")


def _update_tot(package: Package, now: datetime) -> None:
    if package.auto_asap:
        package.set_tot_asap(now)


def default_start_type(flight: Flight) -> StartType:
    """What the flight starts as with its current pilots."""
    return new_flight_start_type(
        flight.coalition.game.settings,
        flight.squadron,
        flight.flight_type,
        flight.roster.player_count > 0,
    )


def reconcile_player_laser_codes(flight: Flight) -> None:
    """AI members give their own laser code back; players get the campaign default."""
    game = flight.coalition.game
    for member in flight.iter_members():
        if not member.is_player and member.tgp_laser_code is not None:
            member.release_tgp_laser_code()
        elif member.is_player and member.tgp_laser_code is None:
            apply_default_player_laser_code(
                member, game.settings, game.laser_code_registry
            )


def _pilots_changed(flight: Flight, now: datetime) -> None:
    """Laser codes follow the players, and the start type goes back to its default,
    as a player flight has a default of its own."""
    reconcile_player_laser_codes(flight)
    flight.start_type = default_start_type(flight)
    _update_tot(flight.package, now)


# --- Slots ----------------------------------------------------------------------


def max_flight_resize(flight: Flight) -> int:
    """The most aircraft this flight can have: its own, plus what its squadron has."""
    return max(
        flight.count,
        min(
            flight.count + flight.squadron.untasked_aircraft,
            flight.unit_type.max_group_size,
        ),
    )


def resize_flight(flight: Flight, size: int, now: datetime) -> None:
    require_not_started(flight)
    if size < 1:
        raise CommandError("Flight must have at least one aircraft.")
    if size > max_flight_resize(flight):
        raise CommandError(
            f"This flight can have at most {max_flight_resize(flight)} aircraft."
        )
    if size == flight.count:
        return
    flight.resize(size)
    _pilots_changed(flight, now)


def set_flight_pilot(
    flight: Flight, slot: int, pilot: Optional[Pilot], now: datetime
) -> None:
    """Puts this pilot, or nobody, in this slot of the flight.

    The pilot must be free. The previous one goes back to the squadron.
    """
    require_not_started(flight)
    _require_slot(flight, slot)
    if pilot is flight.roster.pilot_at(slot):
        return
    if pilot is not None and not any(
        pilot is free for free in flight.squadron.available_pilots
    ):
        raise CommandError(f"{pilot.name} is not available.")
    flight.set_pilot(slot, pilot)
    _pilots_changed(flight, now)


def set_flight_slot_player(
    flight: Flight, slot: int, player: bool, events: GameUpdateEvents, now: datetime
) -> None:
    """Makes the pilot of this slot a player or an AI, like the air wing screen."""
    require_not_started(flight)
    _require_slot(flight, slot)
    pilot = flight.roster.pilot_at(slot)
    if pilot is None:
        raise CommandError("Assign a pilot to this slot first.")
    set_pilot_player(flight.squadron, pilot, player, events)
    _pilots_changed(flight, now)


def _require_slot(flight: Flight, slot: int) -> None:
    if not 0 <= slot < flight.count:
        raise CommandError("This flight has no such slot.", status_code=404)


# --- Squadron --------------------------------------------------------------------


def flight_squadron_candidates(flight: Flight) -> list[Squadron]:
    """The other squadrons this flight can move to: all that can launch it now.

    A transfer flight must keep serving its pickup and drop-off. Any Transport-capable
    squadron may take it, so the player can move it to a squadron kept off auto-planning
    and fly it.
    """
    air_wing = flight.coalition.air_wing
    cargo = flight.cargo
    candidates: list[Squadron]
    if cargo is not None and isinstance(cargo.transport, Airlift):
        candidates = airlift_squadrons(
            air_wing, cargo, cargo.transport.destination, flight.count
        )
    else:
        candidates = air_wing.best_squadrons_for(
            flight.package.target,
            flight.flight_type,
            flight.roster.max_size,
            flight.is_helo,
            True,
            ignore_range=True,
        )
    return [squadron for squadron in candidates if squadron is not flight.squadron]


def _replacement_divert(
    flight: Flight, aircraft: AircraftType, arrival: ControlPoint
) -> Optional[ControlPoint]:
    """The closest friendly field near the target the new squadron can divert to."""
    player = flight.coalition.player
    closest = ClosestAirfields(
        flight.package.target,
        list(flight.coalition.game.theater.control_points_for(player)),
    )
    for airfield in closest.operational_airfields_within(
        nautical_miles(DIVERT_LIMIT_NM)
    ):
        if (
            airfield.captured == player
            and airfield != arrival
            and airfield.can_operate(aircraft)
            and not isinstance(airfield, OffMapSpawn)
        ):
            return airfield
    return None


def change_flight_squadron(flight: Flight, squadron: Squadron, now: datetime) -> Flight:
    """A new flight of this squadron takes the place of this one in the package.

    Like the Qt editor: it keeps its size, task, start type, radio and cargo, and gets
    new pilots, its aircraft's default loadout, a new divert field and a new flight
    plan. It also keeps its name and, when the new aircraft has it, its callsign. A
    base that dictates its start type wins.

    Raises:
        CommandError: the squadron cannot take it, or the flight cannot be planned, in
            which case nothing changed.
    """
    require_not_started(flight)
    if not any(squadron is other for other in flight_squadron_candidates(flight)):
        raise CommandError(f"{squadron} cannot take this flight.")
    package = flight.package
    replacement = Flight(
        package,
        squadron,
        flight.count,
        flight.flight_type,
        squadron.location.required_aircraft_start_type or flight.start_type,
        _replacement_divert(flight, squadron.aircraft, squadron.location),
        custom_name=flight.custom_name,
        frequency=flight.frequency,
        cargo=flight.cargo,
        channel=flight.tacan,
        callsign_tcn=flight.tcn_name,
    )
    callsign = flight.callsign
    if callsign is not None and callsign.name in replacement.available_callsigns:
        replacement.callsign = callsign

    # Keep the transfer attached, otherwise deleting the old flight drops its Airlift
    # and the cargo is neither delivered nor generated.
    reassign_airlift(flight, replacement)
    package.add_flight(replacement)
    try:
        replacement.recreate_flight_plan()
    except PlanningError as ex:
        reassign_airlift(replacement, flight)
        package.remove_flight(replacement)
        raise CommandError(f"Could not plan the flight: {ex}") from ex

    # It stays where it was in the list of the package.
    index = package.flights.index(flight)
    package.remove_flight(flight)
    package.flights.remove(replacement)
    package.flights.insert(index, replacement)

    reconcile_player_laser_codes(replacement)
    _update_tot(package, now)
    return replacement


# --- Start, divert, offset --------------------------------------------------------


def set_flight_start_type(flight: Flight, start_type: StartType, now: datetime) -> None:
    require_not_started(flight)
    required = flight.departure.required_aircraft_start_type
    if required is not None and start_type is not required:
        raise CommandError(
            f"A flight from {flight.departure.name} starts as {required.value}."
        )
    flight.start_type = start_type
    _update_tot(flight.package, now)


def divert_options(flight: Flight) -> list[ControlPoint]:
    """The friendly fields this aircraft can land at, by name."""
    return sorted(
        (
            cp
            for cp in flight.coalition.game.theater.controlpoints
            if cp.captured == flight.coalition.player
            and cp.can_operate(flight.unit_type)
        ),
        key=lambda cp: cp.name,
    )


def set_flight_divert(flight: Flight, divert: Optional[ControlPoint]) -> None:
    """Changes the divert field, which replans the flight.

    Raises:
        CommandError: the field is not an option, or the flight cannot be planned, in
            which case it keeps its divert field.
    """
    require_not_started(flight)
    old_divert = flight.divert
    if divert == old_divert:
        return
    if divert is not None and divert not in divert_options(flight):
        raise CommandError(f"This flight cannot divert to {divert.name}.")
    flight.divert = divert
    try:
        flight.recreate_flight_plan()
    except PlanningError as ex:
        flight.divert = old_divert
        raise CommandError(f"Could not update the flight plan: {ex}") from ex


def set_flight_tot_offset(flight: Flight, offset: timedelta, now: datetime) -> None:
    """Offset of the flight's TOT from the package's: negative is ahead of it."""
    require_not_started(flight)
    if abs(offset) > MAX_TOT_OFFSET:
        raise CommandError("The TOT offset is 59:59 at most, ahead or behind.")
    flight.flight_plan.tot_offset = offset
    _update_tot(flight.package, now)


# --- Name and callsign -------------------------------------------------------------


def set_flight_custom_name(flight: Flight, name: str) -> None:
    """Refused with a | in it. An empty name removes it."""
    if "|" in name:
        raise CommandError("Cannot include | in flight name")
    flight.custom_name = name.strip() or None


def set_callsign(container: CallsignContainer, name: str, number: int) -> None:
    """Sets the callsign of a flight or another group that can choose one."""
    if name not in container.available_callsigns:
        raise CommandError(f"{name} is not an available callsign.")
    if not CALLSIGN_MIN_NUMBER <= number <= CALLSIGN_MAX_NUMBER:
        raise CommandError(
            f"The callsign number is {CALLSIGN_MIN_NUMBER} to {CALLSIGN_MAX_NUMBER}."
        )
    container.callsign = Callsign(name, number)


def reset_callsign(container: CallsignContainer) -> None:
    """Back to an automatic callsign."""
    container.callsign = None

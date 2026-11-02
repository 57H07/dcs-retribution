"""Commands of the General and Pilots tabs of a flight (WEB-04.2). See
`docs/dev/api-commands.md` section 8a: each answers the whole package."""

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends

from game import Game
from game.ato import Flight, Package
from game.commands import CommandError
from game.commands.flightsettings import (
    change_flight_squadron,
    reset_callsign,
    resize_flight,
    set_callsign,
    set_flight_custom_name,
    set_flight_divert,
    set_flight_pilot,
    set_flight_slot_player,
    set_flight_start_type,
    set_flight_tot_offset,
)
from game.commands.packages import require_package
from game.gamelock import locked
from game.server import EventStream
from game.squadrons import Pilot
from game.theater import ControlPoint
from .flightsettingsmodels import (
    FlightCallsignJs,
    FlightCustomNameJs,
    FlightDivertJs,
    FlightPilotChoiceJs,
    FlightSettingsJs,
    FlightSizeJs,
    FlightSlotPlayerJs,
    FlightSquadronChangedJs,
    FlightSquadronChoiceJs,
    FlightStartTypeJs,
    FlightTotOffsetJs,
)
from .models import PackageDetailJs
from .routes import _flight, _now, _require_game, _squadron
from ..commanderrors import command_error_responses
from ..dependencies import GameContext

router: APIRouter = APIRouter()

FLIGHT = "/{package_id}/flights/{flight_id}"


def _find(
    game: Game | None, package_id: UUID, flight_id: UUID
) -> tuple[Game, Package, Flight]:
    game = _require_game(game)
    package = require_package(game, package_id)
    return game, package, _flight(package, flight_id)


def _changed(game: Game, package: Package, flight: Flight) -> PackageDetailJs:
    """Publishes the change: the TOT of an ASAP package moves with its flights."""
    with EventStream.event_context() as events:
        if package.auto_asap:
            events.update_flights_in_package(package)
        else:
            events.update_flight(flight)
    return PackageDetailJs.for_package(game, package)


@router.get(
    FLIGHT + "/settings",
    operation_id="get_flight_settings",
    response_model=FlightSettingsJs,
    responses=command_error_responses("No campaign is loaded, or no such flight."),
)
@locked
def get_flight_settings(
    package_id: UUID,
    flight_id: UUID,
    game: Game | None = Depends(GameContext.get),
) -> FlightSettingsJs:
    _, _, flight = _find(game, package_id, flight_id)
    return FlightSettingsJs.for_flight(flight)


@router.put(
    FLIGHT + "/squadron",
    operation_id="set_flight_squadron",
    response_model=FlightSquadronChangedJs,
    responses=command_error_responses(
        "The squadron cannot take the flight, or it cannot be planned."
    ),
)
@locked
def put_flight_squadron(
    package_id: UUID,
    flight_id: UUID,
    body: FlightSquadronChoiceJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightSquadronChangedJs:
    """A new flight of this squadron replaces this one, under another id."""
    game, package, flight = _find(game, package_id, flight_id)
    replacement = change_flight_squadron(
        flight, _squadron(game, package, body.squadron_id), _now(game)
    )
    with EventStream.event_context() as events:
        events.delete_flight(flight)
        events.new_flight(replacement)
        for other in package.flights:
            if other is not replacement:
                events.update_flight(other)
        game.compute_unculled_zones(events)
    return FlightSquadronChangedJs(
        flight_id=replacement.id, package=PackageDetailJs.for_package(game, package)
    )


@router.put(
    FLIGHT + "/size",
    operation_id="set_flight_size",
    response_model=PackageDetailJs,
    responses=command_error_responses("The squadron lacks the aircraft."),
)
@locked
def put_flight_size(
    package_id: UUID,
    flight_id: UUID,
    body: FlightSizeJs,
    game: Game | None = Depends(GameContext.get),
) -> PackageDetailJs:
    game, package, flight = _find(game, package_id, flight_id)
    resize_flight(flight, body.size, _now(game))
    return _changed(game, package, flight)


@router.put(
    FLIGHT + "/start-type",
    operation_id="set_flight_start_type",
    response_model=PackageDetailJs,
    responses=command_error_responses("The base dictates the start type."),
)
@locked
def put_flight_start_type(
    package_id: UUID,
    flight_id: UUID,
    body: FlightStartTypeJs,
    game: Game | None = Depends(GameContext.get),
) -> PackageDetailJs:
    game, package, flight = _find(game, package_id, flight_id)
    set_flight_start_type(flight, body.start_type, _now(game))
    return _changed(game, package, flight)


def _control_point(game: Game, control_point_id: UUID) -> ControlPoint:
    try:
        return game.theater.find_control_point_by_id(control_point_id)
    except KeyError:
        raise CommandError("This base no longer exists.", status_code=404)


@router.put(
    FLIGHT + "/divert",
    operation_id="set_flight_divert",
    response_model=PackageDetailJs,
    responses=command_error_responses(
        "The flight cannot divert there, or it cannot be planned."
    ),
)
@locked
def put_flight_divert(
    package_id: UUID,
    flight_id: UUID,
    body: FlightDivertJs,
    game: Game | None = Depends(GameContext.get),
) -> PackageDetailJs:
    game, package, flight = _find(game, package_id, flight_id)
    set_flight_divert(
        flight, None if body.divert_id is None else _control_point(game, body.divert_id)
    )
    return _changed(game, package, flight)


@router.put(
    FLIGHT + "/tot-offset",
    operation_id="set_flight_tot_offset",
    response_model=PackageDetailJs,
    responses=command_error_responses("The offset is out of range."),
)
@locked
def put_flight_tot_offset(
    package_id: UUID,
    flight_id: UUID,
    body: FlightTotOffsetJs,
    game: Game | None = Depends(GameContext.get),
) -> PackageDetailJs:
    game, package, flight = _find(game, package_id, flight_id)
    set_flight_tot_offset(flight, timedelta(seconds=body.seconds), _now(game))
    return _changed(game, package, flight)


@router.put(
    FLIGHT + "/custom-name",
    operation_id="set_flight_custom_name",
    response_model=PackageDetailJs,
    responses=command_error_responses("The name has a | in it."),
)
@locked
def put_flight_custom_name(
    package_id: UUID,
    flight_id: UUID,
    body: FlightCustomNameJs,
    game: Game | None = Depends(GameContext.get),
) -> PackageDetailJs:
    game, package, flight = _find(game, package_id, flight_id)
    set_flight_custom_name(flight, body.name)
    return _changed(game, package, flight)


@router.put(
    FLIGHT + "/callsign",
    operation_id="set_flight_callsign",
    response_model=PackageDetailJs,
    responses=command_error_responses("The callsign is not available."),
)
@locked
def put_flight_callsign(
    package_id: UUID,
    flight_id: UUID,
    body: FlightCallsignJs,
    game: Game | None = Depends(GameContext.get),
) -> PackageDetailJs:
    game, package, flight = _find(game, package_id, flight_id)
    set_callsign(flight, body.name, body.number)
    return _changed(game, package, flight)


@router.delete(
    FLIGHT + "/callsign",
    operation_id="reset_flight_callsign",
    response_model=PackageDetailJs,
    responses=command_error_responses("No campaign is loaded, or no such flight."),
)
@locked
def delete_flight_callsign(
    package_id: UUID,
    flight_id: UUID,
    game: Game | None = Depends(GameContext.get),
) -> PackageDetailJs:
    """Back to an automatic callsign."""
    game, package, flight = _find(game, package_id, flight_id)
    reset_callsign(flight)
    return _changed(game, package, flight)


def _free_pilot(flight: Flight, pilot_id: UUID) -> Pilot:
    for pilot in flight.squadron.available_pilots:
        if pilot.id == pilot_id:
            return pilot
    raise CommandError("This pilot is no longer available.")


@router.put(
    FLIGHT + "/pilots/{slot}",
    operation_id="set_flight_pilot",
    response_model=PackageDetailJs,
    responses=command_error_responses("The pilot is no longer available."),
)
@locked
def put_flight_pilot(
    package_id: UUID,
    flight_id: UUID,
    slot: int,
    body: FlightPilotChoiceJs,
    game: Game | None = Depends(GameContext.get),
) -> PackageDetailJs:
    """A pilot, or nobody, in this slot (0 is the lead)."""
    game, package, flight = _find(game, package_id, flight_id)
    pilot = None if body.pilot_id is None else _free_pilot(flight, body.pilot_id)
    set_flight_pilot(flight, slot, pilot, _now(game))
    return _changed(game, package, flight)


@router.put(
    FLIGHT + "/pilots/{slot}/player",
    operation_id="set_flight_slot_player",
    response_model=PackageDetailJs,
    responses=command_error_responses("The slot is empty or the pilot cannot change."),
)
@locked
def put_flight_slot_player(
    package_id: UUID,
    flight_id: UUID,
    slot: int,
    body: FlightSlotPlayerJs,
    game: Game | None = Depends(GameContext.get),
) -> PackageDetailJs:
    """Makes the pilot of this slot a player or an AI."""
    game, package, flight = _find(game, package_id, flight_id)
    with EventStream.event_context() as events:
        set_flight_slot_player(flight, slot, body.player, events, _now(game))
    return _changed(game, package, flight)

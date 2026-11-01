"""Radios & TACAN tab of a flight in the package editor (WEB-04.5)."""

from uuid import UUID

from fastapi import APIRouter, Depends

from game import Game
from game.ato import Flight
from game.commands.flightradios import (
    set_datalink_value,
    set_flight_frequency,
    set_flight_tacan,
    set_package_frequency,
)
from game.commands.packages import require_package
from game.gamelock import locked
from game.server import EventStream
from .radiomodels import (
    DatalinkValueJs,
    FlightFrequencyJs,
    FlightRadiosJs,
    FlightTacanJs,
    PackageFrequencyJs,
)
from .routes import _flight, _refresh_qt, _require_game
from ..commanderrors import command_error_responses
from ..dependencies import GameContext, QtCallbacks, QtContext

#: Included in the router of `routes.py`, which adds `/packages`.
router: APIRouter = APIRouter(prefix="/{package_id}/flights/{flight_id}/radios")


def _find(game: Game, package_id: UUID, flight_id: UUID) -> Flight:
    return _flight(require_package(game, package_id), flight_id)


@router.get(
    "",
    operation_id="get_flight_radios",
    response_model=FlightRadiosJs,
    responses=command_error_responses("No campaign is loaded, or no such flight."),
)
@locked
def get_flight_radios(
    package_id: UUID,
    flight_id: UUID,
    game: Game | None = Depends(GameContext.get),
) -> FlightRadiosJs:
    game = _require_game(game)
    return FlightRadiosJs.for_flight(game, _find(game, package_id, flight_id))


@router.put(
    "/frequency",
    operation_id="set_flight_frequency",
    response_model=FlightRadiosJs,
    responses=command_error_responses("The radio of the flight cannot tune it."),
)
@locked
def put_flight_frequency(
    package_id: UUID,
    flight_id: UUID,
    body: FlightFrequencyJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRadiosJs:
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    with EventStream.event_context() as events:
        set_flight_frequency(flight, body.mhz, body.modulation, events)
    _refresh_qt(qt)
    return FlightRadiosJs.for_flight(game, flight)


@router.put(
    "/package-frequency",
    operation_id="set_package_frequency",
    response_model=FlightRadiosJs,
    responses=command_error_responses("The frequency is out of limits."),
)
@locked
def put_package_frequency(
    package_id: UUID,
    flight_id: UUID,
    body: PackageFrequencyJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRadiosJs:
    """Sets the frequency of the package this flight belongs to."""
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    with EventStream.event_context() as events:
        set_package_frequency(flight.package, body.mhz, events)
    _refresh_qt(qt)
    return FlightRadiosJs.for_flight(game, flight)


@router.put(
    "/tacan",
    operation_id="set_flight_tacan",
    response_model=FlightRadiosJs,
    responses=command_error_responses(
        "Not a tanker with a beacon, or a value out of limits."
    ),
)
@locked
def put_flight_tacan(
    package_id: UUID,
    flight_id: UUID,
    body: FlightTacanJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRadiosJs:
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    with EventStream.event_context() as events:
        set_flight_tacan(flight, body.channel, body.band, body.callsign, events)
    _refresh_qt(qt)
    return FlightRadiosJs.for_flight(game, flight)


@router.put(
    "/datalink/{member_index}",
    operation_id="set_flight_datalink",
    response_model=FlightRadiosJs,
    responses=command_error_responses(
        "No such member or setting, or an invalid value."
    ),
)
@locked
def put_flight_datalink(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    body: DatalinkValueJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRadiosJs:
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    with EventStream.event_context() as events:
        set_datalink_value(flight, member_index, body.identifier, body.value, events)
    _refresh_qt(qt)
    return FlightRadiosJs.for_flight(game, flight)

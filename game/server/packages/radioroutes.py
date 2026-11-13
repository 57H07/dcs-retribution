"""Radios & TACAN tab of a flight in the package editor (WEB-04.5)."""

import shutil
from uuid import UUID

from fastapi import APIRouter, Depends

from game import Game, persistency
from game.ato import Flight
from game.commands import CommandError
from game.commands.flightcartridge import (
    apply_to_aircraft,
    reset_cartridge_settings,
    set_cartridge_settings,
)
from game.commands.mission import last_cartridge
from game.commands.flightradios import (
    set_datalink_value,
    set_flight_frequency,
    set_flight_tacan,
    set_package_frequency,
)
from game.commands.packages import require_package
from game.gamelock import game_lock, locked, locks_game_itself
from game.native import FileOutcome, NativeBridge, one_dialog
from game.server import EventStream
from .radiomodels import (
    CartridgeSettingsUpdateJs,
    DatalinkValueJs,
    FlightFrequencyJs,
    FlightRadiosJs,
    FlightTacanJs,
    PackageFrequencyJs,
)
from .routes import _flight, _require_game
from ..commanderrors import command_error_responses
from ..dependencies import GameContext
from ..native.models import FileActionResultJs
from ..native.routes import require_bridge

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
) -> FlightRadiosJs:
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    with EventStream.event_context() as events:
        set_flight_frequency(flight, body.mhz, body.modulation, events)
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
) -> FlightRadiosJs:
    """Sets the frequency of the package this flight belongs to."""
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    with EventStream.event_context() as events:
        set_package_frequency(flight.package, body.mhz, events)
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
) -> FlightRadiosJs:
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    with EventStream.event_context() as events:
        set_flight_tacan(flight, body.channel, body.band, body.callsign, events)
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
) -> FlightRadiosJs:
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    with EventStream.event_context() as events:
        set_datalink_value(flight, member_index, body.identifier, body.value, events)
    return FlightRadiosJs.for_flight(game, flight)


@router.put(
    "/cartridge/settings",
    operation_id="set_cartridge_settings",
    response_model=FlightRadiosJs,
    responses=command_error_responses(
        "The aircraft takes no cartridge, or a CMDS value is out of limits."
    ),
)
@locked
def put_cartridge_settings(
    package_id: UUID,
    flight_id: UUID,
    body: CartridgeSettingsUpdateJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightRadiosJs:
    """Sets the cartridge of every player flight of the flight's squadron (#221)."""
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    set_cartridge_settings(flight, body.auto_load, body.threats, body.cmds)
    return FlightRadiosJs.for_flight(game, flight)


@router.delete(
    "/cartridge/settings",
    operation_id="reset_cartridge_settings",
    response_model=FlightRadiosJs,
    responses=command_error_responses("The aircraft takes no cartridge."),
)
@locked
def delete_cartridge_settings(
    package_id: UUID,
    flight_id: UUID,
    game: Game | None = Depends(GameContext.get),
) -> FlightRadiosJs:
    """Back to the module's defaults, loaded at spawn."""
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    reset_cartridge_settings(flight)
    return FlightRadiosJs.for_flight(game, flight)


@router.post(
    "/cartridge/settings/apply-to-aircraft",
    operation_id="apply_cartridge_settings_to_aircraft",
    response_model=FlightRadiosJs,
    responses=command_error_responses("The aircraft takes no cartridge."),
)
@locked
def post_apply_cartridge_settings(
    package_id: UUID,
    flight_id: UUID,
    game: Game | None = Depends(GameContext.get),
) -> FlightRadiosJs:
    """Copies the settings to every squadron of the coalition with the same aircraft."""
    game = _require_game(game)
    flight = _find(game, package_id, flight_id)
    apply_to_aircraft(flight)
    return FlightRadiosJs.for_flight(game, flight)


NO_CARTRIDGE = (
    "No data cartridge for this flight: it comes with the mission (Take off), "
    "for a player flight of an aircraft that takes one."
)


@router.post(
    "/cartridge/save",
    operation_id="save_flight_cartridge",
    response_model=FileActionResultJs,
    responses=command_error_responses(NO_CARTRIDGE),
)
@locks_game_itself
def post_save_cartridge(
    package_id: UUID,
    flight_id: UUID,
    bridge: NativeBridge = Depends(require_bridge),
) -> FileActionResultJs:
    """Asks where to save the data cartridge of the last mission, then copies it.

    The DCS DTC manager reads `Saved Games/DCS/DTC`, where the dialog opens.
    """
    with game_lock():
        game = _require_game(GameContext.get())
        source = last_cartridge(_find(game, package_id, flight_id).id)
    if source is None:
        raise CommandError(NO_CARTRIDGE)
    with one_dialog():
        path = bridge.choose_save_file(
            "Save the data cartridge",
            str(persistency.base_path() / "DTC" / source.name),
            "Data cartridge (*.dtc)",
        )
    if not path:
        return FileActionResultJs(outcome=FileOutcome.CANCELLED, path=None)
    shutil.copyfile(source, path)
    return FileActionResultJs(outcome=FileOutcome.SAVED, path=path)

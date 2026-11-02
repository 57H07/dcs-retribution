from uuid import UUID

from fastapi import APIRouter, Depends

from game import Game
from game.ato import Flight
from game.commands import CommandError
from game.commands.flightpayload import (
    backup_payload_file,
    require_member,
    reset_weapon_settings,
    save_member_payload,
    set_flight_fuel,
    set_member_custom,
    set_member_livery,
    set_member_loadout,
    set_member_property,
    set_member_pylon,
    set_same_livery,
    set_same_loadout,
    set_tgp_laser_code,
    set_weapon_laser_code,
    set_weapon_setting,
)
from game.commands.packages import require_package
from game.gamelock import locked
from game.server import EventStream
from .models import (
    FlightFuelJs,
    FlightPayloadJs,
    MemberCustomLoadoutJs,
    MemberLiveryJs,
    MemberLoadoutNameJs,
    MemberPylonWeaponJs,
    PayloadFileJs,
    PayloadValueJs,
    SameForAllJs,
    SavePayloadJs,
    TgpLaserCodeJs,
    WeaponLaserCodeChoiceJs,
)
from ..commanderrors import command_error_responses
from ..dependencies import GameContext

router: APIRouter = APIRouter(
    prefix="/packages/{package_id}/flights/{flight_id}/payload"
)

_REFUSED = command_error_responses("The engine refuses this change of the payload.")


def _game(game: Game | None) -> Game:
    if game is None:
        raise CommandError("No campaign is loaded.")
    return game


def _flight(game: Game, package_id: UUID, flight_id: UUID) -> Flight:
    for flight in require_package(game, package_id).flights:
        if flight.id == flight_id:
            return flight
    raise CommandError("This flight is no longer planned.", status_code=404)


def _changed(game: Game, flight: Flight) -> FlightPayloadJs:
    """Every open screen refreshes; the command answers the whole read model."""
    with EventStream.event_context() as events:
        events.update_flight(flight)
    return FlightPayloadJs.for_flight(game, flight)


@router.get(
    "",
    operation_id="get_flight_payload",
    response_model=FlightPayloadJs,
    responses=command_error_responses("No campaign is loaded, or no such flight."),
)
@locked
def get_flight_payload(
    package_id: UUID,
    flight_id: UUID,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    return FlightPayloadJs.for_flight(game, _flight(game, package_id, flight_id))


@router.put(
    "/fuel",
    operation_id="set_flight_fuel",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_flight_fuel(
    package_id: UUID,
    flight_id: UUID,
    body: FlightFuelJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    set_flight_fuel(flight, body.fuel)
    return _changed(game, flight)


@router.put(
    "/same-loadout",
    operation_id="set_same_loadout",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_same_loadout(
    package_id: UUID,
    flight_id: UUID,
    body: SameForAllJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    set_same_loadout(flight, body.same)
    return _changed(game, flight)


@router.put(
    "/same-livery",
    operation_id="set_same_livery",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_same_livery(
    package_id: UUID,
    flight_id: UUID,
    body: SameForAllJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    set_same_livery(flight, body.same)
    return _changed(game, flight)


@router.post(
    "/backup",
    operation_id="backup_flight_payloads",
    response_model=PayloadFileJs,
    responses=command_error_responses("The file cannot be copied."),
)
@locked
def post_backup(
    package_id: UUID,
    flight_id: UUID,
    game: Game | None = Depends(GameContext.get),
) -> PayloadFileJs:
    """Backs up the payload file of the aircraft, if it has one."""
    path = backup_payload_file(_flight(_game(game), package_id, flight_id))
    return PayloadFileJs(path=None if path is None else str(path))


@router.put(
    "/members/{member_index}/loadout",
    operation_id="set_member_loadout",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_member_loadout(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    body: MemberLoadoutNameJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    set_member_loadout(flight, require_member(flight, member_index), body.name)
    return _changed(game, flight)


@router.put(
    "/members/{member_index}/custom",
    operation_id="set_member_custom_loadout",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_member_custom(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    body: MemberCustomLoadoutJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    """On: starts from what the member flies. Off: back to the task's default."""
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    set_member_custom(game, flight, require_member(flight, member_index), body.custom)
    return _changed(game, flight)


@router.put(
    "/members/{member_index}/pylons/{number}",
    operation_id="set_member_pylon",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_member_pylon(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    number: int,
    body: MemberPylonWeaponJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    member = require_member(flight, member_index)
    set_member_pylon(game, flight, member, number, body.clsid)
    return _changed(game, flight)


@router.put(
    "/members/{member_index}/pylons/{number}/settings",
    operation_id="set_member_weapon_setting",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_weapon_setting(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    number: int,
    body: PayloadValueJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    member = require_member(flight, member_index)
    set_weapon_setting(flight, member, number, body.id, body.value)
    return _changed(game, flight)


@router.delete(
    "/members/{member_index}/pylons/{number}/settings",
    operation_id="reset_member_weapon_settings",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def delete_weapon_settings(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    number: int,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    """Back to the defaults of the weapon."""
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    reset_weapon_settings(flight, require_member(flight, member_index), number)
    return _changed(game, flight)


@router.put(
    "/members/{member_index}/tgp-laser-code",
    operation_id="set_member_tgp_laser_code",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_tgp_laser_code(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    body: TgpLaserCodeJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    set_tgp_laser_code(game, require_member(flight, member_index), body.assigned)
    return _changed(game, flight)


@router.put(
    "/members/{member_index}/weapon-laser-code",
    operation_id="set_member_weapon_laser_code",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_weapon_laser_code(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    body: WeaponLaserCodeChoiceJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    set_weapon_laser_code(game, require_member(flight, member_index), body.code)
    return _changed(game, flight)


@router.put(
    "/members/{member_index}/livery",
    operation_id="set_member_livery",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_member_livery(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    body: MemberLiveryJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    member = require_member(flight, member_index)
    set_member_livery(flight, member, body.livery_id, body.use_livery_set)
    return _changed(game, flight)


@router.put(
    "/members/{member_index}/properties",
    operation_id="set_member_property",
    response_model=FlightPayloadJs,
    responses=_REFUSED,
)
@locked
def put_member_property(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    body: PayloadValueJs,
    game: Game | None = Depends(GameContext.get),
) -> FlightPayloadJs:
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    member = require_member(flight, member_index)
    set_member_property(game, flight, member, body.id, body.value)
    return _changed(game, flight)


@router.post(
    "/members/{member_index}/save",
    operation_id="save_member_payload",
    response_model=PayloadFileJs,
    responses=command_error_responses(
        "The loadout is not custom, or the file cannot be written."
    ),
)
@locked
def post_save_payload(
    package_id: UUID,
    flight_id: UUID,
    member_index: int,
    body: SavePayloadJs,
    game: Game | None = Depends(GameContext.get),
) -> PayloadFileJs:
    """Saves the custom loadout as a named payload of the aircraft."""
    game = _game(game)
    flight = _flight(game, package_id, flight_id)
    member = require_member(flight, member_index)
    path = save_member_payload(flight, member, body.name)
    _changed(game, flight)
    return PayloadFileJs(path=str(path))

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from game import Game
from game.commands import CommandError
from game.commands.groundorders import find_ground_unit_type
from game.commands.transfers import cancel_transfer, find_transfer, place_transfer
from game.gamelock import locked
from game.server import EventStream
from game.squadrons import Squadron
from game.theater import ControlPoint
from game.theater.player import Player
from game.transfers import TransferOrder
from .models import NewTransferJs, TransferJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext, QtCallbacks, QtContext

router: APIRouter = APIRouter(prefix="/transfers")


@router.get("/", operation_id="list_transfers", response_model=list[TransferJs] | None)
@locked
def list_transfers(
    game: Game | None = Depends(GameContext.get),
) -> list[TransferJs] | None:
    """The player's pending ground unit transfers; null without a campaign."""
    if game is None:
        return None
    return [
        TransferJs.from_transfer(t) for t in game.coalition_for(Player.BLUE).transfers
    ]


def _base(game: Game, cp_id: UUID) -> ControlPoint:
    try:
        return game.theater.find_control_point_by_id(cp_id)
    except KeyError:
        raise CommandError("This base no longer exists.", status_code=404)


def _transport_squadron(game: Game, squadron_id: UUID) -> Squadron:
    for squadron in game.blue.air_wing.iter_squadrons():
        if squadron.id == squadron_id:
            return squadron
    raise CommandError("This squadron no longer exists.", status_code=404)


@router.post(
    "/",
    operation_id="create_transfer",
    response_model=TransferJs,
    responses=command_error_responses(
        "No campaign is loaded, not a player base, a destination this base cannot send "
        "to, no units or more than the base has, no route, or a squadron that cannot "
        "fly it (then nothing changes)"
    ),
)
@locked
def create_transfer(
    new: NewTransferJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> TransferJs:
    """Sends ground units to another base. With a squadron: a Transport mission."""
    if game is None:
        raise CommandError("No campaign is loaded.")
    origin = _base(game, new.origin_id)
    destination = _base(game, new.destination_id)
    if new.squadron_id is not None and not new.airlift:
        raise CommandError("Only an airlift can have a Transport squadron.")
    squadron = (
        _transport_squadron(game, new.squadron_id)
        if new.squadron_id is not None
        else None
    )
    units = {
        find_ground_unit_type(origin, line.unit_id): line.count for line in new.units
    }
    transfer = TransferOrder(
        origin=origin,
        destination=destination,
        units=units,
        request_airflift=new.airlift,
    )
    now = GameContext.get_sim().current_time_in_sim_if_game_loaded
    if now is None:
        raise CommandError("No campaign is loaded.")
    place_transfer(game, transfer, squadron, now)
    with EventStream.event_context() as events:
        events.update_control_point(origin)
    if qt is not None and qt.packages_changed is not None:
        # An airlift adds a package behind the Qt ATO models.
        qt.packages_changed()
    return TransferJs.from_transfer(transfer)


@router.delete(
    "/{transfer_id}",
    operation_id="cancel_transfer",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses(
        "No campaign is loaded, the transfer is not the player's, or it is gone"
    ),
)
@locked
def cancel(
    transfer_id: UUID,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> None:
    """Cancels a player transfer: its units return to the origin's inventory."""
    if game is None:
        raise CommandError("No campaign is loaded.")
    transfer = find_transfer(game, transfer_id)
    if transfer is None:
        raise CommandError("This transfer is no longer pending.", status_code=404)
    cancel_transfer(game, transfer)
    with EventStream.event_context() as events:
        events.update_control_point(transfer.origin)
    if qt is not None and qt.game_changed is not None:
        qt.game_changed()

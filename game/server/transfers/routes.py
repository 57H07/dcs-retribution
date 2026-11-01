from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from game import Game
from game.commands import CommandError
from game.commands.transfers import cancel_transfer, find_transfer
from game.gamelock import locked
from game.server import EventStream
from game.theater.player import Player
from .models import TransferJs
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

from game.gamelock import locked
from fastapi import APIRouter, Depends

from game import Game
from game.commands import CommandError, skip_turn
from game.server import GameContext
from .models import CampaignStateJs, GameJs, TurnJs
from ..commanderrors import command_error_responses
from ..dependencies import QtCallbacks, QtContext

router: APIRouter = APIRouter(prefix="/game")


@router.get("/", operation_id="get_game_state", response_model=GameJs)
@locked
def game_state(game: Game | None = Depends(GameContext.get)) -> GameJs | None:
    if game is None:
        return None
    return GameJs.from_game(game)


@router.post(
    "/turn/pass",
    operation_id="pass_turn",
    response_model=TurnJs,
    responses=command_error_responses("No campaign is loaded, or it is over."),
)
@locked
def pass_turn(
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> TurnJs:
    """Skip the current turn without flying it ("Pass Turn" / "Begin Campaign").

    The new turn is published on the event stream (`new_turn`), so every open screen
    reloads its state.
    """
    if game is None:
        raise CommandError("No campaign is loaded.")
    state = skip_turn(game)
    if qt is not None and qt.turn_passed is not None:
        qt.turn_passed(state)
    return TurnJs(turn=game.turn, campaign_state=CampaignStateJs.from_turn_state(state))

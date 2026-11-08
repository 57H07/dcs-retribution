"""The saves of the running campaign: autosaves and manual saves (#190).

Loading answers once the save is read; the new campaign then arrives as events, as
with File → Open.
"""

from fastapi import APIRouter, Depends

from game import Game, autosaves
from game.commands import CommandError
from game.gamelock import locked, locks_game_itself
from game.native import NativeBridge, load_listed_save
from .models import SaveJs, SavesJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext
from ..native.models import FileActionResultJs
from ..native.routes import require_bridge

router: APIRouter = APIRouter(prefix="/saves")


@router.get(
    "/",
    operation_id="list_saves",
    response_model=SavesJs,
    responses=command_error_responses("No campaign is loaded."),
)
@locked
def list_saves(game: Game | None = Depends(GameContext.get)) -> SavesJs:
    if game is None:
        raise CommandError("No campaign is loaded.")
    previous = autosaves.previous_turn_save(game)
    return SavesJs(
        saves=[SaveJs.from_entry(e) for e in autosaves.list_saves(game)],
        previous_turn_id=None if previous is None else previous.id,
    )


@router.post(
    "/{save_id}/load",
    operation_id="load_save",
    response_model=FileActionResultJs,
    responses=command_error_responses(
        "No campaign is loaded, the save no longer exists or it is incompatible."
    ),
)
@locks_game_itself
def load(
    save_id: str, bridge: NativeBridge = Depends(require_bridge)
) -> FileActionResultJs:
    """Loads a listed save; unsaved progress of the running campaign is lost."""
    return FileActionResultJs.from_result(
        load_listed_save(bridge, GameContext.get, save_id)
    )

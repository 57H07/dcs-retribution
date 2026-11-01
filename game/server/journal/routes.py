from fastapi import APIRouter, Depends

from game import Game
from game.commands import CommandError
from game.commands.notes import notes_of, set_notes
from game.gamelock import locked
from .models import InformationJs, NotesJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext

router: APIRouter = APIRouter()


@router.get("/notes", operation_id="get_notes", response_model=NotesJs | None)
@locked
def get_notes(game: Game | None = Depends(GameContext.get)) -> NotesJs | None:
    """The campaign notes (a kneeboard page); null without a campaign."""
    if game is None:
        return None
    return NotesJs(text=notes_of(game))


@router.put(
    "/notes",
    operation_id="set_notes",
    response_model=NotesJs,
    responses=command_error_responses("No campaign is loaded"),
)
@locked
def put_notes(notes: NotesJs, game: Game | None = Depends(GameContext.get)) -> NotesJs:
    """Replaces the campaign notes; saved with the campaign."""
    if game is None:
        raise CommandError("No campaign is loaded.")
    set_notes(game, notes.text)
    return NotesJs(text=notes_of(game))


@router.get(
    "/informations",
    operation_id="list_informations",
    response_model=list[InformationJs] | None,
)
@locked
def list_informations(
    game: Game | None = Depends(GameContext.get),
) -> list[InformationJs] | None:
    """Messages of the info panel, newest first; null without a campaign."""
    if game is None:
        return None
    return [InformationJs.from_information(i) for i in reversed(game.informations)]

"""Campaign notes (WEB-08.2), shown as a kneeboard page; shared by web and Qt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import CommandError

if TYPE_CHECKING:
    from game import Game

#: Generous bound so that a pasted file cannot bloat the save.
MAX_NOTES_LENGTH = 100_000


def notes_of(game: Game) -> str:
    """The notes of the campaign; old saves may have none."""
    return getattr(game, "notes", "") or ""


def set_notes(game: Game, text: str) -> None:
    if len(text) > MAX_NOTES_LENGTH:
        raise CommandError(
            f"Notes are limited to {MAX_NOTES_LENGTH:,} characters.", status_code=422
        )
    game.notes = text

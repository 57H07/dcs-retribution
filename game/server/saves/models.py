"""DTOs of the Load screen (#190)."""

from __future__ import annotations

from pydantic import BaseModel

from game.autosaves import SaveEntry, SaveKind


class SaveJs(BaseModel):
    id: str
    kind: SaveKind
    turn: int
    #: Date in game, ISO format.
    game_date: str
    #: When it was saved, local time, ISO format.
    saved_at: str
    file_name: str

    class Config:
        title = "Save"

    @staticmethod
    def from_entry(entry: SaveEntry) -> SaveJs:
        return SaveJs(
            id=entry.id,
            kind=entry.kind,
            turn=entry.turn,
            game_date=entry.game_date.isoformat(),
            saved_at=entry.saved_at.isoformat(timespec="seconds"),
            file_name=entry.path.name,
        )


class SavesJs(BaseModel):
    """The saves of the campaign, newest first, and the one to go back a turn."""

    saves: list[SaveJs]
    previous_turn_id: str | None

    class Config:
        title = "Saves"

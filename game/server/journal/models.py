"""Notes and info panel (WEB-08.2): read models of `QNotesWindow` and
`QInfoPanel`."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from game.infos.information import Information


class NotesJs(BaseModel):
    text: str


class InformationJs(BaseModel):
    """One message of the campaign's info panel."""

    turn: int
    title: str
    text: str
    #: Real-world time the message was logged (not the campaign clock).
    timestamp: datetime | None

    @staticmethod
    def from_information(info: Information) -> InformationJs:
        return InformationJs(
            turn=info.turn,
            title=info.title,
            text=info.text,
            timestamp=getattr(info, "timestamp", None),
        )

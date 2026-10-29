from __future__ import annotations

from pydantic import BaseModel

from game.native import FileActionResult, FileOutcome


class FileActionResultJs(BaseModel):
    """Outcome of a file action once the player closed the dialog (WEB-00.7)."""

    outcome: FileOutcome
    path: str | None

    class Config:
        title = "FileActionResult"

    @classmethod
    def from_result(cls, result: FileActionResult) -> FileActionResultJs:
        return FileActionResultJs(outcome=result.outcome, path=result.path)

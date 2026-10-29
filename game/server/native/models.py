from __future__ import annotations

from pydantic import BaseModel

from game.native import FileActionResult, FileOutcome, FolderPurpose


class FileActionResultJs(BaseModel):
    """Outcome of a file action once the player closed the dialog (WEB-00.7)."""

    outcome: FileOutcome
    path: str | None

    class Config:
        title = "FileActionResult"

    @classmethod
    def from_result(cls, result: FileActionResult) -> FileActionResultJs:
        return FileActionResultJs(outcome=result.outcome, path=result.path)


class FolderPickRequestJs(BaseModel):
    purpose: FolderPurpose
    # Folder the dialog opens in (the current value of the field), if any.
    start: str = ""

    class Config:
        title = "FolderPickRequest"


class FolderPickResultJs(BaseModel):
    """The folder chosen, or null when the player cancelled (WEB-07.2)."""

    path: str | None

    class Config:
        title = "FolderPickResult"

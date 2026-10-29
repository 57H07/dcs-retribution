from __future__ import annotations

from http import HTTPStatus


class CommandError(Exception):
    """A player action that the game rules refuse.

    The message is shown to the player as is, so keep it short and readable. The API
    answers with `status_code` (409 Conflict by default: the request is well formed
    but the current game state does not allow it) and `{"detail": message}`.
    """

    status_code: int = HTTPStatus.CONFLICT

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code

"""Qt screens the web UI can open while they are not migrated (WEB-00.3).

Each value is a path segment of `POST /qt/dialogs/{dialog}`. File actions, links and
quit go through the native bridge instead (`/native/*`, WEB-00.7).
A screen leaves `QtDialog` once its web version ships and its Qt dialog is deleted (W9).
Stats, finances and intel left for the web reports screen (WEB-08.1); notes, logs,
about, transfers, the info panel, import layouts and Pretense for web screens and
commands (WEB-08.2); the debriefing for the web after-action report (WEB-05.2).
"""

from __future__ import annotations

from enum import Enum


class QtDialog(str, Enum):
    AIR_WING = "air-wing"

    @property
    def needs_game(self) -> bool:
        """True when the dialog only makes sense with a campaign loaded."""
        return self not in _WITHOUT_GAME


_WITHOUT_GAME: set[QtDialog] = set()

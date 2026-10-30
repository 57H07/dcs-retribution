"""Qt screens the web UI can open while they are not migrated (WEB-00.3).

Each value is a path segment of `POST /qt/dialogs/{dialog}`. File actions, links and
quit go through the native bridge instead (`/native/*`, WEB-00.7).
A screen leaves `QtDialog` once its web version ships and its Qt dialog is deleted (W9).
"""

from __future__ import annotations

from enum import Enum


class QtDialog(str, Enum):
    STATS = "stats"
    NOTES = "notes"
    LOGS = "logs"
    ABOUT = "about"
    IMPORT_LAYOUTS = "import-layouts"
    PRETENSE_CAMPAIGN = "pretense-campaign"
    AIR_WING = "air-wing"
    TRANSFERS = "transfers"
    REPORTS = "reports"
    FINANCES = "finances"
    INTEL = "intel"
    DEBRIEFING = "debriefing"

    @property
    def needs_game(self) -> bool:
        """True when the dialog only makes sense with a campaign loaded."""
        return self not in _WITHOUT_GAME


_WITHOUT_GAME = {
    QtDialog.LOGS,
    QtDialog.ABOUT,
    QtDialog.IMPORT_LAYOUTS,
    QtDialog.DEBRIEFING,
}

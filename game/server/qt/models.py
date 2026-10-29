"""Qt screens and links the web UI can open while they are not migrated (WEB-00.3).

Each value is a path segment of `POST /qt/dialogs/{dialog}` or `POST /qt/links/{link}`.
A screen leaves `QtDialog` once its web version ships and its Qt dialog is deleted (W9).
"""

from __future__ import annotations

from enum import Enum


class QtDialog(str, Enum):
    NEW_GAME = "new-game"
    OPEN_GAME = "open-game"
    SAVE_GAME = "save-game"
    SAVE_GAME_AS = "save-game-as"
    PREFERENCES = "preferences"
    SETTINGS = "settings"
    STATS = "stats"
    NOTES = "notes"
    LOGS = "logs"
    ABOUT = "about"
    IMPORT_LAYOUTS = "import-layouts"
    PRETENSE_CAMPAIGN = "pretense-campaign"
    AIR_WING = "air-wing"
    TRANSFERS = "transfers"
    AIR_TASKING_ORDER = "air-tasking-order"
    REPORTS = "reports"
    FINANCES = "finances"
    INTEL = "intel"
    DEBRIEFING = "debriefing"
    QUIT = "quit"

    @property
    def needs_game(self) -> bool:
        """True when the dialog only makes sense with a campaign loaded."""
        return self not in _WITHOUT_GAME


_WITHOUT_GAME = {
    QtDialog.NEW_GAME,
    QtDialog.OPEN_GAME,
    QtDialog.PREFERENCES,
    QtDialog.LOGS,
    QtDialog.ABOUT,
    QtDialog.IMPORT_LAYOUTS,
    QtDialog.DEBRIEFING,
    QtDialog.QUIT,
}


class QtLink(str, Enum):
    """External pages of the Help menu, opened in the system browser by Qt."""

    DISCORD = "discord"
    GITHUB = "github"
    UKRAINE = "ukraine"
    PRETENSE_DISCORD = "pretense-discord"
    RELEASES = "releases"
    MANUAL = "manual"
    FORUM_THREAD = "forum-thread"
    ISSUES = "issues"

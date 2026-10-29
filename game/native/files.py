"""Open, save and save-as through the native bridge (WEB-00.7).

Shared by the `/native/*` API routes and the Qt menus, so that both apply the same
rules as the former `QLiberationWindow.openFile/saveGame/saveGameAs`.

The game lock is never held while a dialog waits for the player: these functions
take it only to read the campaign before the dialog and to write it after.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from game import persistency
from game.commands import CommandError
from game.gamelock import game_lock

from .bridge import NativeBridge

if TYPE_CHECKING:
    from game import Game

CurrentGame = Callable[[], "Game | None"]


class FileOutcome(str, Enum):
    SAVED = "saved"
    OPENED = "opened"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class FileActionResult:
    outcome: FileOutcome
    path: str | None = None


CANCELLED = FileActionResult(FileOutcome.CANCELLED)

# One file dialog at a time: a second Ctrl+S while the first dialog is open would
# otherwise stack another modal dialog on top of it.
_DIALOG = threading.Lock()


@contextmanager
def _one_dialog() -> Iterator[None]:
    if not _DIALOG.acquire(blocking=False):
        raise CommandError("A file dialog is already open.")
    try:
        yield
    finally:
        _DIALOG.release()


def _require(game: Game | None) -> Game:
    if game is None:
        raise CommandError("No campaign is loaded.")
    return game


def _start_dir(game: Game | None) -> str:
    if game is not None and game.savepath:
        return game.savepath
    return str(persistency.save_dir())


def save_game(bridge: NativeBridge, current_game: CurrentGame) -> FileActionResult:
    """Save to the current save file, or ask for one (save as) when there is none."""
    with game_lock():
        game = _require(current_game())
        if game.savepath:
            return _write(bridge, game, game.savepath)
    return save_game_as(bridge, current_game)


def save_game_as(bridge: NativeBridge, current_game: CurrentGame) -> FileActionResult:
    with game_lock():
        game = _require(current_game())
        start = _start_dir(game)
    with _one_dialog():
        path = bridge.choose_save_path(start)
    if not path:
        return CANCELLED
    with game_lock():
        if current_game() is not game:
            raise CommandError(
                "Another campaign was loaded while the dialog was open: "
                "nothing was saved."
            )
        return _write(bridge, game, path)


def _write(bridge: NativeBridge, game: Game, path: str) -> FileActionResult:
    previous = game.savepath
    game.savepath = path
    if not persistency.save_game(game):
        game.savepath = previous
        raise CommandError(f"Could not save the campaign to {path}.", status_code=500)
    bridge.game_saved(path)
    return FileActionResult(FileOutcome.SAVED, path)


def open_game(bridge: NativeBridge, current_game: CurrentGame) -> FileActionResult:
    """Ask for a save file, read and migrate it, then hand it to the shell."""
    with game_lock():
        start = _start_dir(current_game())
    with _one_dialog():
        path = bridge.choose_open_path(start)
    if not path:
        return CANCELLED
    # The new campaign is not shared with any other thread yet: no lock needed.
    game = _load(path)
    bridge.game_loaded(game, path)
    return FileActionResult(FileOutcome.OPENED, path)


def _load(path: str) -> Game:
    from game import Migrator

    incompatible = CommandError(
        f"Incompatible save file: {path}. Please report the issue on GitHub or "
        "Discord with the campaign that fails to load."
    )
    try:
        game = persistency.load_game(path)
    except OSError:
        logging.exception("Could not read save file %s", path)
        raise CommandError(f"Could not read {path}.")
    if game is None:
        raise incompatible
    try:
        Migrator(game, ".liberation" in path)
    except Exception:
        logging.exception("Could not migrate save file %s", path)
        raise incompatible
    return game


class FolderPurpose(str, Enum):
    """Folders the preferences ask for (WEB-07.2)."""

    SAVED_GAMES = "saved-games"
    DCS_INSTALL = "dcs-install"

    @property
    def dialog_title(self) -> str:
        if self is FolderPurpose.SAVED_GAMES:
            return "Select DCS Saved Game Directory"
        return "Select DCS Installation Directory"


def choose_folder(
    bridge: NativeBridge, purpose: FolderPurpose, start: str
) -> str | None:
    """Ask for a folder; None when the player cancels. Never touches the game."""
    with _one_dialog():
        return bridge.choose_folder(purpose.dialog_title, start)

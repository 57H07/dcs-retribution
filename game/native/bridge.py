"""The interface a shell implements so that the engine can reach the system (W7)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game


class NativeBridge(ABC):
    """System services of the shell hosting the web UI.

    Threading contract (see `game.gamelock`):

    * `choose_open_path` and `choose_save_path` block until the player answers the
      dialog. They are called *without* the game lock, from an API worker thread or
      from the shell's own UI thread, and must work from both.
    * Every other method may be called with the game lock held: it must only queue
      the work onto the shell's UI thread (or do something that never waits on
      another thread) and return at once.
    """

    @abstractmethod
    def choose_open_path(self, start: str) -> str | None:
        """Ask for a save file to open. None when the player cancels."""

    @abstractmethod
    def choose_save_path(self, start: str) -> str | None:
        """Ask where to save the campaign. None when the player cancels."""

    @abstractmethod
    def game_loaded(self, game: Game, path: str) -> None:
        """Make `game`, just read from `path`, the campaign of the shell."""

    @abstractmethod
    def game_saved(self, path: str) -> None:
        """The campaign was saved to `path`: remember it as the last save file."""

    @abstractmethod
    def open_new_game(self) -> None:
        """Open the new campaign wizard."""

    @abstractmethod
    def open_folder(self, path: Path) -> None:
        """Show `path` in the system file manager."""

    @abstractmethod
    def open_url(self, url: str) -> None:
        """Open `url` in the system browser."""

    @abstractmethod
    def quit(self) -> None:
        """Close the application (the shell may ask to save first)."""


class NativeContext:
    """The bridge of the running shell, or None (tests, no shell yet)."""

    _bridge: NativeBridge | None = None

    @classmethod
    def set_bridge(cls, bridge: NativeBridge | None) -> None:
        cls._bridge = bridge

    @classmethod
    def get(cls) -> NativeBridge | None:
        return cls._bridge

"""Qt implementation of the native bridge (WEB-00.7, W7).

API routes run on worker threads, but Qt widgets live on the main thread. Every call
is therefore queued onto the main thread through a signal. The file dialogs make the
calling worker wait for the answer on a `Future`, which is safe because the engine
never holds the game lock while it asks (`game.native.files`).
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from PySide6.QtCore import QCoreApplication, QObject, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QWidget

from game.native import NativeBridge

if TYPE_CHECKING:
    from game import Game

T = TypeVar("T")

SAVE_FILE_FILTER = "*.retribution;;*.liberation"


class _MainThread(QObject):
    """Runs callables on the thread that created it (the Qt main thread)."""

    run = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        # Auto connection: queued when emitted from another thread.
        self.run.connect(self._call)

    @staticmethod
    def _call(func: Callable[[], None]) -> None:
        func()


class QtShell:
    """What the bridge needs from the main window (`QLiberationWindow`)."""

    def __init__(
        self,
        window: QWidget,
        on_game_loaded: Callable[[Game, str], None],
        on_game_saved: Callable[[str], None],
        open_new_game: Callable[[], None],
        quit: Callable[[], None],
    ) -> None:
        self.window = window
        self.on_game_loaded = on_game_loaded
        self.on_game_saved = on_game_saved
        self.open_new_game = open_new_game
        self.quit = quit


class QtNativeBridge(NativeBridge):
    def __init__(self, shell: QtShell) -> None:
        self._shell = shell
        self._main_thread = _MainThread()

    @staticmethod
    def _on_main_thread() -> bool:
        app = QCoreApplication.instance()
        return app is not None and QThread.currentThread() is app.thread()

    def _queue(self, func: Callable[[], None]) -> None:
        """Run `func` on the main thread without waiting for it."""
        self._main_thread.run.emit(func)

    def _wait_for(self, func: Callable[[], T]) -> T:
        """Run `func` on the main thread and wait for its result."""
        if self._on_main_thread():
            return func()
        future: Future[T] = Future()

        def run() -> None:
            try:
                future.set_result(func())
            except BaseException as error:
                future.set_exception(error)

        self._queue(run)
        return future.result()

    def choose_open_path(self, start: str) -> str | None:
        def ask() -> str | None:
            path, _ = QFileDialog.getOpenFileName(
                self._shell.window,
                "Select game file to open",
                dir=start,
                filter=SAVE_FILE_FILTER,
            )
            return path or None

        return self._wait_for(ask)

    def choose_save_path(self, start: str) -> str | None:
        def ask() -> str | None:
            path, _ = QFileDialog.getSaveFileName(
                self._shell.window, "Save As", dir=start, filter=SAVE_FILE_FILTER
            )
            return path or None

        return self._wait_for(ask)

    def game_loaded(self, game: Game, path: str) -> None:
        self._queue(lambda: self._shell.on_game_loaded(game, path))

    def game_saved(self, path: str) -> None:
        self._queue(lambda: self._shell.on_game_saved(path))

    def open_new_game(self) -> None:
        self._queue(self._shell.open_new_game)

    def open_folder(self, path: Path) -> None:
        url = QUrl.fromLocalFile(str(path))
        self._queue(lambda: self._open_url(url))

    def open_url(self, url: str) -> None:
        webbrowser.open_new_tab(url)

    def quit(self) -> None:
        self._queue(self._shell.quit)

    @staticmethod
    def _open_url(url: QUrl) -> None:
        QDesktopServices.openUrl(url)

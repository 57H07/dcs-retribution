"""The window hosting the web UI: all that is left of the Qt interface (WEB-09.1)."""

import logging
from typing import Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QCloseEvent, QGuiApplication, QIcon
from PySide6.QtWidgets import QMainWindow, QMessageBox

from game import Game, VERSION
from game import liberation_install
from game.commands import CommandError
from game.native import NativeContext, save_game
from game.native.files import load_save
from game.server import GameContext
from game.server.gamesession import activate_game
from qt_ui.nativebridge import QtNativeBridge, QtShell
from qt_ui.uncaughtexceptionhandler import UncaughtExceptionHandler
from qt_ui.webview import WebView


class ShellWindow(QMainWindow):
    def __init__(self, game: Optional[Game], dev: bool) -> None:
        super().__init__()

        self._uncaught_exception_handler = UncaughtExceptionHandler(self)
        self.native_bridge = QtNativeBridge(
            QtShell(
                self,
                on_game_loaded=self._on_game_opened,
                on_game_saved=self._on_game_saved,
                on_game_created=self._on_game_created,
                open_new_game=self._open_new_game,
                quit=self.close,
            )
        )
        NativeContext.set_bridge(self.native_bridge)

        self.web_view = WebView(dev, self)
        self.setCentralWidget(self.web_view)
        self.setWindowIcon(QIcon("./resources/icon.png"))
        self._update_title()

        # Default to maximized on the main display if we don't have any persistent
        # configuration.
        screen = QGuiApplication.primaryScreen().availableSize()
        self.setGeometry(0, 0, screen.width(), screen.height())
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self._restore_window_geometry()

        if game is not None:
            self._on_game_created(game)
        else:
            self._load_last_save()

    def _load_last_save(self) -> None:
        path = liberation_install.get_last_save_file()
        if not path:
            logging.info("No existing save game")
            return
        logging.info("Loading last saved game : %s", path)
        try:
            game = load_save(path)
        except CommandError as error:
            QMessageBox.critical(self, "Incompatible save", error.message)
            return
        self._on_game_opened(game, path)

    def _on_game_opened(self, game: Game, path: str) -> None:
        activate_game(game)
        self._update_title(game, path)

    def _on_game_created(self, game: Game) -> None:
        activate_game(game)
        self._update_title(game)

    def _on_game_saved(self, path: str) -> None:
        liberation_install.setup_last_save_file(path)
        liberation_install.save_config()
        self._update_title(GameContext.get(), path)

    def _open_new_game(self) -> None:
        self.web_view.show_screen("/new-game")

    def _update_title(
        self, game: Optional[Game] = None, save_path: Optional[str] = None
    ) -> None:
        """DCS Retribution - vX.X.X - campaign_name - file_name."""
        title = f"DCS Retribution - v{VERSION}"
        if game is not None and game.campaign_name:
            title += f" - {game.campaign_name}"
        if save_path:
            file_name = save_path.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
            title += f" - {file_name}"
        self.setWindowTitle(title)

    def _settings(self) -> QSettings:
        return QSettings("DCS Retribution", "Qt UI")

    def _restore_window_geometry(self) -> None:
        geometry = self._settings().value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    def closeEvent(self, event: QCloseEvent) -> None:
        result = QMessageBox.question(
            self,
            "Quit Retribution?",
            "Would you like to save before quitting?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if result == QMessageBox.StandardButton.Cancel:
            event.ignore()
            return
        if result == QMessageBox.StandardButton.Yes and GameContext.get() is not None:
            try:
                save_game(self.native_bridge, GameContext.get)
            except CommandError as error:
                QMessageBox.critical(self, "DCS Retribution", error.message)
                event.ignore()
                return
        self._settings().setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

from __future__ import annotations

import logging
from urllib.parse import quote
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from game.server.security import ApiKeyManager
from game.server.settings import ServerSettings
from qt_ui.liberation_install import server_port
from qt_ui.liberation_theme import get_token_variant
from qt_ui.models import GameModel
from qt_ui.theme_manager import theme_signals
from qt_ui.widgets.map.webprofile import map_web_profile


class LoggingWebPage(QWebEnginePage):
    def javaScriptConsoleMessage(
        self,
        level: QWebEnginePage.JavaScriptConsoleMessageLevel,
        message: str,
        line_number: int,
        source: str,
    ) -> None:
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            logging.error(message)
        elif level == QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel:
            logging.warning(message)
        else:
            logging.info(message)


class QLiberationMap(QWebEngineView):
    def __init__(self, game_model: GameModel, dev: bool, parent) -> None:
        super().__init__(parent)
        self.game_model = game_model
        self.setMinimumSize(800, 600)

        # Disk-based profile: basemap tiles go through the persistent HTTP cache.
        self.page = LoggingWebPage(map_web_profile(), self)
        # Required to allow "cross-origin" access from file:// scoped canvas.html to the
        # localhost HTTP backend.
        self.page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )

        if dev:
            url = QUrl("http://localhost:3000")
        else:
            url = QUrl.fromLocalFile(str(Path("client/build/index.html").resolve()))
        server_settings = ServerSettings.get(server_port())
        host = server_settings.server_bind_address
        if host.startswith("::"):
            host = f"[{host}]"
        port = server_settings.server_port
        api_key = quote(ApiKeyManager.key(), safe="")
        url.setQuery(
            f"server={host}:{port}&apiKey={api_key}&theme={get_token_variant()}"
        )
        self.page.load(url)
        self.setPage(self.page)
        theme_signals().theme_changed.connect(self.apply_theme)

    def apply_theme(self, variant: str) -> None:
        """Restyles the loaded map without reloading it (GFX-01.2).

        The page reads its initial theme from the URL; afterwards the client
        follows the data-theme attribute of the document element.
        """
        self.page.runJavaScript(theme_script(variant))


def theme_script(variant: str) -> str:
    if not variant.isalpha():
        raise ValueError(f"Invalid theme variant {variant!r}")
    return f'document.documentElement.dataset.theme = "{variant}";'

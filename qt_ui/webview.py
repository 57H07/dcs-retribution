"""The web view showing the client page (`client/`), with its server and API key."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from game.liberation_install import server_port
from game.server.security import ApiKeyManager
from game.server.settings import ServerSettings
from qt_ui.webprofile import map_web_profile


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


class WebView(QWebEngineView):
    def __init__(self, dev: bool, parent: QWidget) -> None:
        super().__init__(parent)
        self.setMinimumSize(800, 600)

        # Disk-based profile: basemap tiles go through the persistent HTTP cache.
        self.web_page = LoggingWebPage(map_web_profile(), self)
        # Required to allow "cross-origin" access from the file:// page to the
        # localhost HTTP backend.
        self.web_page.settings().setAttribute(
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
        url.setQuery(page_query(f"{host}:{port}", api_key))
        self.web_page.load(url)
        self.setPage(self.web_page)

    def show_screen(self, path: str) -> None:
        """Opens a screen of the web UI, which is hash-routed (WEB-00.3)."""
        self.web_page.runJavaScript(f'window.location.hash = "#{path}";')


def page_query(server: str, api_key: str) -> str:
    """Query string of the client page."""
    return f"server={server}&apiKey={api_key}"

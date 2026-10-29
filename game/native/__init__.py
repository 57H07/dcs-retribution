"""Native bridge: what the web UI needs from the operating system (WEB-00.7, W7).

Choosing a save file, opening a folder or an external link and quitting cannot be
done by a web page. The engine asks a `NativeBridge` instead, which the shell hosting
the web view implements: Qt today (`qt_ui/nativebridge.py`), Electron or a browser
later. The file actions themselves (`files.py`) know nothing about Qt or HTTP: the
`/native/*` API routes and the remaining Qt menus share them.
"""

from .bridge import NativeBridge, NativeContext
from .files import FileActionResult, FileOutcome, open_game, save_game, save_game_as
from .places import ExternalLink, NativeFolder

__all__ = [
    "ExternalLink",
    "FileActionResult",
    "FileOutcome",
    "NativeBridge",
    "NativeContext",
    "NativeFolder",
    "open_game",
    "save_game",
    "save_game_as",
]

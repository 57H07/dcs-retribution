"""Applies the current theme to the running application (GFX-01.2).

``liberation_theme`` knows which theme is selected; this module makes Qt follow
it, at startup and whenever the user picks another theme, without a restart:

* the application stylesheet is replaced, which re-polishes every widget, open
  dialogs included;
* the themed icons (``uiconstants.ICONS``) are reloaded from the theme's icon
  folder;
* ``theme_changed`` is emitted so that widgets holding something the stylesheet
  cannot reach (icons already set, painted colours, the map page) refresh it.

Widgets connect a bound method to ``theme_signals().theme_changed``: PySide
drops the connection when the receiving QObject is destroyed.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from qt_ui import liberation_theme, uiconstants


class ThemeSignals(QObject):
    #: Emitted after a theme switch, with the new token variant ("dark"/"light").
    theme_changed = Signal(str)


_signals: Optional[ThemeSignals] = None


def theme_signals() -> ThemeSignals:
    global _signals
    if _signals is None:
        _signals = ThemeSignals()
    return _signals


def apply_theme(app: QApplication) -> None:
    """Styles the application with the current theme."""
    app.setStyleSheet(liberation_theme.load_stylesheet())


def switch_theme(theme_index: int, app: Optional[QApplication] = None) -> bool:
    """Selects, saves and applies a theme. Returns False if it was already active."""
    if theme_index not in liberation_theme.THEMES:
        raise ValueError(f"Unknown theme index {theme_index}")
    changed = theme_index != liberation_theme.get_theme_index()
    liberation_theme.set_theme_index(theme_index)
    liberation_theme.save_theme_config()
    if not changed:
        return False

    if app is None:
        instance = QApplication.instance()
        assert isinstance(instance, QApplication)
        app = instance
    logging.info("Switching to the %s theme", liberation_theme.get_theme_name())
    apply_theme(app)

    uiconstants.load_icons()
    theme_signals().theme_changed.emit(liberation_theme.get_token_variant())
    return True

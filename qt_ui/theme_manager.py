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

Colours come from the design tokens, never from the widgets (GFX-01.3):

* states styled by the stylesheet use ``set_style_class()`` and a rule of
  ``resources/stylesheets/widgets.qss.template``;
* painted colours use ``token_color()`` at paint time or on theme_changed;
* rich-text links take the palette's link colour, set here from
  ``color-text-accent``.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

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


def token_color(name: str) -> QColor:
    """Design token of the current theme as a QColor, e.g. "color-chart-enemy"."""
    color = QColor(liberation_theme.get_token(name))
    if not color.isValid():
        raise ValueError(f"Token {name!r} is not a colour")
    return color


def set_style_class(widget: QWidget, style_class: Optional[str]) -> None:
    """Sets the "style" property matched by the stylesheets (None clears it).

    Qt does not re-evaluate property selectors on its own, so the widget is
    re-polished.
    """
    widget.setProperty("style", style_class)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def apply_theme(app: QApplication) -> None:
    """Styles the application with the current theme."""
    # Links in rich text (labels, message boxes) take the palette's link colour
    # when their HTML is parsed; QSS has no property for it.
    palette = app.palette()
    link = token_color("color-text-accent")
    palette.setColor(QPalette.ColorRole.Link, link)
    palette.setColor(QPalette.ColorRole.LinkVisited, link)
    app.setPalette(palette)
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

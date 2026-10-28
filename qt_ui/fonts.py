"""Bundled Inter font (GFX-01.4).

Inter (SIL Open Font License 1.1, resources/fonts/Inter/OFL.txt) is shipped
with the app and registered with Qt at startup, so no system install or network
access is needed. The application font is built from the design tokens
(font-family, font-family-fallback, font-size-md).

HiDPI: Qt 6 always scales by the screen's device pixel ratio, and main.py keeps
fractional factors (PassThrough rounding policy) so 150 % renders at 150 %, not
200 %. The font is sized in points and QSS sizes are logical pixels, so both
follow that ratio; hinting is disabled because hinted outlines snap to the
device pixel grid differently at fractional ratios, which changes glyph widths
and makes text spacing uneven at 150 %.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping

from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication

from qt_ui.design_tokens import TOKENS_PATH, load_tokens, px_to_points

FONTS_DIR = Path("resources/fonts/Inter")


def load_bundled_fonts(directory: Path = FONTS_DIR) -> list[str]:
    """Registers every bundled font file and returns the families it provides."""
    families: set[str] = set()
    for font_file in sorted(directory.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        if font_id == -1:
            logging.error("Could not load font %s", font_file)
            continue
        families.update(QFontDatabase.applicationFontFamilies(font_id))
    if not families:
        logging.error("No bundled font found in %s", directory)
    return sorted(families)


def _family_list(stack: str) -> list[str]:
    return [name.strip().strip("\"'") for name in stack.split(",") if name.strip()]


def app_font(tokens: Mapping[str, str]) -> QFont:
    font = QFont()
    font.setFamilies(
        _family_list(tokens["font-family"])
        + _family_list(tokens["font-family-fallback"])
    )
    font.setPointSizeF(px_to_points(tokens["font-size-md"]))
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def apply_app_font(app: QGuiApplication, variant: str | None = None) -> QFont:
    """Loads the bundled fonts and makes Inter the application font."""
    families = load_bundled_fonts()
    design = load_tokens(TOKENS_PATH)
    font = app_font(design.variant(variant or design.default_variant))
    app.setFont(font)
    logging.info("Application font: %s (bundled: %s)", font.families(), families)
    return font

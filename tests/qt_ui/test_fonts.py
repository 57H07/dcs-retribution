import os
from pathlib import Path
from typing import Iterator

import pytest
from PySide6.QtGui import QFont, QGuiApplication

from qt_ui.design_tokens import REPO_ROOT, load_tokens
from qt_ui.fonts import FONTS_DIR, app_font, load_bundled_fonts

CLIENT_FONTS_DIR = REPO_ROOT / "client/src/theme/fonts"
OFL_TITLE = "SIL OPEN FONT LICENSE Version 1.1"


@pytest.fixture(scope="module")
def gui_app() -> Iterator[QGuiApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication([])
    assert isinstance(app, QGuiApplication)
    yield app


@pytest.mark.parametrize(
    "licence",
    [
        REPO_ROOT / FONTS_DIR / "OFL.txt",
        CLIENT_FONTS_DIR / "OFL.txt",
        REPO_ROOT / "client/public/licenses/Inter-OFL.txt",
    ],
)
def test_ofl_licence_ships_with_the_font(licence: Path) -> None:
    text = licence.read_text(encoding="utf-8")
    assert OFL_TITLE in text
    assert "The Inter Project Authors" in text


def test_map_client_bundles_inter() -> None:
    assert (CLIENT_FONTS_DIR / "InterVariable.woff2").is_file()
    fonts_css = (REPO_ROOT / "client/src/theme/fonts.css").read_text(encoding="utf-8")
    assert "./fonts/InterVariable.woff2" in fonts_css
    # No network font source: every src is a bundled file.
    assert "http" not in fonts_css


def test_pyinstaller_package_includes_the_fonts() -> None:
    spec = (REPO_ROOT / "pyinstaller.spec").read_text(encoding="utf-8")
    assert "('resources', 'resources')" in spec
    assert "('client/build', 'client/build')" in spec


def test_bundled_fonts_register_inter(gui_app: QGuiApplication) -> None:
    families = load_bundled_fonts(REPO_ROOT / FONTS_DIR)
    assert "Inter" in families


def test_app_font_comes_from_the_tokens() -> None:
    tokens = load_tokens().variant("dark")
    font = app_font(tokens)
    assert font.families()[0] == "Inter"
    assert "Segoe UI" in font.families()
    # 12px at 96 logical DPI; Qt scales points with the device pixel ratio.
    assert font.pointSizeF() == 9
    assert font.hintingPreference() == QFont.HintingPreference.PreferNoHinting

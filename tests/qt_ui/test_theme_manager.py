import json
from pathlib import Path
from typing import Iterator

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout

from qt_ui import liberation_theme, uiconstants
from qt_ui.design_tokens import REPO_ROOT, load_tokens
from qt_ui.theme_manager import apply_theme, switch_theme, theme_signals
from qt_ui.widgets.map.QLiberationMap import theme_script

DARK = 2
LIGHT = 3


@pytest.fixture
def themed_app(
    qt_app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[QApplication]:
    # Resources are loaded relative to the repository root, the saved theme
    # goes to a temporary file.
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setattr(
        liberation_theme,
        "THEME_PREFERENCES_FILE_PATH",
        str(tmp_path / "liberation_theme.json"),
    )
    liberation_theme.set_theme_index(DARK)
    apply_theme(qt_app)
    uiconstants.load_icons()
    yield qt_app
    qt_app.setStyleSheet("")


def background(widget: QLabel) -> str:
    widget.ensurePolished()
    return widget.palette().color(QPalette.ColorRole.Window).name()


def test_switch_restyles_open_windows_without_restart(
    themed_app: QApplication,
) -> None:
    dialog = QDialog()
    label = QLabel("Open dialog", dialog)
    QVBoxLayout(dialog).addWidget(label)
    dialog.show()
    dark = load_tokens().variant("dark")["color-bg-canvas"]
    light = load_tokens().variant("light")["color-bg-canvas"]
    assert background(label) == dark

    assert switch_theme(LIGHT)
    assert themed_app.styleSheet() == liberation_theme.load_stylesheet()
    assert background(label) == light

    assert switch_theme(DARK)
    assert background(label) == dark
    dialog.close()


def test_switch_saves_the_theme(themed_app: QApplication) -> None:
    switch_theme(LIGHT)
    saved = Path(liberation_theme.THEME_PREFERENCES_FILE_PATH).read_text()
    assert json.loads(saved) == {"theme_index": LIGHT}


def test_switch_reloads_icons_and_notifies(themed_app: QApplication) -> None:
    received: list[str] = []
    theme_signals().theme_changed.connect(received.append)
    try:
        dark_icon = uiconstants.ICONS["Settings"].toImage()
        assert switch_theme(LIGHT)
        assert received == ["light"]
        # Dark and Light use different icon folders.
        assert uiconstants.ICONS["Settings"].toImage() != dark_icon

        assert not switch_theme(LIGHT)
        assert received == ["light"]
    finally:
        theme_signals().theme_changed.disconnect(received.append)


def test_unknown_theme_is_rejected(themed_app: QApplication) -> None:
    with pytest.raises(ValueError):
        switch_theme(42)


def test_map_theme_script() -> None:
    assert theme_script("light") == 'document.documentElement.dataset.theme = "light";'
    with pytest.raises(ValueError):
        theme_script('dark"; alert("x')

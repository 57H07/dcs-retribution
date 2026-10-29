"""WEB-00.3: the web UI option (preference + RETRIBUTION_WEB_UI override, W10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qt_ui import liberation_install


@pytest.fixture
def prefs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "retribution_preferences.json"
    monkeypatch.setattr(liberation_install, "PREFERENCES_PATH", path)
    monkeypatch.setattr(liberation_install.persistency, "setup", lambda *args: None)
    monkeypatch.delenv(liberation_install.WEB_UI_ENV_VAR, raising=False)
    return path


def _write(path: Path, **extra: object) -> None:
    data = {"saved_game_dir": "", "dcs_install_dir": "", **extra}
    path.write_text(json.dumps(data))


def test_off_by_default(prefs: Path) -> None:
    _write(prefs)
    liberation_install.init()
    assert liberation_install.web_ui_enabled() is False


def test_preference_turns_it_on_and_is_saved(prefs: Path) -> None:
    _write(prefs, web_ui=True)
    liberation_install.init()
    assert liberation_install.web_ui_enabled() is True

    liberation_install.set_web_ui_preference(False)
    liberation_install.save_config()
    assert json.loads(prefs.read_text())["web_ui"] is False


@pytest.mark.parametrize(
    "value, saved, expected",
    [("1", False, True), ("on", False, True), ("0", True, False), ("", True, True)],
)
def test_environment_overrides_the_preference(
    prefs: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    saved: bool,
    expected: bool,
) -> None:
    _write(prefs, web_ui=saved)
    liberation_install.init()
    monkeypatch.setenv(liberation_install.WEB_UI_ENV_VAR, value)
    assert liberation_install.web_ui_enabled() is expected


def test_page_query_requests_the_web_shell_only_when_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qt_ui.widgets.map import QLiberationMap

    monkeypatch.setattr(QLiberationMap, "get_token_variant", lambda: "dark")
    page_query = QLiberationMap.page_query

    on = page_query("[::1]:16880", "key", web_shell=True)
    off = page_query("[::1]:16880", "key", web_shell=False)
    assert on.startswith("server=[::1]:16880&apiKey=key&")
    assert on.endswith("&shell=web")
    assert "shell=" not in off

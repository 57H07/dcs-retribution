"""WEB-07.2: install preferences and first start, with no campaign loaded."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from game import liberation_install
from game.native import NativeContext
from game.server import GameContext
from tests.server.test_native_routes import FakeBridge, _set_game
from tests.server.test_settings_routes import _request


@pytest.fixture
def prefs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An absent preferences file, no detectable DCS, no campaign loaded."""
    path = tmp_path / "user" / "retribution_preferences.json"
    monkeypatch.setattr(liberation_install, "PREFERENCES_PATH", path)
    monkeypatch.setattr(liberation_install.persistency, "setup", lambda *args: None)
    monkeypatch.setattr(liberation_install, "_detect_saved_games_directory", str)
    monkeypatch.setattr(liberation_install, "_detect_install_directory", str)
    monkeypatch.delenv(liberation_install.WEB_UI_ENV_VAR, raising=False)
    _set_game(monkeypatch, None)
    return path


@pytest.fixture
def replaced(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Records each MissionScripting.lua replacement (install folder used)."""
    calls: list[str] = []
    monkeypatch.setattr(
        liberation_install,
        "replace_mission_scripting_file",
        lambda: calls.append(liberation_install.get_dcs_install_directory()),
    )
    return calls


@pytest.fixture
def saved_games(tmp_path: Path) -> Path:
    path = tmp_path / "Saved Games" / "DCS"
    path.mkdir(parents=True)
    return path


@pytest.fixture
def dcs(tmp_path: Path) -> Path:
    path = tmp_path / "DCS World"
    (path / "Scripts").mkdir(parents=True)
    return path


def _body(saved_games: Path | str, install: Path | str, **extra: Any) -> dict[str, Any]:
    return {
        "saved_game_dir": str(saved_games),
        "dcs_install_dir": str(install),
        "prefer_liberation_payloads": True,
        "setup_preferences_on_every_start": False,
        "server_port": 16881,
        "web_ui": True,
        **extra,
    }


def _get() -> dict[str, Any]:
    status, body = _request("GET", "/preferences/")
    assert status == 200
    return body


def _put(body: dict[str, Any]) -> tuple[int, Any]:
    return _request("PUT", "/preferences/", body)


# --- first start detection ------------------------------------------------------


def test_first_start_without_preferences_file_and_no_campaign(prefs: Path) -> None:
    assert GameContext.get() is None
    assert liberation_install.init() is True
    state = _get()
    assert state["first_start"] is True
    assert state["saved_game_dir_problem"] == "Choose your DCS Saved Games folder."
    assert state["dcs_install_dir_problem"] is None
    assert state["preferences"]["server_port"] == 16880
    assert state["preferences"]["web_ui"] is False


@pytest.mark.parametrize("content", ["", "{}", "[]", "not json"])
def test_empty_or_broken_preferences_file_starts_the_first_start(
    prefs: Path, content: str
) -> None:
    prefs.parent.mkdir(parents=True)
    prefs.write_text(content)
    assert liberation_install.init() is True
    assert _get()["first_start"] is True


def test_valid_preferences_skip_the_first_start(
    prefs: Path, saved_games: Path, dcs: Path
) -> None:
    prefs.parent.mkdir(parents=True)
    prefs.write_text(
        json.dumps({"saved_game_dir": str(saved_games), "dcs_install_dir": str(dcs)})
    )
    assert liberation_install.init() is False
    state = _get()
    assert state["first_start"] is False
    assert state["saved_game_dir_problem"] is None
    assert state["dcs_install_dir_problem"] is None


def test_setup_on_every_start_shows_the_first_start(
    prefs: Path, saved_games: Path, dcs: Path
) -> None:
    prefs.parent.mkdir(parents=True)
    prefs.write_text(
        json.dumps(
            {
                "saved_game_dir": str(saved_games),
                "dcs_install_dir": str(dcs),
                "setup_preferences_on_every_start": True,
            }
        )
    )
    liberation_install.init()
    assert _get()["first_start"] is True


def test_missing_saved_games_folder_shows_the_first_start(
    prefs: Path, tmp_path: Path
) -> None:
    gone = tmp_path / "deleted"
    prefs.parent.mkdir(parents=True)
    prefs.write_text(json.dumps({"saved_game_dir": str(gone), "dcs_install_dir": ""}))
    assert liberation_install.init() is False
    state = _get()
    assert state["first_start"] is True
    assert state["saved_game_dir_problem"] == f"{gone} is not a valid directory."


# --- saving ---------------------------------------------------------------------


def test_put_saves_to_the_preferences_file_and_ends_the_first_start(
    prefs: Path, saved_games: Path, dcs: Path, replaced: list[str]
) -> None:
    liberation_install.init()
    status, state = _put(_body(saved_games, dcs))
    assert status == 200
    assert state["first_start"] is False
    assert state["warning"] is None
    assert state["preferences"] == _body(saved_games, dcs)
    saved = json.loads(prefs.read_text())
    assert saved["saved_game_dir"] == str(saved_games)
    assert saved["dcs_install_dir"] == str(dcs)
    assert saved["prefer_liberation_payloads"] is True
    assert saved["server_port"] == 16881
    assert saved["web_ui"] is True
    # Accepting the first start replaces MissionScripting.lua, as in Qt; later
    # changes do not.
    assert replaced == [str(dcs)]
    assert _put(_body(saved_games, dcs, prefer_liberation_payloads=False))[0] == 200
    assert replaced == [str(dcs)]
    assert _get()["preferences"]["prefer_liberation_payloads"] is False


def test_put_keeps_fields_it_does_not_edit(
    prefs: Path, saved_games: Path, dcs: Path, replaced: list[str]
) -> None:
    prefs.parent.mkdir(parents=True)
    prefs.write_text(
        json.dumps(
            {
                "saved_game_dir": str(saved_games),
                "dcs_install_dir": str(dcs),
                "last_save_file": "C:/saves/a.retribution",
                "ignore_empty_install_directory": True,
            }
        )
    )
    liberation_install.init()
    assert _put(_body(saved_games, dcs))[0] == 200
    saved = json.loads(prefs.read_text())
    assert saved["last_save_file"] == "C:/saves/a.retribution"
    assert saved["ignore_empty_install_directory"] is True


def test_failed_mission_scripting_replacement_is_a_warning(
    prefs: Path, saved_games: Path, dcs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail() -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(liberation_install, "replace_mission_scripting_file", fail)
    liberation_install.init()
    status, state = _put(_body(saved_games, dcs))
    assert status == 200
    assert "MissionScripting" in state["warning"]
    assert prefs.exists()


# --- validation (as the Qt window) ---------------------------------------------


def _refused(body: dict[str, Any], prefs: Path) -> str:
    status, error = _put(body)
    assert status == 409
    assert not prefs.exists()
    return str(error["detail"])


def test_invalid_saved_games_folder_is_refused(
    prefs: Path, tmp_path: Path, dcs: Path, replaced: list[str]
) -> None:
    liberation_install.init()
    missing = tmp_path / "nowhere"
    assert (
        _refused(_body(missing, dcs), prefs) == f"{missing} is not a valid directory."
    )
    assert _refused(_body("", dcs), prefs) == "Choose your DCS Saved Games folder."
    assert replaced == []
    assert _get()["first_start"] is True


def test_install_folder_must_be_a_dcs_installation(
    prefs: Path, tmp_path: Path, saved_games: Path, replaced: list[str]
) -> None:
    liberation_install.init()
    missing = tmp_path / "nowhere"
    assert "is not a valid directory" in _refused(_body(saved_games, missing), prefs)
    not_dcs = tmp_path / "Documents"
    not_dcs.mkdir()
    assert "is not a DCS installation folder" in _refused(
        _body(saved_games, not_dcs), prefs
    )
    assert replaced == []


def test_empty_install_folder_needs_confirmation(
    prefs: Path, saved_games: Path, replaced: list[str]
) -> None:
    liberation_install.init()
    assert "Confirm to leave it empty" in _refused(_body(saved_games, ""), prefs)
    status, state = _put(_body(saved_games, "", allow_empty_install_dir=True))
    assert status == 200
    assert state["first_start"] is False
    assert json.loads(prefs.read_text())["dcs_install_dir"] == ""


@pytest.mark.parametrize("port", [0, 65536])
def test_server_port_out_of_range_is_rejected(
    prefs: Path, saved_games: Path, dcs: Path, port: int
) -> None:
    liberation_install.init()
    status, _ = _put(_body(saved_games, dcs, server_port=port))
    assert status == 422
    assert not prefs.exists()


# --- folder picker (native bridge) ----------------------------------------------


def test_pick_folder_answers_the_chosen_folder_without_the_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge = FakeBridge("D:/DCS World")
    monkeypatch.setattr(NativeContext, "_bridge", bridge)
    status, body = _request(
        "POST", "/native/pick-folder", {"purpose": "dcs-install", "start": "C:/"}
    )
    assert (status, body) == (200, {"path": "D:/DCS World"})
    assert bridge.asked == [("folder:Select DCS Installation Directory", "C:/")]
    assert bridge.lock_free_while_asking == [True]


def test_pick_folder_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = FakeBridge(None)
    monkeypatch.setattr(NativeContext, "_bridge", bridge)
    status, body = _request("POST", "/native/pick-folder", {"purpose": "saved-games"})
    assert (status, body) == (200, {"path": None})
    assert bridge.asked == [("folder:Select DCS Saved Game Directory", "")]


def test_pick_folder_needs_the_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(NativeContext, "_bridge", None)
    status, _ = _request("POST", "/native/pick-folder", {"purpose": "saved-games"})
    assert status == 503

"""#190: the saves of the campaign over HTTP (Load screen)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

import game
from game import autosaves
from game.autosaves import SaveKind
from game.native import NativeContext
from tests.server.test_command_view_commands import _request
from tests.server.test_native_routes import FakeBridge, _set_game
from tests.test_autosaves import fake_game


@pytest.fixture
def bridge(monkeypatch: pytest.MonkeyPatch) -> FakeBridge:
    fake = FakeBridge()
    monkeypatch.setattr(NativeContext, "_bridge", fake)
    return fake


@pytest.fixture
def current(monkeypatch: pytest.MonkeyPatch) -> Any:
    """A loaded campaign of its own, so its autosave folder is empty."""
    campaign = fake_game(campaign_id=uuid4().hex, savepath="C:/saves/mine.retribution")
    _set_game(monkeypatch, campaign)
    monkeypatch.setattr(game, "Migrator", lambda g, is_liberation: None)
    return campaign


def test_saves_lists_the_autosaves_newest_first_and_the_previous_turn(
    current: Any,
) -> None:
    for turn in (1, 2):
        current.turn = turn
        autosaves.autosave(current, SaveKind.TURN)
    autosaves.autosave(current, SaveKind.TAKEOFF)
    current.turn = 3

    status, body = _request("GET", "/saves/")

    assert status == 200
    assert [(s["kind"], s["turn"]) for s in body["saves"]] == [
        ("takeoff", 2),
        ("turn", 2),
        ("turn", 1),
    ]
    assert body["saves"][0]["file_name"] == "takeoff-0002.retribution"
    assert body["saves"][0]["game_date"] == "1999-06-14"
    assert body["previous_turn_id"] == "takeoff-0002"


def test_saves_needs_a_campaign(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_game(monkeypatch, None)
    assert _request("GET", "/saves/") == (409, {"detail": "No campaign is loaded."})


def test_loading_an_autosave_keeps_saving_where_the_player_saved(
    bridge: FakeBridge, current: Any
) -> None:
    current.turn = 4
    entry = autosaves.autosave(current, SaveKind.TURN)
    assert entry is not None

    status, body = _request("POST", f"/saves/{entry.id}/load")

    assert (status, body) == (200, {"outcome": "opened", "path": str(entry.path)})
    [(loaded, path)] = bridge.loaded
    assert loaded.turn == 4
    assert loaded.savepath == "C:/saves/mine.retribution"
    assert path == "C:/saves/mine.retribution"


def test_loading_an_unknown_save_is_refused(bridge: FakeBridge, current: Any) -> None:
    status, body = _request("POST", "/saves/turn-0099/load")
    assert status == 409
    assert body == {"detail": "This save no longer exists."}
    assert bridge.loaded == []

"""#193: the war diary routes: the entries, newest first, and the HTML export."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from game import persistency
from game.native import NativeContext
from game.server import GameContext
from game.wardiary import DiaryBase, DiaryEntry, DiaryPilot
from tests.server.test_command_view_commands import _request
from tests.server.test_native_routes import FakeBridge


def _entry(turn: int, summary: str) -> DiaryEntry:
    return DiaryEntry(
        turn=turn,
        date="17 May 2022",
        weather="Clear, no rain, no fog",
        verdict="Tactical victory",
        verdict_tone="good",
        summary=summary,
        air_kills_friendly=2,
        air_kills_enemy=1,
        ground_kills_friendly=3,
        ground_kills_enemy=0,
        bases=[DiaryBase("cp-1", "Krymsk", taken=True)],
        pilots=[DiaryPilot("p-1", "Lt. Moroz", "VF-11", "F/A-18C", "Rescued")],
        budget_next_turn=1420.5,
        income_next_turn=180.0,
    )


@pytest.fixture
def game(monkeypatch: pytest.MonkeyPatch) -> Any:
    game = SimpleNamespace(
        campaign_name="Operation Dawn",
        war_diary=[_entry(3, "Quiet day"), _entry(4, "Krymsk taken")],
        war_diary_since_turn=3,
    )
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=game), raising=False
    )
    return game


@pytest.fixture
def bridge(monkeypatch: pytest.MonkeyPatch) -> FakeBridge:
    fake = FakeBridge()
    monkeypatch.setattr(NativeContext, "_bridge", fake)
    return fake


def test_the_diary_lists_the_turns_newest_first(game: Any) -> None:
    status, body = _request("GET", "/war-diary")

    assert status == 200
    assert body["campaign"] == "Operation Dawn"
    assert body["since_turn"] == 3
    assert [e["turn"] for e in body["entries"]] == [4, 3]
    latest = body["entries"][0]
    assert latest["summary"] == "Krymsk taken"
    assert latest["bases"] == [{"id": "cp-1", "name": "Krymsk", "taken": True}]
    assert latest["pilots"][0]["pilot_id"] == "p-1"
    assert latest["verdict_tone"] == "good"


def test_no_campaign_has_no_diary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    assert _request("GET", "/war-diary") == (200, None)


def test_the_diary_is_exported_where_the_player_wants(
    game: Any, bridge: FakeBridge, tmp_path: Path
) -> None:
    target = tmp_path / "dawn.html"
    bridge.answer = str(target)

    status, body = _request("POST", "/war-diary/export")

    assert (status, body) == (200, {"outcome": "saved", "path": str(target)})
    page = target.read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>")
    assert page.index("Krymsk taken") < page.index("Quiet day")
    [(kind, start)] = bridge.asked
    assert kind == "save-file"
    # Next to the saves, in the Retribution folder, not at the root of Saved Games.
    assert start == str(
        persistency.base_path() / "Retribution" / "War diary - Operation Dawn.html"
    )


def test_exporting_the_diary_can_be_cancelled(
    game: Any, bridge: FakeBridge, tmp_path: Path
) -> None:
    status, body = _request("POST", "/war-diary/export")

    assert (status, body) == (200, {"outcome": "cancelled", "path": None})

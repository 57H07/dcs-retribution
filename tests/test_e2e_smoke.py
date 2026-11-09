"""WEB-09: a campaign played end to end through the API, as the web UI drives it.

No Qt and no DCS: the API runs in-process and a fake native bridge answers the file
dialogs, but the engine, the simulation and the mission generation are the real ones.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from game import Game
from game.commands.newgame import GenerationStatus, NewGameGeneration
from game.native import NativeContext
from game.server import GameContext
from game.server.gamesession import activate_game, start_session
from game.server.missionresult import MissionResultContext
from game.server.newgame.routes import NewGameContext
from tests.flightplans.referencegame import repository_payloads_only
from tests.server.test_air_wing import _request
from tests.server.test_native_routes import FakeBridge

CAMPAIGNS = [
    "Caucasus_Multi_Georgia",
    "RetakeTheFalklands",
    "TheValleyOfRotary",
    "WRL_AssaultonDamascus",
]

#: What the screens of the web UI read once a campaign runs.
SCREENS = [
    "/game/",
    "/game/top-bar",
    "/game/timeline",
    "/game/mission/checks",
    "/packages/",
    "/settings/",
    "/transfers/",
    "/air-wing",
    "/reports/intel",
    "/objectives",
]


class ShellBridge(FakeBridge):
    """Hands campaigns over like the Qt shell, without its thread hop."""

    def __init__(self, save_path: Path) -> None:
        super().__init__()
        self.save_path = save_path

    def choose_save_path(self, start: str) -> str | None:
        return str(self.save_path)

    def choose_open_path(self, start: str) -> str | None:
        return str(self.save_path)

    def game_created(self, game: Game) -> None:
        activate_game(game)

    def game_loaded(self, game: Game, path: str) -> None:
        activate_game(game)

    def game_saved(self, path: str) -> None:
        pass


@pytest.fixture(scope="module", autouse=True)
def _payloads(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    missing = Path(tmp_path_factory.mktemp("payloads")) / "none"
    with repository_payloads_only(missing):
        yield


@pytest.fixture
def session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[NewGameGeneration]:
    monkeypatch.setattr(GameContext, "_game_model", None, raising=False)
    start_session()
    monkeypatch.setattr(
        NativeContext, "_bridge", ShellBridge(tmp_path / "smoke.retribution")
    )
    generation = NewGameGeneration()
    NewGameContext.set(generation)
    yield generation
    generation.join()
    NewGameContext.set(None)
    MissionResultContext.get().reset()
    GameContext.get_sim().set_game(None)


def _ok(method: str, path: str, body: Any = None) -> Any:
    status, answer = _request(method, path, body)
    assert status < 300, f"{method} {path}: {status} {answer}"
    return answer


def _new_campaign(generation: NewGameGeneration, campaign_id: str) -> Game:
    options = _ok("GET", "/new-game/options")
    campaign = next(c for c in options["campaigns"] if c["id"] == campaign_id)
    _ok(
        "POST",
        "/new-game/generation",
        {
            "campaign_id": campaign_id,
            "blue": {"name": campaign["recommended_blue_faction"]},
            "red": {"name": campaign["recommended_red_faction"]},
            # Not every campaign recommends a date.
            "start_date": campaign["start_date"] or "2011-06-01",
            "player_budget": 2000,
            "enemy_budget": 2000,
            "seed": 2026,
            "settings": {},
        },
    )
    generation.join()
    snapshot = generation.snapshot()
    assert snapshot.status is GenerationStatus.CONFIGURING, snapshot.error
    _ok("POST", "/new-game/generation/begin")
    generation.join()
    snapshot = generation.snapshot()
    assert snapshot.status is GenerationStatus.DONE, snapshot.error
    return GameContext.require()


@pytest.mark.parametrize("campaign_id", CAMPAIGNS)
def test_a_campaign_from_the_wizard_to_the_second_turn(
    session: NewGameGeneration, campaign_id: str
) -> None:
    game = _new_campaign(session, campaign_id)
    assert game.turn == 0
    for screen in SCREENS:
        _ok("GET", screen)

    first_loop = GameContext.get_sim().game_loop
    answer = _ok("POST", "/game/turn/pass")
    assert answer["turn"] == 1
    assert answer["campaign_state"] == "continue"
    # A turn has its own simulation: the one of the previous turn is finished with.
    second_loop = GameContext.get_sim().game_loop
    assert second_loop is not first_loop
    bar = _ok("GET", "/game/top-bar")
    assert bar["turn"] == 1
    assert bar["campaign_state"] == "continue"
    for screen in SCREENS:
        _ok("GET", screen)

    # Take off, then back to planning.
    assert Path(_ok("POST", "/game/mission")["path"]).exists()
    assert _ok("GET", "/game/mission/result")["status"] == "waiting"
    _ok("POST", "/game/mission/result/cancel")
    assert _ok("GET", "/game/mission/result")["status"] == "idle"

    # Save, then open the save: the running campaign is replaced.
    assert _ok("POST", "/native/save-as")["outcome"] == "saved"
    assert _ok("POST", "/native/open")["outcome"] == "opened"
    reopened = GameContext.require()
    assert reopened is not game
    assert reopened.turn == 1
    assert _ok("GET", "/game/top-bar")["turn"] == 1


def test_a_stock_campaign_sets_its_objectives(session: NewGameGeneration) -> None:
    """#194: the example campaign's objectives match its bases and sites."""
    _new_campaign(session, "golan_heights_lite")

    answer = _ok("GET", "/objectives")
    assert [o["title"] for o in answer["objectives"]] == [
        "Capture Golan North",
        "Blind the Syrian air defences on the Golan",
        "Shut down the Qiryat Plant",
        "Keep the Golan South radar on the air",
    ]
    assert {o["state"] for o in answer["objectives"]} == {"In progress"}
    assert all(o["expected"] for o in answer["objectives"])
    bar = _ok("GET", "/game/top-bar")
    summary = bar["objectives"]
    assert (summary["met"], summary["missed"], summary["total"]) == (0, 0, 4)
    # The nearest deadline first; the plant has none.
    assert [o["title"] for o in summary["in_progress"]] == [
        "Blind the Syrian air defences on the Golan",
        "Capture Golan North",
        "Keep the Golan South radar on the air",
        "Shut down the Qiryat Plant",
    ]

    _ok("POST", "/game/turn/pass")
    answer = _ok("GET", "/objectives")
    assert {o["state"] for o in answer["objectives"]} == {"In progress"}

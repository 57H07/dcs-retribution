"""WEB-09.1: the campaign in play, without any Qt model."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.server import EventStream, GameContext
from game.server import gamesession
from game.server.dependencies import GameModel
from game.server.missionresult import MissionResultContext
from game.sim.simcontroller import SimController
from game.sim.simspeedsetting import SimSpeedSetting


class _Waiter:
    def __init__(self) -> None:
        self.resets = 0

    def reset(self) -> None:
        self.resets += 1


class _Sim:
    def __init__(self) -> None:
        self.games: list[Any] = []

    def set_game(self, game: Any) -> None:
        self.games.append(game)


def _game() -> Any:
    terrain = SimpleNamespace(map_view_default=SimpleNamespace(position="center"))
    return SimpleNamespace(theater=SimpleNamespace(terrain=terrain))


@pytest.fixture
def sim(monkeypatch: pytest.MonkeyPatch) -> _Sim:
    fake = _Sim()
    monkeypatch.setattr(GameContext, "_game_model", GameModel(None, fake), raising=False)  # type: ignore[arg-type]
    # The real one: the autouse fixture of this package records it otherwise.
    monkeypatch.setattr(
        GameContext,
        "reload_sim",
        lambda: GameContext.get_sim().set_game(GameContext.get()),
    )
    return fake


def test_activating_a_campaign_tells_everyone(
    sim: _Sim, monkeypatch: pytest.MonkeyPatch
) -> None:
    waiter = _Waiter()
    monkeypatch.setattr(MissionResultContext, "_waiter", waiter)
    drained: list[bool] = []
    published: list[Any] = []
    monkeypatch.setattr(EventStream, "drain", lambda: drained.append(True))
    monkeypatch.setattr(EventStream, "put_nowait", published.append)
    events = SimpleNamespace(game_loaded=lambda game: ("loaded", game))
    monkeypatch.setattr(gamesession, "GameUpdateEvents", lambda: events)
    game = _game()

    gamesession.activate_game(game)

    assert GameContext.get() is game
    assert sim.games == [game]
    assert waiter.resets == 1
    assert drained == [True]
    assert published == [("loaded", game)]


def test_the_sim_controller_needs_no_game() -> None:
    sim = SimController(None, lambda _: None)
    assert sim.simulation_speed is SimSpeedSetting.PAUSED
    assert sim.current_time_in_sim_if_game_loaded is None
    sim.set_game(None)

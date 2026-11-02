import pytest

from game.server import GameContext


@pytest.fixture(autouse=True)
def sim_reloads(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Records `GameContext.reload_sim`: most tests here fake the simulation."""
    reloads: list[bool] = []
    monkeypatch.setattr(GameContext, "reload_sim", lambda: reloads.append(True))
    return reloads

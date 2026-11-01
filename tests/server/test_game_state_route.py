"""The map asks for the game on every launch, with or without a campaign."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from game.server import GameContext
from game.server.app import app


def test_game_state_is_null_without_a_campaign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    response = TestClient(app).get("/game/")
    assert response.status_code == 200
    assert response.json() is None

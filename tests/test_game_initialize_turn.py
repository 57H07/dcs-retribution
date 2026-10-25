from __future__ import annotations

from unittest.mock import MagicMock, patch

from game.game import Game


def test_initialize_turn_renders_motorpools_before_planning() -> None:
    """Regression (BUG-03.2): motorpools must be rendered from the reserve before
    the coalitions plan. Otherwise Strike flight plans against them read empty or
    stale groups and get no target."""
    calls: list[str] = []
    game = MagicMock()
    game.theater.controlpoints = []
    game.blue.initialize_turn.side_effect = lambda *_: calls.append("blue")
    game.red.initialize_turn.side_effect = lambda *_: calls.append("red")

    with patch(
        "game.missiongenerator.motorpoolpopulator.MotorpoolPopulator"
    ) as populator:
        populator.return_value.populate.side_effect = lambda: calls.append("populate")
        Game.initialize_turn(game, MagicMock())

    populator.assert_called_once_with(game)
    assert calls == ["populate", "blue", "red"]

from unittest.mock import MagicMock, patch

from game.commander.battlepositions import BattlePositions
from game.commander.theaterstate import battle_positions_for


def test_front_line_point_out_of_air_assault_reach_is_covered() -> None:
    # Regression: Slava Ukraini crashed on Begin Campaign with a KeyError in
    # BreakthroughAttack because the front line's enemy base (Anapa) was out of
    # air assault reach and so missing from the battle positions.
    front_line_enemy = MagicMock(name="Anapa")
    neutral_fob = MagicMock(name="neutral FOB")
    empty = BattlePositions(blocking_capture=[], defending_front_line=[])
    with patch.object(BattlePositions, "for_control_point", return_value=empty):
        positions = battle_positions_for([front_line_enemy], [neutral_fob])

    assert set(positions) == {front_line_enemy, neutral_fob}


def test_point_in_both_lists_appears_once() -> None:
    cp = MagicMock(name="cp")
    empty = BattlePositions(blocking_capture=[], defending_front_line=[])
    with patch.object(BattlePositions, "for_control_point", return_value=empty):
        positions = battle_positions_for([cp], [cp])

    assert list(positions) == [cp]

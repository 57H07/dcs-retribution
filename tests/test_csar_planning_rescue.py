"""CSAR-01 gaps on planning and rescue: escorts, SAM avoidance, hoist at sea,
delivery-only AI rescues and front proximity (#65, #66, #67, #68, #71)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from dcs.mapping import Point
from dcs.terrain import Terrain

from game.squadrons.csarservice import CsarService
from game.theater.player import Player
from game.utils import nautical_miles

_TERRAIN = MagicMock(spec=Terrain)
_NM = nautical_miles(1).meters


# ---------------------------------------------------------------------------
# #71: front proximity is measured to the whole front line
# ---------------------------------------------------------------------------


def _survival_game(front_points: list[Point]) -> Any:
    game = MagicMock()
    game.settings = SimpleNamespace(
        csar_survival_turns=3,
        csar_survival_turns_hostile=2,
    )
    game.theater.closest_control_point.return_value.is_friendly.return_value = True
    # The midpoint is far from the pilot; only the route passes close by.
    front = SimpleNamespace(
        position=Point(0.0, 500 * _NM, _TERRAIN), points=front_points
    )
    game.theater.conflicts.return_value = [front]
    return game


def test_pilot_near_one_end_of_a_long_front_gets_the_hostile_survival_time() -> None:
    game = _survival_game(
        [Point(0.0, 10 * _NM, _TERRAIN), Point(0.0, 200 * _NM, _TERRAIN)]
    )

    turns = CsarService(game)._survival_turns(Point(0.0, 0.0, _TERRAIN), Player.BLUE)

    assert turns == 2


def test_pilot_far_from_the_whole_front_gets_the_normal_survival_time() -> None:
    game = _survival_game(
        [Point(0.0, 100 * _NM, _TERRAIN), Point(0.0, 200 * _NM, _TERRAIN)]
    )

    turns = CsarService(game)._survival_turns(Point(0.0, 0.0, _TERRAIN), Player.BLUE)

    assert turns == 3

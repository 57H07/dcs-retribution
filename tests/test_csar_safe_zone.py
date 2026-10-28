"""CSAR-01.4: pilots who come down in a safe zone are recovered without a rescue.

Safe means on land, over friendly territory, far enough from the enemy's threat
zones and from every front line. Off by default; when off, the normal downed-pilot
flow applies.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import MagicMock, patch

from dcs.mapping import Point
from dcs.terrain import Terrain
from shapely.geometry import Polygon

from game.squadrons.csarservice import CsarService
from game.squadrons.downedpilot import DownedPilot
from game.squadrons.pilot import Pilot, PilotStatus
from game.theater.player import Player
from game.threatzones import ThreatZones
from game.utils import nautical_miles

_TERRAIN = MagicMock(spec=Terrain)

#: An enemy SAM ring: a square 20 nm wide centred 100 nm east of the origin.
_NM = nautical_miles(1).meters


def _square(center_x: float, half_width: float) -> Polygon:
    return Polygon(
        [
            (center_x - half_width, -half_width),
            (center_x + half_width, -half_width),
            (center_x + half_width, half_width),
            (center_x - half_width, half_width),
        ]
    )


def _game(
    *,
    enabled: bool = True,
    threat_distance: int = 10,
    front_distance: int = 30,
    friendly_territory: bool = True,
    at_sea: bool = False,
    front_line_x: Optional[float] = None,
    threat: Optional[Polygon] = None,
) -> Any:
    game = MagicMock()
    game.turn = 5
    game.settings = SimpleNamespace(
        csar_enabled=True,
        csar_enabled_red=True,
        # The base radius is a separate mechanism; keep it out of the way.
        csar_control_point_radius=0,
        csar_safe_zone_recovery=enabled,
        csar_safe_zone_threat_distance=threat_distance,
        csar_safe_zone_front_line_distance=front_distance,
        csar_survival_turns=3,
        csar_survival_turns_hostile=2,
        csar_ai_recovery_turns=2,
        csar_player_recovery_turns=1,
    )
    theater = game.theater
    theater.terrain = _TERRAIN
    theater.is_in_sea.return_value = at_sea
    theater.closest_control_point.return_value.is_friendly.return_value = (
        friendly_territory
    )
    if front_line_x is None:
        theater.conflicts.return_value = []
    else:
        front = SimpleNamespace(
            position=Point(front_line_x, 0.0, _TERRAIN),
            points=[
                Point(front_line_x, -50 * _NM, _TERRAIN),
                Point(front_line_x, 50 * _NM, _TERRAIN),
            ],
        )
        theater.conflicts.return_value = [front]

    empty = Polygon()
    zones = ThreatZones(theater, empty, threat if threat is not None else empty, empty)
    game.threat_zone_for.return_value = zones
    return game


def _down(game: Any, x_nm: float = 0.0, was_player: bool = False) -> Any:
    pilot = Pilot("Maverick")
    squadron = MagicMock()
    squadron.player = Player.BLUE
    squadron.aircraft.display_name = "F-16C"
    squadron.coalition.downed_pilots = []
    flight = MagicMock()
    flight.squadron = squadron
    with patch(
        "game.squadrons.csarservice.find_downed_pilot_position",
        side_effect=lambda _theater, near: near,
    ):
        result = CsarService(game).down_pilot(
            flight, pilot, was_player, Point(x_nm * _NM, 0.0, _TERRAIN)
        )
    return pilot, result, squadron


def test_pilot_down_in_a_safe_zone_is_recovered() -> None:
    game = _game(front_line_x=200 * _NM, threat=_square(100 * _NM, 10 * _NM))

    pilot, result, squadron = _down(game)

    assert result is None
    assert pilot.status is PilotStatus.Recovering
    assert pilot.turns_until_available == 2  # csar_ai_recovery_turns
    assert squadron.coalition.downed_pilots == []
    game.threat_zone_for.assert_called_with(Player.RED)


def test_player_pilot_recovered_in_a_safe_zone_uses_the_player_turns() -> None:
    pilot, _, _ = _down(_game(), was_player=True)

    assert pilot.turns_until_available == 1  # csar_player_recovery_turns


def test_pilot_down_near_the_front_stays_downed() -> None:
    game = _game(front_line_x=20 * _NM)

    pilot, result, squadron = _down(game)

    assert isinstance(result, DownedPilot)
    assert pilot.status is PilotStatus.Downed
    assert result in squadron.coalition.downed_pilots


def test_front_line_is_measured_along_its_length_not_to_its_midpoint() -> None:
    """The front line's ends are 50 nm from its centre: a pilot level with one end
    is right next to the line even though its midpoint is far away."""
    game = _game(front_line_x=5 * _NM)
    front = game.theater.conflicts.return_value[0]
    front.position = Point(0.0, 60 * _NM, _TERRAIN)
    front.points = [
        Point(0.0, 10 * _NM, _TERRAIN),
        Point(0.0, 110 * _NM, _TERRAIN),
    ]

    _, result, _ = _down(game)

    assert result is not None


def test_pilot_down_inside_a_threat_zone_stays_downed() -> None:
    game = _game(threat=_square(0.0, 10 * _NM))

    _, result, _ = _down(game)

    assert result is not None


def test_pilot_down_too_close_to_a_threat_zone_stays_downed() -> None:
    # Zone edge at 5 nm, threshold 10 nm.
    game = _game(threat=_square(15 * _NM, 10 * _NM))

    _, result, _ = _down(game)

    assert result is not None


def test_zero_threat_distance_only_requires_being_outside_the_zone() -> None:
    game = _game(threat_distance=0, threat=_square(15 * _NM, 10 * _NM))

    pilot, result, _ = _down(game)

    assert result is None
    assert pilot.recovering


def test_pilot_down_over_enemy_territory_stays_downed() -> None:
    _, result, _ = _down(_game(friendly_territory=False))

    assert result is not None


def test_pilot_down_at_sea_stays_downed() -> None:
    _, result, _ = _down(_game(at_sea=True))

    assert result is not None


def test_disabled_setting_keeps_the_normal_flow() -> None:
    pilot, result, _ = _down(_game(enabled=False))

    assert result is not None
    assert pilot.downed


def test_safe_zone_recovery_is_off_by_default() -> None:
    from game.settings import Settings

    assert Settings().csar_safe_zone_recovery is False

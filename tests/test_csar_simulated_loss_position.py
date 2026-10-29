"""Where the pilot of a loss with no DCS-reported ejection comes down.

Regression for simulated/auto-resolved turns turning almost every downed pilot
into a prisoner of war: the fallback position used to be the flight's target,
which is usually inside an enemy base's control point radius.
"""

from __future__ import annotations

import random
from types import SimpleNamespace
from typing import Any, Iterator
from unittest.mock import MagicMock, patch

import pytest
from dcs.mapping import Point
from dcs.terrain import Terrain

from game.ato.flightstate.killed import Killed
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.squadrons.csarservice import CsarService
from game.squadrons.pilot import Pilot
from game.theater.player import Player
from game.utils import nautical_miles

_TERRAIN = MagicMock(spec=Terrain)

#: The enemy airbase the strike is aimed at, and the target 3 nm from it.
ENEMY_BASE = Point(0.0, 0.0, _TERRAIN)
TARGET = Point(nautical_miles(3).meters, 0.0, _TERRAIN)
#: The flight's home base, 120 nm away.
HOME = Point(nautical_miles(120).meters, 0.0, _TERRAIN)


@pytest.fixture(autouse=True)
def _seeded() -> Iterator[None]:
    state = random.getstate()
    random.seed(1234)
    yield
    random.setstate(state)


def _control_point(name: str, position: Point, friendly_to_blue: bool) -> Any:
    cp = MagicMock()
    cp.name = name
    cp.id = name
    cp.position = position
    cp.is_friendly.side_effect = lambda player: player.is_blue == friendly_to_blue
    return cp


def _game() -> Any:
    game = MagicMock()
    game.settings = SimpleNamespace(
        invulnerable_player_pilots=False,
        csar_enabled=True,
        csar_enabled_red=True,
        csar_ejection_chance=100,
        csar_control_point_radius=15,
        csar_safe_zone_recovery=False,
        csar_capture_radius=30,
        csar_survival_turns=3,
        csar_survival_turns_hostile=2,
        csar_ai_recovery_turns=2,
        csar_player_recovery_turns=1,
        csar_prisoners_of_war=True,
        csar_rescue_ai_pilots=True,
    )
    game.turn = 5
    game.pilots_captured_this_turn = []
    bases = [
        _control_point("Enemy AB", ENEMY_BASE, friendly_to_blue=False),
        _control_point("Home AB", HOME, friendly_to_blue=True),
    ]
    game.theater.closest_control_point.side_effect = lambda pos: min(
        bases, key=lambda cp: cp.position.distance_to_point(pos)
    )
    game.theater.conflicts.return_value = []
    game.theater.is_in_sea.return_value = False
    return game


def _flight(game: Any) -> Any:
    flight = MagicMock()
    flight.squadron.player = Player.BLUE
    flight.squadron.aircraft.display_name = "F-16CM"
    flight.squadron.coalition.downed_pilots = []
    flight.package.target.position = TARGET
    flight.arrival.position = HOME
    # Not shot down by the aircraft simulation: no known position.
    flight.state = MagicMock()
    return flight


def _lose(
    game: Any, flight: Any, ejection: Point | None = None, count: int = 1
) -> list[Pilot]:
    processor = MissionResultsProcessor(game)
    csar = CsarService(game)
    pilots = []
    with patch(
        "game.squadrons.csarservice.find_downed_pilot_position",
        side_effect=lambda theater, position: position,
    ):
        for n in range(count):
            pilot = Pilot(f"Pilot {n}")
            debriefing = MagicMock()
            debriefing.ejected_pilot_positions = (
                {} if ejection is None else {id(pilot): ejection}
            )
            loss = SimpleNamespace(pilot=pilot, flight=flight)
            processor._process_lost_pilot(loss, debriefing, csar)
            pilots.append(pilot)
    return pilots


def test_simulated_loss_next_to_an_enemy_airbase_is_not_always_a_prisoner() -> None:
    game = _game()
    pilots = _lose(game, _flight(game), count=200)

    prisoners = sum(p.prisoner_of_war for p in pilots)
    downed = sum(p.downed for p in pilots)
    assert prisoners < len(pilots) // 2
    assert downed > len(pilots) // 2


def test_fallback_position_lies_on_the_way_home_from_the_target() -> None:
    game = _game()
    flight = _flight(game)
    csar = CsarService(game)
    reach = nautical_miles(40).meters + 5000

    for _ in range(100):
        position = csar.fallback_position_for(flight)
        assert position.distance_to_point(TARGET) <= reach
        # Never beyond the target, away from home.
        assert position.x >= TARGET.x - 5000


def test_fallback_position_of_a_flight_with_no_route_home_stays_at_target() -> None:
    game = _game()
    flight = _flight(game)
    flight.arrival.position = TARGET

    position = CsarService(game).fallback_position_for(flight)

    assert position.distance_to_point(TARGET) <= 5000


def test_flight_shot_down_by_the_simulation_comes_down_where_it_was_hit() -> None:
    game = _game()
    flight = _flight(game)
    shot_down_at = Point(nautical_miles(60).meters, 0.0, _TERRAIN)
    flight.state = Killed(shot_down_at, flight, MagicMock())

    pilots = _lose(game, flight, count=50)

    assert all(p.downed for p in pilots)
    for downed in flight.squadron.coalition.downed_pilots:
        # At most 20 nm toward home (plus the 2 km scatter), never away from it.
        assert downed.position.distance_to_point(shot_down_at) <= (
            nautical_miles(20).meters + 2000
        )
        assert downed.position.x >= shot_down_at.x - 2000


def test_flight_shot_down_by_the_simulation_over_an_enemy_base_can_be_captured() -> (
    None
):
    """The better estimate still captures pilots who really came down on top of
    an enemy base -- just not every one of them."""
    game = _game()
    flight = _flight(game)
    flight.state = Killed(ENEMY_BASE, flight, MagicMock())

    pilots = _lose(game, flight, count=100)

    prisoners = sum(p.prisoner_of_war for p in pilots)
    assert 0 < prisoners < len(pilots)


def test_real_ejection_position_is_kept() -> None:
    """In-mission ejections keep the DCS position, whatever the flight state."""
    game = _game()
    flight = _flight(game)
    flight.state = Killed(HOME, flight, MagicMock())

    (pilot,) = _lose(game, flight, ejection=ENEMY_BASE)

    assert pilot.prisoner_of_war

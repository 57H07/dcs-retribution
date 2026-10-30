"""WEB-08.1: read models and routes of the reports screen (Intel, Stats, Finances)."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from game.models.game_stats import GameStats, GameTurnMetadata
from game.server import GameContext
from game.server.reports.models import (
    CoalitionFinancesJs,
    CoalitionIntelJs,
    FinancesJs,
    IntelJs,
    StatsJs,
)
from game.theater.player import Player
from tests.server.test_command_view_commands import _request


@dataclass(frozen=True)
class _UnitType:
    display_name: str


def _unit(name: str) -> _UnitType:
    return _UnitType(name)


F16 = _unit("F-16CM")
A10 = _unit("A-10C")
MIG29 = _unit("MiG-29S")
ABRAMS = _unit("M1A2 Abrams")
BRADLEY = _unit("M2A2 Bradley")
T72 = _unit("T-72B")


def _tgo(name: str, category: str, alive: int, dead: int = 0) -> Any:
    statics = [SimpleNamespace(alive=True)] * alive
    statics += [SimpleNamespace(alive=False)] * dead
    return SimpleNamespace(obj_name=name, category=category, statics=statics)


class _ControlPoint:
    def __init__(
        self,
        name: str,
        captured: Player,
        aircraft: dict[Any, int] | None = None,
        armor: dict[Any, int] | None = None,
        income: float = 0,
        ground_objects: list[Any] | None = None,
    ) -> None:
        self.id = uuid4()
        self.name = name
        self.captured = captured
        self._aircraft = aircraft or {}
        self.base = SimpleNamespace(armor=armor or {})
        self.income_per_turn = income
        self.ground_objects = ground_objects or []
        self.parking_asked: list[Any] = []

    def allocated_aircraft(self, parking_type: Any) -> Any:
        self.parking_asked.append(parking_type)
        return SimpleNamespace(present=self._aircraft)


def _turn(fa: int, ea: int, fv: int, ev: int) -> GameTurnMetadata:
    data = GameTurnMetadata()
    data.allied_units.aircraft_count = fa
    data.enemy_units.aircraft_count = ea
    data.allied_units.vehicles_count = fv
    data.enemy_units.vehicles_count = ev
    return data


def _game() -> Any:
    incirlik = _ControlPoint(
        "Incirlik",
        Player.BLUE,
        aircraft={F16: 12, A10: 4, MIG29: 0},
        armor={BRADLEY: 3, ABRAMS: 5},
        income=20,
        ground_objects=[
            _tgo("Ammo depot", "ammo", alive=3, dead=1),
            _tgo("Oil field", "oil", alive=2),
            _tgo("SAM site", "aa", alive=4),
        ],
    )
    empty = _ControlPoint("Carrier", Player.BLUE, income=0)
    farp = _ControlPoint(
        "FARP Alpha", Player.BLUE, armor={ABRAMS: 2}, income=5, ground_objects=[]
    )
    hama = _ControlPoint(
        "Hama",
        Player.RED,
        aircraft={MIG29: 8},
        armor={T72: 10},
        income=10,
        ground_objects=[_tgo("Village", "village", alive=4)],
    )
    points = [incirlik, empty, farp, hama]
    stats = GameStats()
    stats.data_per_turn = [_turn(20, 12, 10, 14), _turn(16, 8, 8, 10)]
    return SimpleNamespace(
        theater=SimpleNamespace(
            control_points_for=lambda player: (
                cp for cp in points if cp.captured is player
            )
        ),
        settings=SimpleNamespace(
            player_income_multiplier=1.5, enemy_income_multiplier=1.0
        ),
        coalition_for=lambda player: SimpleNamespace(
            budget=812.5 if player is Player.BLUE else 300.0
        ),
        game_stats=stats,
        points=points,
    )


# --- Intel -------------------------------------------------------------------


def test_intel_lists_bases_with_units_sorted_by_name() -> None:
    game = _game()
    intel = CoalitionIntelJs.from_game(game, Player.BLUE)
    incirlik, _, farp, _ = game.points

    assert intel.aircraft.total == 16
    [base] = intel.aircraft.bases
    assert (base.id, base.name, base.total) == (str(incirlik.id), "Incirlik", 16)
    # Zero counts are skipped, as in the Qt window.
    assert [(u.name, u.count) for u in base.units] == [("A-10C", 4), ("F-16CM", 12)]

    assert intel.ground.total == 10
    assert [(b.name, b.total) for b in intel.ground.bases] == [
        ("Incirlik", 8),
        ("FARP Alpha", 2),
    ]
    assert [u.name for u in intel.ground.bases[0].units] == [
        "M1A2 Abrams",
        "M2A2 Bradley",
    ]


def test_intel_counts_every_parking_type() -> None:
    game = _game()
    CoalitionIntelJs.from_game(game, Player.BLUE)
    [parking] = game.points[0].parking_asked
    assert parking.include_fixed_wing
    assert parking.include_fixed_wing_stol
    assert parking.include_rotary_wing


def test_intel_covers_both_coalitions() -> None:
    intel = IntelJs.from_game(_game())
    assert intel.friendly.aircraft.total == 16
    assert intel.enemy.aircraft.total == 8
    assert [b.name for b in intel.enemy.ground.bases] == ["Hama"]


# --- Finances ----------------------------------------------------------------


def test_finances_break_income_down_by_base_and_building() -> None:
    finances = CoalitionFinancesJs.from_game(_game(), Player.BLUE)
    assert finances.budget == 812.5
    assert finances.multiplier == 1.5
    # Bases with income only, highest first.
    assert [(b.name, b.income) for b in finances.bases] == [
        ("Incirlik", 20),
        ("FARP Alpha", 5),
    ]
    # Rewarding buildings only (no SAM), counting the alive statics.
    assert [
        (b.name, b.category, b.count, b.income_per_building, b.income)
        for b in finances.buildings
    ] == [
        ("Oil field", "oil", 2, 10, 20),
        ("Ammo depot", "ammo", 3, 2, 6),
    ]
    assert finances.from_bases == 25
    assert finances.from_buildings == 26
    assert finances.total == pytest.approx((25 + 26) * 1.5)


def test_enemy_finances_use_the_enemy_multiplier() -> None:
    finances = FinancesJs.from_game(_game())
    assert finances.enemy.budget == 300
    assert finances.enemy.multiplier == 1.0
    assert finances.enemy.total == pytest.approx(10 + 4 * 0.25)


# --- Stats -------------------------------------------------------------------


def test_stats_list_each_recorded_turn() -> None:
    stats = StatsJs.from_game(_game())
    assert [t.model_dump() for t in stats.turns] == [
        {
            "turn": 0,
            "friendly_aircraft": 20,
            "enemy_aircraft": 12,
            "friendly_vehicles": 10,
            "enemy_vehicles": 14,
        },
        {
            "turn": 1,
            "friendly_aircraft": 16,
            "enemy_aircraft": 8,
            "friendly_vehicles": 8,
            "enemy_vehicles": 10,
        },
    ]


# --- Routes ------------------------------------------------------------------


def _load(monkeypatch: pytest.MonkeyPatch, game: Any) -> None:
    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(game=game, sim_controller=None),
        raising=False,
    )


@pytest.mark.parametrize("report", ["intel", "stats", "finances"])
def test_routes_are_null_without_a_campaign(
    report: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load(monkeypatch, None)
    assert _request("GET", f"/reports/{report}") == (200, None)


def test_routes_serve_the_read_models(monkeypatch: pytest.MonkeyPatch) -> None:
    game = _game()
    _load(monkeypatch, game)

    status, intel = _request("GET", "/reports/intel")
    assert status == 200
    assert intel["friendly"]["aircraft"]["bases"][0]["units"][0] == {
        "name": "A-10C",
        "count": 4,
    }
    assert intel["enemy"]["ground"]["total"] == 10

    status, stats = _request("GET", "/reports/stats")
    assert status == 200
    assert [t["friendly_aircraft"] for t in stats["turns"]] == [20, 16]

    status, finances = _request("GET", "/reports/finances")
    assert status == 200
    assert finances["friendly"]["budget"] == 812.5
    assert finances["friendly"]["buildings"][0]["name"] == "Oil field"

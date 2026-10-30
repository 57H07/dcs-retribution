"""Reports screen (WEB-08.1): read models of the Intel, Stats and Finances windows.

Same figures as `IntelWindow` (`qt_ui/windows/intel.py`), `QStatsWindow`
(`qt_ui/windows/stats/`) and `QFinancesMenu` (`qt_ui/windows/finances/`), computed
here so that the client only lays them out (spec §0 rule 1).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel

from game.income import Income
from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint


class _Named(Protocol):
    @property
    def display_name(self) -> str: ...


class UnitCountJs(BaseModel):
    name: str
    count: int


class BaseForcesJs(BaseModel):
    """Units present at one base, sorted by name."""

    id: str
    name: str
    total: int
    units: list[UnitCountJs]


class ForcesJs(BaseModel):
    """Bases holding at least one unit, in theater order, and the coalition total."""

    total: int
    bases: list[BaseForcesJs]

    @staticmethod
    def from_bases(
        bases: Iterable[tuple[ControlPoint, Iterable[tuple[_Named, int]]]],
    ) -> ForcesJs:
        rows: list[BaseForcesJs] = []
        for control_point, units in bases:
            counts = sorted(
                (
                    UnitCountJs(name=unit.display_name, count=count)
                    for unit, count in units
                    if count
                ),
                key=lambda u: u.name,
            )
            total = sum(u.count for u in counts)
            if total:
                rows.append(
                    BaseForcesJs(
                        id=str(control_point.id),
                        name=control_point.name,
                        total=total,
                        units=counts,
                    )
                )
        return ForcesJs(total=sum(b.total for b in rows), bases=rows)


class CoalitionIntelJs(BaseModel):
    """The "Air forces" and "Ground forces" tabs of the Qt intel window."""

    aircraft: ForcesJs
    ground: ForcesJs

    @staticmethod
    def from_game(game: Game, player: Player) -> CoalitionIntelJs:
        from game.theater import ParkingType

        parking = ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)
        control_points = list(game.theater.control_points_for(player))
        return CoalitionIntelJs(
            aircraft=ForcesJs.from_bases(
                (cp, cp.allocated_aircraft(parking).present.items())
                for cp in control_points
            ),
            ground=ForcesJs.from_bases(
                (cp, cp.base.armor.items()) for cp in control_points
            ),
        )


class IntelJs(BaseModel):
    friendly: CoalitionIntelJs
    enemy: CoalitionIntelJs

    @staticmethod
    def from_game(game: Game) -> IntelJs:
        return IntelJs(
            friendly=CoalitionIntelJs.from_game(game, Player.BLUE),
            enemy=CoalitionIntelJs.from_game(game, Player.RED),
        )


class BaseIncomeJs(BaseModel):
    id: str
    name: str
    income: float


class BuildingIncomeJs(BaseModel):
    name: str
    category: str
    count: int
    income_per_building: float
    income: float


class CoalitionFinancesJs(BaseModel):
    """`FinancesLayout`: income per base and per building, multiplier and balance.

    Bases and buildings come sorted by income, highest first.
    """

    budget: float
    multiplier: float
    from_bases: float
    from_buildings: float
    total: float
    bases: list[BaseIncomeJs]
    buildings: list[BuildingIncomeJs]

    @staticmethod
    def from_game(game: Game, player: Player) -> CoalitionFinancesJs:
        income = Income(game, player)
        bases = sorted(
            income.control_points, key=lambda cp: cp.income_per_turn, reverse=True
        )
        buildings = sorted(income.buildings, key=lambda b: b.income, reverse=True)
        return CoalitionFinancesJs(
            budget=game.coalition_for(player).budget,
            multiplier=income.multiplier,
            from_bases=income.from_bases,
            from_buildings=income.total_buildings,
            total=income.total,
            bases=[
                BaseIncomeJs(id=str(cp.id), name=cp.name, income=cp.income_per_turn)
                for cp in bases
            ],
            buildings=[
                BuildingIncomeJs(
                    name=b.name,
                    category=b.category,
                    count=b.number,
                    income_per_building=b.income_per_building,
                    income=b.income,
                )
                for b in buildings
            ],
        )


class FinancesJs(BaseModel):
    """Finances of the player, and of the enemy (the "Economy" intel tab)."""

    friendly: CoalitionFinancesJs
    enemy: CoalitionFinancesJs

    @staticmethod
    def from_game(game: Game) -> FinancesJs:
        return FinancesJs(
            friendly=CoalitionFinancesJs.from_game(game, Player.BLUE),
            enemy=CoalitionFinancesJs.from_game(game, Player.RED),
        )


class TurnStatsJs(BaseModel):
    turn: int
    friendly_aircraft: int
    enemy_aircraft: int
    friendly_vehicles: int
    enemy_vehicles: int


class StatsJs(BaseModel):
    """Aircraft and combat vehicle counts recorded at each turn (`GameStats`)."""

    turns: list[TurnStatsJs]

    @staticmethod
    def from_game(game: Game) -> StatsJs:
        return StatsJs(
            turns=[
                TurnStatsJs(
                    turn=index,
                    friendly_aircraft=data.allied_units.aircraft_count,
                    enemy_aircraft=data.enemy_units.aircraft_count,
                    friendly_vehicles=data.allied_units.vehicles_count,
                    enemy_vehicles=data.enemy_units.vehicles_count,
                )
                for index, data in enumerate(game.game_stats.data_per_turn)
            ]
        )

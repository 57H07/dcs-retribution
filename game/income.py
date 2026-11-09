from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from game.config import REWARDS
from game.objectives import capped_income_bonus
from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game


@dataclass(frozen=True)
class BuildingIncome:
    name: str
    category: str
    number: int
    income_per_building: float

    @property
    def income(self) -> float:
        return self.number * self.income_per_building


class Income:
    def __init__(
        self, game: Game, player: Player, paid_at_turn: Optional[int] = None
    ) -> None:
        """The income `player` gets at the end of a turn.

        Args:
            paid_at_turn: `Game.turn` when it is paid, which decides the objective
                bonuses (#194); by default the next payment.
        """
        if player.is_blue:
            self.multiplier = game.settings.player_income_multiplier
        else:
            self.multiplier = game.settings.enemy_income_multiplier
        self.control_points = []
        self.buildings = []

        for cp in game.theater.control_points_for(player):
            if cp.income_per_turn:
                self.control_points.append(cp)

            for tgo in cp.ground_objects:
                if tgo.category not in REWARDS:
                    continue
                self.buildings.append(
                    BuildingIncome(
                        tgo.obj_name,
                        tgo.category,
                        sum(1 for b in tgo.statics if b.alive),
                        REWARDS[tgo.category],
                    )
                )

        self.from_bases = sum(cp.income_per_turn for cp in self.control_points)
        self.total_buildings = sum(b.income for b in self.buildings)
        #: Before the objective bonuses (#194), which are capped against it.
        self.base: float = (self.total_buildings + self.from_bases) * self.multiplier
        if paid_at_turn is None:
            paid_at_turn = game.turn + 1
        self.from_objectives = capped_income_bonus(
            game, player, paid_at_turn, self.base
        )
        self.total = max(self.base + self.from_objectives, 0)

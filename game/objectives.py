"""Campaign objectives (#194): optional goals a campaign sets in its YAML.

They never decide the end of the campaign, which stays "take every enemy base".
A met objective grants its reward; a missed one costs nothing. Rewards are
capped against the coalition's income so that a campaign cannot hand out too
much: see the ``*_CAP`` constants and docs/campaigns/objectives.md.

The objectives are read once, when the campaign is generated, and kept on the
game: a save does not need its campaign file to go on.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Optional
from uuid import UUID

from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game
    from game.squadrons import Squadron
    from game.theater import ControlPoint, TheaterGroundObject

#: An immediate budget is at most this many turns of the coalition's income.
BUDGET_CAP_TURNS = 2.0
#: An income bonus (or cut) is at most this share of the coalition's income...
INCOME_CAP_SHARE = 0.25
#: ...and all the bonuses (or cuts) paid in one turn at most this share.
TOTAL_INCOME_CAP_SHARE = 0.5
#: Aircraft and pilots given by one objective.
REINFORCEMENTS_CAP = 4

#: The category of a destroy objective for every air defence site, radar and IADS
#: node on land, besides the categories of the ground objects.
IADS = "iads"


class ObjectiveKind(Enum):
    CAPTURE = "capture"
    HOLD = "hold"
    DESTROY = "destroy"
    SURVIVE = "survive"


class ObjectiveState(Enum):
    IN_PROGRESS = "In progress"
    MET = "Met"
    MISSED = "Missed"


@dataclass(frozen=True)
class ObjectiveReward:
    budget: float = 0
    income: float = 0
    #: Turns the income bonus lasts; None for the rest of the campaign.
    income_turns: Optional[int] = None
    aircraft: int = 0
    pilots: int = 0
    #: The squadron that receives the aircraft and pilots.
    squadron: Optional[str] = None
    enemy_budget: float = 0
    enemy_income: float = 0
    enemy_income_turns: Optional[int] = None

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.budget,
                self.income,
                self.aircraft,
                self.pilots,
                self.enemy_budget,
                self.enemy_income,
            )
        )

    def describe(self) -> str:
        """What the campaign promises, before the caps."""
        parts = []
        if self.budget:
            parts.append(f"+{_money(self.budget)} budget")
        if self.income:
            parts.append(f"+{_money(self.income)} income{_for(self.income_turns)}")
        if self.aircraft:
            parts.append(f"{self.aircraft} aircraft for {self.squadron}")
        if self.pilots:
            parts.append(f"{self.pilots} pilots for {self.squadron}")
        if self.enemy_budget:
            parts.append(f"-{_money(self.enemy_budget)} enemy budget")
        if self.enemy_income:
            parts.append(
                f"-{_money(self.enemy_income)} enemy income"
                f"{_for(self.enemy_income_turns)}"
            )
        return ", ".join(parts)


@dataclass
class IncomeBonus:
    """Income added to (or, negative, taken from) a coalition each turn."""

    player: Player
    amount: float
    #: The first and last turns it is paid, as `Game.turn` reads when the income
    #: is paid (`Coalition.end_turn`). No last turn: until the end.
    first_turn: int
    last_turn: Optional[int]
    source: str

    def paid_at(self, turn: int) -> bool:
        return self.first_turn <= turn and (
            self.last_turn is None or turn <= self.last_turn
        )


@dataclass
class CampaignObjective:
    title: str
    kind: ObjectiveKind
    #: The base, ground object or category, as the player reads it.
    target: str
    #: Capture: the last turn to take it. Hold and survive: the turn to reach.
    deadline: Optional[int]
    reward: ObjectiveReward = field(default_factory=ObjectiveReward)
    control_point_id: Optional[UUID] = None
    #: Destroy: the enemy ground objects to destroy. Survive: the friendly one.
    ground_object_ids: list[UUID] = field(default_factory=list)
    state: ObjectiveState = ObjectiveState.IN_PROGRESS
    resolved_turn: Optional[int] = None
    #: What the reward actually gave, after the caps.
    granted: str = ""


@dataclass
class CampaignObjectives:
    objectives: list[CampaignObjective] = field(default_factory=list)
    income_bonuses: list[IncomeBonus] = field(default_factory=list)

    def income_bonus(self, player: Player, turn: int) -> float:
        """The objective income paid to `player` at the end of `turn`, uncapped."""
        return sum(
            b.amount
            for b in self.income_bonuses
            if b.player is player and b.paid_at(turn)
        )


@dataclass(frozen=True)
class Progress:
    """How far an objective in progress is."""

    #: Destroy: ground objects destroyed, out of `total`.
    done: Optional[int] = None
    total: Optional[int] = None
    #: Turns left before the deadline, this one included.
    turns_left: Optional[int] = None


# --- loading -------------------------------------------------------------------


class InvalidObjective(ValueError):
    pass


def load(
    raw: Any, game: Game, miz_names: Optional[Mapping[UUID, str]] = None
) -> CampaignObjectives:
    """The campaign's `objectives:` YAML section; bad entries are logged and skipped.

    Args:
        miz_names: the name of each base in the campaign's .miz, by base id: the
            generation renames some (carriers take a name of the faction).
    """
    loaded = CampaignObjectives()
    if not raw:
        return loaded
    if not isinstance(raw, list):
        logging.warning("Campaign objectives must be a list, ignoring them")
        return loaded
    for index, entry in enumerate(raw, start=1):
        try:
            loaded.objectives.append(_objective(entry, game, miz_names or {}))
        except InvalidObjective as error:
            logging.warning(f"Campaign objective {index} ignored: {error}")
    return loaded


def _objective(
    entry: Any, game: Game, miz_names: Mapping[UUID, str]
) -> CampaignObjective:
    if not isinstance(entry, dict):
        raise InvalidObjective("an objective is a mapping")
    kinds = [k for k in ObjectiveKind if k.value in entry]
    if len(kinds) != 1:
        raise InvalidObjective(
            "it needs exactly one of " + ", ".join(k.value for k in ObjectiveKind)
        )
    [kind] = kinds
    value = entry[kind.value]
    reward = _reward(entry.get("reward") or {})
    if kind is ObjectiveKind.CAPTURE:
        cp = _control_point(game, value, miz_names)
        if cp.captured.is_blue:
            raise InvalidObjective(f"{cp.name} is already the player's")
        objective = CampaignObjective(
            f"Capture {cp.name}",
            kind,
            cp.name,
            _turn(entry, "by_turn", required=False),
            control_point_id=cp.id,
        )
    elif kind is ObjectiveKind.HOLD:
        cp = _control_point(game, value, miz_names)
        if not cp.captured.is_blue:
            raise InvalidObjective(f"{cp.name} is not the player's")
        objective = CampaignObjective(
            f"Hold {cp.name}",
            kind,
            cp.name,
            _turn(entry, "until_turn", required=True),
            control_point_id=cp.id,
        )
    elif kind is ObjectiveKind.DESTROY:
        target, targets = _destroy_targets(game, value, miz_names)
        objective = CampaignObjective(
            f"Destroy {target}",
            kind,
            target,
            _turn(entry, "by_turn", required=False),
            ground_object_ids=[t.id for t in targets],
        )
    else:
        until = _turn(entry, "until_turn", required=True)
        objective = _survive(game, value, until, miz_names)
    objective.reward = reward
    if entry.get("title"):
        objective.title = str(entry["title"])
    return objective


def _named(
    game: Game, name: Any, miz_names: Mapping[UUID, str]
) -> Optional[ControlPoint]:
    for cp in game.theater.controlpoints:
        if name in (cp.name, miz_names.get(cp.id)):
            return cp
    return None


def _control_point(
    game: Game, name: Any, miz_names: Mapping[UUID, str]
) -> ControlPoint:
    if (cp := _named(game, name, miz_names)) is not None:
        return cp
    raise InvalidObjective(f"no base named {name!r}")


def _turn(entry: dict[str, Any], key: str, required: bool) -> Optional[int]:
    value = entry.get(key)
    if value is None:
        if required:
            raise InvalidObjective(f"it needs {key}")
        return None
    if not isinstance(value, int) or value < 1:
        raise InvalidObjective(f"{key} must be a turn number")
    return value


def _destroy_targets(
    game: Game, value: Any, miz_names: Mapping[UUID, str]
) -> tuple[str, list[TheaterGroundObject]]:
    if isinstance(value, str):
        named = [
            tgo
            for tgo in game.theater.ground_objects
            if tgo.original_name == value and tgo.control_point.captured.is_red
        ]
        if not named:
            raise InvalidObjective(f"no enemy ground object named {value!r}")
        return value, named
    if not isinstance(value, dict) or "category" not in value:
        raise InvalidObjective("destroy names a ground object or a category")
    category = str(value["category"]).lower()
    at = value.get("at")
    base = _control_point(game, at, miz_names) if at else None
    bases = [base] if base else list(game.theater.controlpoints)
    targets = [
        tgo
        for cp in bases
        if cp.captured.is_red
        for tgo in cp.ground_objects
        if _in_category(tgo, category)
    ]
    if not targets:
        raise InvalidObjective(f"no enemy ground object of category {category!r}")
    what = "the enemy IADS" if category == IADS else f"the enemy {category} sites"
    return (f"{what} at {base.name}" if base else what), targets


def _in_category(tgo: TheaterGroundObject, category: str) -> bool:
    if category == IADS:
        # Ships are part of the IADS network, but a player out to blind the air
        # defences means the land sites.
        return tgo.is_iads and not tgo.sea_object
    return tgo.category == category


def _survive(
    game: Game, value: Any, until: Optional[int], miz_names: Mapping[UUID, str]
) -> CampaignObjective:
    if (cp := _named(game, value, miz_names)) is not None:
        if not cp.captured.is_blue:
            raise InvalidObjective(f"{cp.name} is not the player's")
        return CampaignObjective(
            f"Keep {cp.name} alive",
            ObjectiveKind.SURVIVE,
            cp.name,
            until,
            control_point_id=cp.id,
        )
    named = [
        tgo
        for tgo in game.theater.ground_objects
        if tgo.original_name == value and tgo.control_point.captured.is_blue
    ]
    if not named:
        raise InvalidObjective(f"no friendly base or ground object named {value!r}")
    return CampaignObjective(
        f"Keep {value} alive",
        ObjectiveKind.SURVIVE,
        str(value),
        until,
        ground_object_ids=[t.id for t in named],
    )


def _reward(raw: Any) -> ObjectiveReward:
    if not isinstance(raw, dict):
        raise InvalidObjective("reward is a mapping")

    def number(key: str) -> float:
        value = raw.get(key, 0)
        if not isinstance(value, (int, float)) or value < 0:
            raise InvalidObjective(f"reward {key} must be a positive number")
        return float(value)

    def count(key: str) -> int:
        value = raw.get(key, 0)
        if not isinstance(value, int) or value < 0:
            raise InvalidObjective(f"reward {key} must be a positive whole number")
        return value

    def turns(key: str) -> Optional[int]:
        value = raw.get(key)
        if value is None:
            return None
        if not isinstance(value, int) or value < 1:
            raise InvalidObjective(f"reward {key} must be a number of turns")
        return value

    reward = ObjectiveReward(
        budget=number("budget"),
        income=number("income"),
        income_turns=turns("income_turns"),
        aircraft=count("aircraft"),
        pilots=count("pilots"),
        squadron=raw.get("squadron"),
        enemy_budget=number("enemy_budget"),
        enemy_income=number("enemy_income"),
        enemy_income_turns=turns("enemy_income_turns"),
    )
    if (reward.aircraft or reward.pilots) and not reward.squadron:
        raise InvalidObjective("aircraft and pilots go to a named squadron")
    return reward


# --- turn end ------------------------------------------------------------------


def end_of_turn(game: Game) -> None:
    """Resolves the objectives at the end of `game.turn`, then grants the rewards.

    Runs before the turn counter moves and before the income is paid, so that an
    income bonus is paid with this very turn's income.
    """
    for objective in game.objectives.objectives:
        if objective.state is not ObjectiveState.IN_PROGRESS:
            continue
        state = _evaluate(objective, game)
        if state is ObjectiveState.IN_PROGRESS:
            continue
        objective.state = state
        objective.resolved_turn = game.turn
        if state is ObjectiveState.MET:
            objective.granted = _grant(objective, game)
            text = f"Reward: {objective.granted}" if objective.granted else ""
            game.message(f"Objective met: {objective.title}", text)
        else:
            game.message(f"Objective missed: {objective.title}", "")


def _evaluate(objective: CampaignObjective, game: Game) -> ObjectiveState:
    turn = game.turn
    deadline = objective.deadline
    if objective.kind is ObjectiveKind.CAPTURE:
        cp = _find_control_point(game, objective.control_point_id)
        if cp is not None and cp.captured.is_blue:
            return ObjectiveState.MET
        return _too_late(turn, deadline)
    if objective.kind is ObjectiveKind.DESTROY:
        if not _remaining_targets(objective, game):
            return ObjectiveState.MET
        return _too_late(turn, deadline)
    # Hold and survive: lost at any time is missed, kept until the turn is met.
    if not _still_standing(objective, game):
        return ObjectiveState.MISSED
    if deadline is not None and turn >= deadline:
        return ObjectiveState.MET
    return ObjectiveState.IN_PROGRESS


def _too_late(turn: int, deadline: Optional[int]) -> ObjectiveState:
    if deadline is not None and turn >= deadline:
        return ObjectiveState.MISSED
    return ObjectiveState.IN_PROGRESS


def _find_control_point(game: Game, cp_id: Optional[UUID]) -> Optional[ControlPoint]:
    for cp in game.theater.controlpoints:
        if cp.id == cp_id:
            return cp
    return None


def _ground_objects(
    objective: CampaignObjective, game: Game
) -> list[TheaterGroundObject]:
    ids = set(objective.ground_object_ids)
    return [tgo for tgo in game.theater.ground_objects if tgo.id in ids]


def _remaining_targets(
    objective: CampaignObjective, game: Game
) -> list[TheaterGroundObject]:
    """The targets still alive in enemy hands: a captured one counts as destroyed."""
    return [
        tgo
        for tgo in _ground_objects(objective, game)
        if not tgo.is_dead and tgo.control_point.captured.is_red
    ]


def _still_standing(objective: CampaignObjective, game: Game) -> bool:
    if objective.control_point_id is not None:
        cp = _find_control_point(game, objective.control_point_id)
        if cp is None or not cp.captured.is_blue:
            return False
        return not cp.is_fleet or cp.runway_is_operational()
    return any(
        not tgo.is_dead and tgo.control_point.captured.is_blue
        for tgo in _ground_objects(objective, game)
    )


def progress(objective: CampaignObjective, game: Game) -> Progress:
    turns_left = None
    if objective.state is ObjectiveState.IN_PROGRESS and objective.deadline:
        turns_left = max(objective.deadline - game.turn + 1, 0)
    if objective.kind is ObjectiveKind.DESTROY:
        total = len(objective.ground_object_ids)
        done = total - len(_remaining_targets(objective, game))
        return Progress(done, total, turns_left)
    return Progress(turns_left=turns_left)


# --- rewards -------------------------------------------------------------------


def base_income(game: Game, player: Player) -> float:
    from game.income import Income

    return Income(game, player).base


def _grant(objective: CampaignObjective, game: Game) -> str:
    reward = objective.reward
    granted = []
    blue_income = base_income(game, Player.BLUE)
    red_income = base_income(game, Player.RED)
    budget = min(reward.budget, BUDGET_CAP_TURNS * blue_income)
    if budget > 0:
        game.blue.adjust_budget(budget)
        granted.append(f"+{_money(budget)} budget")
    income = min(reward.income, INCOME_CAP_SHARE * blue_income)
    if income > 0:
        _add_income(game, Player.BLUE, income, reward.income_turns, objective)
        granted.append(f"+{_money(income)} income{_for(reward.income_turns)}")
    if reward.aircraft or reward.pilots:
        granted.extend(_reinforce(game, reward))
    cut = min(
        reward.enemy_budget, BUDGET_CAP_TURNS * red_income, max(game.red.budget, 0)
    )
    if cut > 0:
        game.red.adjust_budget(-cut)
        granted.append(f"-{_money(cut)} enemy budget")
    income_cut = min(reward.enemy_income, INCOME_CAP_SHARE * red_income)
    if income_cut > 0:
        _add_income(game, Player.RED, -income_cut, reward.enemy_income_turns, objective)
        granted.append(
            f"-{_money(income_cut)} enemy income{_for(reward.enemy_income_turns)}"
        )
    return ", ".join(granted)


def _add_income(
    game: Game,
    player: Player,
    amount: float,
    turns: Optional[int],
    objective: CampaignObjective,
) -> None:
    # Paid from the income of this very turn end, where `Game.turn` is one more.
    first = game.turn + 1
    last = None if turns is None else first + turns - 1
    game.objectives.income_bonuses.append(
        IncomeBonus(player, amount, first, last, objective.title)
    )


def _reinforce(game: Game, reward: ObjectiveReward) -> list[str]:
    squadron = _squadron(game.blue.air_wing.iter_squadrons(), reward.squadron)
    if squadron is None:
        logging.warning(f"Objective reward: no squadron named {reward.squadron!r}")
        return []
    granted = []
    aircraft = min(reward.aircraft, REINFORCEMENTS_CAP, squadron.room_for_aircraft())
    if aircraft > 0:
        squadron.owned_aircraft += aircraft
        granted.append(
            f"{aircraft} {squadron.aircraft.display_name} for {squadron.name}"
        )
    pilots = min(reward.pilots, REINFORCEMENTS_CAP)
    if pilots > 0:
        squadron.add_pilots(pilots)
        granted.append(f"{pilots} pilots for {squadron.name}")
    return granted


def _squadron(squadrons: Iterable[Squadron], name: Optional[str]) -> Optional[Squadron]:
    for squadron in squadrons:
        if squadron.name == name:
            return squadron
    return None


def capped_income_bonus(game: Game, player: Player, turn: int, base: float) -> float:
    """The objective income of `player` paid at `turn`, within the total cap."""
    bonus = game.objectives.income_bonus(player, turn)
    cap = TOTAL_INCOME_CAP_SHARE * base
    return max(-cap, min(bonus, cap))


def _money(amount: float) -> str:
    return f"{amount:g}" if amount != int(amount) else str(int(amount))


def _for(turns: Optional[int]) -> str:
    if turns is None:
        return " per turn"
    return f" per turn for {turns} turn{'s' if turns > 1 else ''}"

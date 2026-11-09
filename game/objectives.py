"""Campaign objectives (#194): optional goals a campaign sets in its YAML.

They never decide the end of the campaign, which stays "take every enemy base".
A met objective grants its reward; a missed one costs nothing. The player sets
how much a reward is worth and caps it against the coalition's income, in the
"Campaign Objectives" settings, so that a campaign cannot hand out too much.

An objective targets the front: a base on the front line, or a site at one. The
ones behind the front are dropped when the campaign is read.

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
    from dcs.mapping import Point

    from game.theater import ControlPoint, TheaterGroundObject

#: The titles of the messages that announce a met or missed objective.
MET_PREFIX = "Objective met: "
MISSED_PREFIX = "Objective missed: "

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
class Target:
    """A base or ground object an objective is about, to show on the map."""

    id: UUID
    name: str
    position: Point
    #: Still to destroy, capture or keep: not destroyed nor taken yet.
    remaining: bool


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
        _check_near_front(cp)
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
        _check_near_front(cp)
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


def _near_front(cp: ControlPoint) -> bool:
    """On the front line: facing an enemy base. A fleet sails where the fight is."""
    return cp.is_fleet or cp.has_active_frontline


def _check_near_front(cp: ControlPoint) -> None:
    if not _near_front(cp):
        raise InvalidObjective(f"{cp.name} is behind the front")


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
            if tgo.original_name == value
            and tgo.control_point.captured.is_red
            and _near_front(tgo.control_point)
        ]
        if not named:
            raise InvalidObjective(f"no enemy ground object {value!r} near the front")
        return value, named
    if not isinstance(value, dict) or "category" not in value:
        raise InvalidObjective("destroy names a ground object or a category")
    category = str(value["category"]).lower()
    at = value.get("at")
    base = _control_point(game, at, miz_names) if at else None
    if base is not None:
        _check_near_front(base)
    bases = [base] if base else list(game.theater.controlpoints)
    targets = [
        tgo
        for cp in bases
        if cp.captured.is_red and _near_front(cp)
        for tgo in cp.ground_objects
        if _in_category(tgo, category)
    ]
    if not targets:
        raise InvalidObjective(
            f"no enemy ground object of category {category!r} near the front"
        )
    what = "the enemy IADS" if category == IADS else f"the enemy {category} sites"
    return (f"{what} at {base.name}" if base else f"{what} near the front"), targets


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
        _check_near_front(cp)
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
        if tgo.original_name == value
        and tgo.control_point.captured.is_blue
        and _near_front(tgo.control_point)
    ]
    if not named:
        raise InvalidObjective(
            f"no friendly base or ground object {value!r} near the front"
        )
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
            game.message(f"{MET_PREFIX}{objective.title}", text)
        else:
            game.message(f"{MISSED_PREFIX}{objective.title}", "")


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


def targets(objective: CampaignObjective, game: Game) -> list[Target]:
    """The bases or ground objects `objective` is about."""
    if objective.control_point_id is not None:
        cp = _find_control_point(game, objective.control_point_id)
        if cp is None:
            return []
        remaining = objective.kind is not ObjectiveKind.CAPTURE or cp.captured.is_red
        return [Target(cp.id, cp.name, cp.position, remaining)]
    if objective.kind is ObjectiveKind.DESTROY:
        left = {tgo.id for tgo in _remaining_targets(objective, game)}
    else:
        left = {
            tgo.id
            for tgo in _ground_objects(objective, game)
            if not tgo.is_dead and tgo.control_point.captured.is_blue
        }
    return [
        Target(tgo.id, tgo.name, tgo.position, tgo.id in left)
        for tgo in _ground_objects(objective, game)
    ]


def aimed_at(game: Game, target_id: UUID) -> list[CampaignObjective]:
    """The objectives in progress about the base or ground object `target_id`."""
    return [
        o
        for o in game.objectives.objectives
        if o.state is ObjectiveState.IN_PROGRESS
        and (o.control_point_id == target_id or target_id in o.ground_object_ids)
    ]


def is_announcement(title: str) -> bool:
    """A message of `end_of_turn` announcing a met or missed objective."""
    return title.startswith((MET_PREFIX, MISSED_PREFIX))


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


@dataclass(frozen=True)
class _Grant:
    """What a reward gives under the player's settings and the caps."""

    budget: float = 0
    income: float = 0
    income_turns: Optional[int] = None
    aircraft: int = 0
    pilots: int = 0
    squadron: Optional[Squadron] = None
    enemy_budget: float = 0
    enemy_income: float = 0
    enemy_income_turns: Optional[int] = None

    def describe(self) -> str:
        parts = []
        if self.budget > 0:
            parts.append(f"+{_money(self.budget)} budget")
        if self.income > 0:
            parts.append(f"+{_money(self.income)} income{_for(self.income_turns)}")
        if self.squadron is not None and self.aircraft > 0:
            parts.append(
                f"{self.aircraft} {self.squadron.aircraft.display_name}"
                f" for {self.squadron.name}"
            )
        if self.squadron is not None and self.pilots > 0:
            parts.append(f"{self.pilots} pilots for {self.squadron.name}")
        if self.enemy_budget > 0:
            parts.append(f"-{_money(self.enemy_budget)} enemy budget")
        if self.enemy_income > 0:
            parts.append(
                f"-{_money(self.enemy_income)} enemy income"
                f"{_for(self.enemy_income_turns)}"
            )
        return ", ".join(parts)


def _plan(objective: CampaignObjective, game: Game) -> _Grant:
    """What `objective` would grant now, under the "Campaign Objectives" settings."""
    settings = game.settings
    reward = objective.reward
    if not settings.objective_rewards:
        return _Grant()
    scale = settings.objective_reward_scale
    budget_cap = settings.objective_budget_cap_turns
    income_cap = settings.objective_income_cap / 100
    blue_income = base_income(game, Player.BLUE)
    red_income = base_income(game, Player.RED)

    budget = income = enemy_budget = enemy_income = 0.0
    if settings.objective_budget_rewards:
        budget = min(reward.budget * scale, budget_cap * blue_income)
    if settings.objective_income_rewards:
        income = min(reward.income * scale, income_cap * blue_income)
    squadron = None
    aircraft = pilots = 0
    if settings.objective_reinforcement_rewards and (reward.aircraft or reward.pilots):
        squadron = _squadron(game.blue.air_wing.iter_squadrons(), reward.squadron)
        if squadron is not None:
            cap = settings.objective_reinforcements_cap
            aircraft = min(
                int(reward.aircraft * scale), cap, squadron.room_for_aircraft()
            )
            pilots = min(int(reward.pilots * scale), cap)
    if settings.objective_enemy_penalties:
        enemy_budget = min(
            reward.enemy_budget * scale,
            budget_cap * red_income,
            max(game.red.budget, 0),
        )
        enemy_income = min(reward.enemy_income * scale, income_cap * red_income)
    return _Grant(
        budget=budget,
        income=income,
        income_turns=reward.income_turns,
        aircraft=aircraft,
        pilots=pilots,
        squadron=squadron,
        enemy_budget=enemy_budget,
        enemy_income=enemy_income,
        enemy_income_turns=reward.enemy_income_turns,
    )


def expected_reward(objective: CampaignObjective, game: Game) -> str:
    """What `objective` would grant if met now, at today's income and settings."""
    return _plan(objective, game).describe()


def _grant(objective: CampaignObjective, game: Game) -> str:
    reward = objective.reward
    grant = _plan(objective, game)
    if grant.budget > 0:
        game.blue.adjust_budget(grant.budget)
    if grant.income > 0:
        _add_income(game, Player.BLUE, grant.income, grant.income_turns, objective)
    if (
        game.settings.objective_rewards
        and game.settings.objective_reinforcement_rewards
        and (reward.aircraft or reward.pilots)
        and grant.squadron is None
    ):
        logging.warning(f"Objective reward: no squadron named {reward.squadron!r}")
    if grant.squadron is not None:
        if grant.aircraft > 0:
            grant.squadron.owned_aircraft += grant.aircraft
        if grant.pilots > 0:
            grant.squadron.add_pilots(grant.pilots)
    if grant.enemy_budget > 0:
        game.red.adjust_budget(-grant.enemy_budget)
    if grant.enemy_income > 0:
        _add_income(
            game,
            Player.RED,
            -grant.enemy_income,
            grant.enemy_income_turns,
            objective,
        )
    return grant.describe()


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


def _squadron(squadrons: Iterable[Squadron], name: Optional[str]) -> Optional[Squadron]:
    for squadron in squadrons:
        if squadron.name == name:
            return squadron
    return None


def capped_income_bonus(game: Game, player: Player, turn: int, base: float) -> float:
    """The objective income of `player` paid at `turn`, within the total cap.

    Nothing when the settings turned these rewards off since they were granted.
    """
    bonus = game.objectives.income_bonus(player, turn)
    if not bonus:
        return 0
    settings = game.settings
    if not settings.objective_rewards:
        return 0
    if player.is_blue and not settings.objective_income_rewards:
        return 0
    if not player.is_blue and not settings.objective_enemy_penalties:
        return 0
    cap = settings.objective_total_income_cap / 100 * base
    return max(-cap, min(bonus, cap))


def _money(amount: float) -> str:
    return f"{amount:g}" if amount != int(amount) else str(int(amount))


def _for(turns: Optional[int]) -> str:
    if turns is None:
        return " per turn"
    return f" per turn for {turns} turn{'s' if turns > 1 else ''}"

"""Objectives generated along the front (#210), for a campaign that defines none.

They use the kinds and rules of the campaign objectives (`game.objectives`): a
base to capture, the air defences or a strike target of a base to destroy, a base
to hold, all on the front line. At the end of each turn the generated objectives
met or missed are replaced on the front as it is then, and the ones the front has
passed are closed, neither met nor missed.

The choice is deterministic: the same theater gives the same objectives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, TYPE_CHECKING

from game.objectives import (
    IADS,
    OVERTAKEN_PREFIX,
    CampaignObjective,
    ObjectiveKind,
    ObjectiveReward,
    ObjectiveState,
    _find_control_point,
    _in_category,
    _near_front,
    _remaining_targets,
)

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint, TheaterGroundObject

#: Turns before a target of a generated objective can be picked again.
COOLDOWN = 3

#: Buildings worth a strike objective, in order of preference.
STRIKE_CATEGORIES = (
    "factory",
    "ammo",
    "fuel",
    "power",
    "commandcenter",
    "comms",
    "oil",
    "ware",
    "warehouse",
)

_CATEGORY_NAMES = {
    "factory": "factory",
    "ammo": "ammo depot",
    "fuel": "fuel depot",
    "power": "power plant",
    "commandcenter": "command center",
    "comms": "communications tower",
    "oil": "oil platform",
    "ware": "warehouse",
    "warehouse": "warehouse",
}


@dataclass(frozen=True)
class _Kind:
    name: str
    #: The objective for this base, or None when the base offers none.
    make: Callable[[Game, ControlPoint], Optional[CampaignObjective]]
    #: Enemy bases for capture and destroy, friendly ones for hold.
    enemy_base: bool


def _capture(game: Game, cp: ControlPoint) -> Optional[CampaignObjective]:
    if cp.is_fleet:
        return None
    return CampaignObjective(
        f"Capture {cp.name}",
        ObjectiveKind.CAPTURE,
        cp.name,
        game.turn + 5,
        reward=ObjectiveReward(budget=300, income=30, income_turns=5),
        control_point_id=cp.id,
    )


def _alive(
    cp: ControlPoint, wanted: Callable[[TheaterGroundObject], bool]
) -> list[TheaterGroundObject]:
    return [tgo for tgo in cp.ground_objects if not tgo.is_dead and wanted(tgo)]


def _air_defences(game: Game, cp: ControlPoint) -> Optional[CampaignObjective]:
    sites = _alive(cp, lambda tgo: _in_category(tgo, IADS))
    if not sites:
        return None
    return CampaignObjective(
        f"Blind the enemy air defences at {cp.name}",
        ObjectiveKind.DESTROY,
        f"the enemy IADS at {cp.name}",
        game.turn + 3,
        reward=ObjectiveReward(enemy_income=30, enemy_income_turns=4),
        ground_object_ids=[tgo.id for tgo in sites],
    )


def _strike(game: Game, cp: ControlPoint) -> Optional[CampaignObjective]:
    for category in STRIKE_CATEGORIES:
        sites = _alive(cp, lambda tgo: tgo.category == category)
        if sites:
            name = _CATEGORY_NAMES[category]
            return CampaignObjective(
                f"Destroy the {name} at {cp.name}",
                ObjectiveKind.DESTROY,
                f"the enemy {name} at {cp.name}",
                game.turn + 4,
                reward=ObjectiveReward(enemy_budget=300),
                ground_object_ids=[tgo.id for tgo in sites],
            )
    return None


def _hold(game: Game, cp: ControlPoint) -> Optional[CampaignObjective]:
    if cp.is_fleet:
        return None
    return CampaignObjective(
        f"Hold {cp.name}",
        ObjectiveKind.HOLD,
        cp.name,
        game.turn + 3,
        reward=ObjectiveReward(budget=150),
        control_point_id=cp.id,
    )


#: One objective of each kind before a second of any.
KINDS = (
    _Kind("capture", _capture, enemy_base=True),
    _Kind("iads", _air_defences, enemy_base=True),
    _Kind("strike", _strike, enemy_base=True),
    _Kind("hold", _hold, enemy_base=False),
)


def _front_bases(game: Game, enemy: bool) -> list[ControlPoint]:
    """The bases of one side on the front, nearest the other side first."""
    ours = [cp for cp in game.theater.controlpoints if cp.captured.is_blue]
    theirs = [cp for cp in game.theater.controlpoints if cp.captured.is_red]
    bases, facing = (theirs, ours) if enemy else (ours, theirs)

    def distance(cp: ControlPoint) -> float:
        return min(
            (cp.position.distance_to_point(other.position) for other in facing),
            default=0.0,
        )

    front = [cp for cp in bases if not cp.is_fleet and cp.has_active_frontline]
    return sorted(front, key=lambda cp: (distance(cp), cp.name))


def _key(kind: _Kind, cp: ControlPoint) -> str:
    return f"{kind.name}:{cp.id}"


def _in_progress(game: Game) -> list[CampaignObjective]:
    return [
        o for o in game.objectives.objectives if o.state is ObjectiveState.IN_PROGRESS
    ]


def _taken(game: Game) -> set[str]:
    """Keys of the objectives in progress and of those used too recently."""
    keys = {o.key for o in _in_progress(game) if o.key}
    keys.update(
        key
        for key, turn in game.objectives.recent.items()
        if game.turn - turn < COOLDOWN
    )
    return keys


def _next(game: Game, kinds: Iterable[_Kind]) -> Optional[CampaignObjective]:
    taken = _taken(game)
    # Spread along the front: a base without an objective in progress first.
    busy = {o.key.split(":", 1)[1] for o in _in_progress(game) if o.key}
    for kind in kinds:
        bases = _front_bases(game, kind.enemy_base)
        for cp in sorted(bases, key=lambda cp: str(cp.id) in busy):
            key = _key(kind, cp)
            if key in taken:
                continue
            objective = kind.make(game, cp)
            if objective is not None:
                objective.generated = True
                objective.key = key
                return objective
    return None


def _by_variety(game: Game) -> list[_Kind]:
    """The kinds with the fewest objectives in progress first."""
    counts = {
        kind.name: sum(o.key.startswith(f"{kind.name}:") for o in _in_progress(game))
        for kind in KINDS
    }
    return sorted(KINDS, key=lambda kind: counts[kind.name])


def top_up(game: Game, announce: bool = True) -> list[CampaignObjective]:
    """Adds generated objectives until the setting's count is in progress."""
    wanted = game.settings.generated_objectives_count
    added: list[CampaignObjective] = []
    while sum(o.generated for o in _in_progress(game)) < wanted:
        objective = _next(game, _by_variety(game))
        if objective is None:
            break
        game.objectives.objectives.append(objective)
        game.objectives.recent[objective.key] = game.turn
        added.append(objective)
        if announce:
            game.message(f"New objective: {objective.title}", _brief(objective))
    return added


def _brief(objective: CampaignObjective) -> str:
    when = "Until" if objective.kind is ObjectiveKind.HOLD else "By"
    text = f"{when} turn {objective.deadline}."
    if not objective.reward.is_empty:
        text += f" Reward: {objective.reward.describe()}"
    return text


def _passed(objective: CampaignObjective, game: Game) -> bool:
    """Whether the front no longer runs by the target of `objective`."""
    if objective.control_point_id is not None:
        cp = _find_control_point(game, objective.control_point_id)
        return cp is not None and not _near_front(cp)
    remaining = _remaining_targets(objective, game)
    return bool(remaining) and not any(
        _near_front(tgo.control_point) for tgo in remaining
    )


def close_overtaken(game: Game) -> None:
    """Closes the generated objectives in progress the front has passed."""
    for objective in _in_progress(game):
        if objective.generated and _passed(objective, game):
            objective.state = ObjectiveState.OVERTAKEN
            objective.resolved_turn = game.turn
            if objective.key:
                game.objectives.recent[objective.key] = game.turn
            game.message(
                f"{OVERTAKEN_PREFIX}{objective.title}",
                "The front has moved past it: no reward, no penalty.",
            )

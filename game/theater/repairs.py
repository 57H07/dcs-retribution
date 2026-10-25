"""Delayed repair of destroyed ground object units and buildings (PER-02).

A unit under repair stays dead (no income, not spawned alive) while its
``repair_turns_remaining`` counts down at the end of each turn. When the counter
runs out the unit is revived. Runways keep their own ``RunwayStatus`` mechanism.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from dcs.mapping import Point

from game.config import REWARDS

if TYPE_CHECKING:
    from game import Game
    from game.settings import Settings
    from game.sim import GameUpdateEvents
    from game.theater.theatergroundobject import TheaterGroundObject
    from game.theater.theatergroup import TheaterUnit

#: Base repair delay (turns) of a building, by ground object category. Categories
#: missing from this table use ``DEFAULT_BUILDING_REPAIR_TURNS``.
BUILDING_REPAIR_TURNS: dict[str, int] = {
    "ammo": 3,
    "fuel": 3,
    "factory": 6,
    "oil": 6,
}
DEFAULT_BUILDING_REPAIR_TURNS = 4

#: Carcasses closer than this to a repaired unit are removed from the game.
CARCASS_MATCH_RADIUS_M = 15


def building_repair_turns(category: str, settings: Settings) -> int:
    """Repair delay of a building of the given category, multiplier applied.

    0 means the repair is instant.
    """
    base = BUILDING_REPAIR_TURNS.get(category, DEFAULT_BUILDING_REPAIR_TURNS)
    # Round first so that float noise (e.g. 3 * 1.1) does not add a turn.
    return max(0, math.ceil(round(base * settings.building_repair_delay_multiplier, 6)))


def building_repair_cost(category: str, settings: Settings) -> float:
    """Cost of repairing one building: its income per turn times the multiplier."""
    return REWARDS.get(category, 0.0) * settings.building_repair_cost_multiplier


def repair_turns_for(unit: TheaterUnit, settings: Settings) -> int:
    """Number of turns needed to repair the given unit. 0 means instant."""
    if unit.is_static:
        return building_repair_turns(unit.ground_object.category, settings)
    # Ground units are repaired instantly.
    return 0


def begin_repair(game: Game, unit: TheaterUnit, events: GameUpdateEvents) -> None:
    """Starts the repair of a dead unit, or repairs it now if the delay is 0."""
    turns = repair_turns_for(unit, game.settings)
    if turns <= 0:
        complete_repair(game, unit, events)
        logging.info(f"Repaired {unit.unit_name}")
    else:
        unit.repair_turns_remaining = turns
        events.update_tgo(unit.ground_object)
        logging.info(f"Scheduled repair of {unit.unit_name} in {turns} turns")


def buy_repair(
    game: Game, unit: TheaterUnit, price: float, events: GameUpdateEvents
) -> bool:
    """Charges the unit owner's budget and starts the repair.

    Returns False (and does nothing) when the owner cannot afford the repair.
    """
    coalition = unit.ground_object.control_point.coalition
    if coalition.budget < price:
        return False
    coalition.budget -= price
    begin_repair(game, unit, events)
    return True


def complete_repair(game: Game, unit: TheaterUnit, events: GameUpdateEvents) -> None:
    unit.repair_turns_remaining = None
    unit.revive(events)
    remove_carcasses_near(game, unit.position)


def remove_carcasses_near(game: Game, position: Point) -> None:
    destroyed_units = game.get_destroyed_units()
    # Iterate over a copy: removing from the list being iterated skips entries.
    for carcass in list(destroyed_units):
        p = Point(float(carcass["x"]), float(carcass["z"]), game.theater.terrain)
        if p.distance_to_point(position) < CARCASS_MATCH_RADIUS_M:
            destroyed_units.remove(carcass)
            logging.info(f"Removed destroyed unit {carcass}")


def process_repairs(
    game: Game, ground_object: TheaterGroundObject, events: GameUpdateEvents
) -> None:
    """Advances the repairs of a ground object by one turn."""
    for unit in ground_object.units:
        turns_remaining = unit.repair_turns_remaining
        if turns_remaining is None:
            continue
        if unit.alive:
            unit.repair_turns_remaining = None
        elif turns_remaining <= 1:
            complete_repair(game, unit, events)
        else:
            unit.repair_turns_remaining = turns_remaining - 1


def restart_repairs(ground_object: TheaterGroundObject, settings: Settings) -> None:
    """Restarts every repair in progress at a ground object that was just struck."""
    for unit in ground_object.units:
        if unit.repair_turns_remaining is not None:
            unit.repair_turns_remaining = max(1, repair_turns_for(unit, settings))


def cancel_repairs(ground_object: TheaterGroundObject) -> None:
    """Drops the repairs in progress, e.g. when the ground object changes hands."""
    for unit in ground_object.units:
        unit.repair_turns_remaining = None

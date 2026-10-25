"""Persistent damage of ground units and ships at theater ground objects (PER-01.3).

A unit that survives a mission damaged is, depending on how much life it lost,
operational, inoperative for a number of turns, or destroyed. An inoperative unit
spawns as a static object in the following missions and is repaired for free when
its countdown ends.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.sim import GameUpdateEvents
    from game.theater.theatergroundobject import TheaterGroundObject
    from game.theater.theatergroup import TheaterUnit

#: (minimum damage ratio, inoperative turns), highest tier first. Damage below the
#: last tier has no effect.
GROUND_DAMAGE_TIERS: tuple[tuple[float, int], ...] = ((0.8, 3), (0.5, 2), (0.2, 1))

#: Share of a unit's price paid to end its inoperative countdown at once.
ACCELERATED_REPAIR_PRICE_RATIO = 0.5


@dataclass(frozen=True)
class GroundDamageOutcome:
    destroyed: bool = False
    inoperative_turns: int = 0


def ground_damage_outcome(
    remaining_life: float, destroy_heavily_damaged: bool
) -> GroundDamageOutcome:
    """Maps a unit's remaining life ratio (0..1) to its damage tier.

    Units that lost 80 % or more of their life are destroyed when
    ``destroy_heavily_damaged`` is set, inoperative for 3 turns otherwise.
    """
    damage = 1.0 - remaining_life
    for threshold, turns in GROUND_DAMAGE_TIERS:
        # Round to avoid 1.0 - 0.8 being slightly below 0.2.
        if round(damage, 6) >= threshold:
            if threshold == GROUND_DAMAGE_TIERS[0][0] and destroy_heavily_damaged:
                return GroundDamageOutcome(destroyed=True)
            return GroundDamageOutcome(inoperative_turns=turns)
    return GroundDamageOutcome()


def is_damage_tracked(unit: TheaterUnit) -> bool:
    """Persistent damage applies to vehicles and ships of ground objects.

    Buildings are left to PER-02, and the ships of carrier and LHA groups keep
    their binary losses since the naval base itself depends on them.
    """
    if not (unit.is_vehicle or unit.is_ship):
        return False
    return not unit.ground_object.is_naval_control_point


def accelerated_repair_cost(unit: TheaterUnit) -> int:
    """Price, in $M, to end a unit's inoperative countdown immediately."""
    price = unit.unit_type.price if unit.unit_type is not None else 0
    return math.ceil(price * ACCELERATED_REPAIR_PRICE_RATIO)


def process_inoperative_repairs(
    ground_objects: Iterable[TheaterGroundObject],
    turn: int,
    events: GameUpdateEvents,
) -> None:
    """Brings back units whose repair countdown has ended by ``turn``."""
    for ground_object in ground_objects:
        for unit in ground_object.units:
            operational_on = unit.operational_on_turn
            if operational_on is not None and operational_on <= turn:
                unit.end_inoperative(events)

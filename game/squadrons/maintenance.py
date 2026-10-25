"""Aircraft maintenance after persistent damage (PER-01.2).

A squadron's inventory is a plain counter with no airframe identity, so damaged
aircraft are tracked as maintenance batches ``(count, turns_remaining)``.
"""

from __future__ import annotations

import math
from typing import Optional

#: Aircraft damage tiers, as ``(minimum damage ratio, turns in maintenance)``,
#: from the most to the least severe. Damage below the last tier is cosmetic.
AIRCRAFT_DAMAGE_TIERS: tuple[tuple[float, int], ...] = (
    (0.8, 3),
    (0.5, 2),
    (0.2, 1),
)

#: Damage ratio from which an aircraft is written off when the "lost" setting is on.
AIRCRAFT_WRITE_OFF_DAMAGE = 0.8

#: Cost of expediting one aircraft's maintenance by one turn, as a fraction of the
#: aircraft's purchase price.
EXPEDITED_REPAIR_PRICE_RATIO = 0.25

#: A maintenance batch: ``(aircraft count, turns remaining)``.
MaintenanceBatch = tuple[int, int]


def aircraft_maintenance_turns(
    remaining_life: float, write_off_heavy_damage: bool
) -> Optional[int]:
    """Turns an aircraft spends in maintenance after returning with
    ``remaining_life`` (0.0 to 1.0).

    Returns 0 if the aircraft is available next turn, and None if it is written
    off (only when ``write_off_heavy_damage`` is set).
    """
    # Round to avoid float noise putting e.g. 0.8 life (20 % damage) below a tier.
    damage = round(1.0 - remaining_life, 6)
    if write_off_heavy_damage and damage >= AIRCRAFT_WRITE_OFF_DAMAGE:
        return None
    for threshold, turns in AIRCRAFT_DAMAGE_TIERS:
        if damage >= threshold:
            return turns
    return 0


def expedited_repair_cost(price: int, aircraft_turns: int) -> int:
    """Cost of expediting ``aircraft_turns`` aircraft-turns of maintenance for an
    aircraft that costs ``price``."""
    return math.ceil(price * EXPEDITED_REPAIR_PRICE_RATIO * aircraft_turns)

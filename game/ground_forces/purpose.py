"""What a ground unit bought at a base does in the campaign (#214).

Said for the players from the classes the ground war planner sends to the front
(`ai_ground_planner`) and the distances it keeps them at.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.data.units import UnitClass

if TYPE_CHECKING:
    from game.dcs.groundunittype import GroundUnitType

_AIR_DEFENCE = (
    "Front line air defence: covers the ground units against aircraft and "
    "helicopters, 5–8 km behind the front."
)

_PURPOSES = {
    UnitClass.TANK: (
        "Front line: main battle unit, fights in the first line, 2–3 km from "
        "the front."
    ),
    UnitClass.IFV: (
        "Front line: infantry fighting vehicle, fights alongside the tanks, "
        "about 3 km from the front."
    ),
    UnitClass.APC: (
        "Front line: armoured personnel carrier, follows the tanks about 3 km "
        "from the front."
    ),
    UnitClass.ATGM: (
        "Front line: anti-tank missiles, fires on enemy armour from 5–6 km "
        "behind the front."
    ),
    UnitClass.ARTILLERY: (
        "Front line: artillery, shells the enemy ground units from 16–18 km "
        "behind the front."
    ),
    UnitClass.SHORAD: _AIR_DEFENCE,
    UnitClass.AAA: _AIR_DEFENCE,
    UnitClass.LOGISTICS: ("Front line: supply trucks, kept 18–20 km behind the front."),
    UnitClass.RECON: (
        "Front line: reconnaissance, scouts close to the front, 2–3 km away."
    ),
}


def front_line_purpose(unit_type: GroundUnitType) -> str:
    """One sentence on the unit's job in the ground war."""
    return _PURPOSES.get(
        unit_type.unit_class,
        "Not sent to the front line: used by air defence sites only.",
    )

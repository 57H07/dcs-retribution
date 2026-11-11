"""#214: what a ground unit bought at a base does in the campaign."""

from __future__ import annotations

from game.data.units import UnitClass
from game.dcs.groundunittype import GroundUnitType
from game.ground_forces.purpose import front_line_purpose
from game.server.unitinfo.routes import UnitInfoJs


def _of_class(unit_class: UnitClass) -> GroundUnitType:
    for dcs_type in GroundUnitType.each_dcs_type():
        for unit_type in GroundUnitType.for_dcs_type(dcs_type):
            if unit_type.unit_class is unit_class:
                return unit_type
    raise AssertionError(f"No ground unit of class {unit_class}")


def test_a_tank_fights_in_the_first_line() -> None:
    assert front_line_purpose(_of_class(UnitClass.TANK)).startswith(
        "Front line: main battle unit"
    )


def test_artillery_fires_from_behind_the_front() -> None:
    assert "16–18 km" in front_line_purpose(_of_class(UnitClass.ARTILLERY))


def test_aaa_covers_the_front_like_shorad() -> None:
    assert front_line_purpose(_of_class(UnitClass.AAA)) == front_line_purpose(
        _of_class(UnitClass.SHORAD)
    )


def test_a_unit_the_ground_war_does_not_use() -> None:
    assert front_line_purpose(_of_class(UnitClass.SEARCH_RADAR)) == (
        "Not sent to the front line: used by air defence sites only."
    )


def test_the_unit_sheet_says_it_for_ground_units_only() -> None:
    tank = _of_class(UnitClass.TANK)
    assert UnitInfoJs.for_unit_type("ground", tank).purpose == front_line_purpose(tank)
    assert UnitInfoJs.for_unit_type("ground", tank).unit_class == "Tank"

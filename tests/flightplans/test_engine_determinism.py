"""Engine fixes the flight-plan harness needs: orders that depended on addresses."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from unittest.mock import MagicMock

from dcs.ships import Stennis

from game.armedforces.forcegroup import ForceGroup
from game.dcs.groundunittype import GroundUnitType
from game.dcs.shipunittype import ShipUnitType


def _force_group(
    units: list[Any], statics: list[Any], layouts: list[Any]
) -> ForceGroup:
    return ForceGroup("group", units, statics, [], layouts)


def test_ground_unit_type_hashes_by_variant_id() -> None:
    unit = GroundUnitType.named("T-55A")
    assert hash(unit) == hash(unit.variant_id)
    # Equal objects must still hash alike: a copy has its own values, not its address.
    assert hash(replace(unit)) == hash(unit)


def test_ship_unit_type_hashes_by_variant_id() -> None:
    ship = next(ShipUnitType.for_dcs_type(Stennis))
    assert hash(ship) == hash(ship.variant_id)


def test_merge_group_keeps_first_seen_order_without_duplicates() -> None:
    layouts = [MagicMock(name=f"layout {i}") for i in range(8)]
    statics = [type(f"Static{i}", (), {}) for i in range(8)]
    group = _force_group(["a", "b"], statics[:5], layouts[:5])

    group.merge_group(_force_group(["b", "c"], statics[3:], layouts[3:]))

    assert group.units == ["a", "b", "c"]
    assert group.statics == statics
    assert group.layouts == layouts

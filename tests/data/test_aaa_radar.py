from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import yaml

from game.data.units import ANTI_AIR_UNIT_CLASSES, UnitClass
from game.dcs.groundunittype import GroundUnitType
from game.factions.faction import Faction
from game.layout.layout import TgoLayoutUnitGroup

# The two SON-9 "Fire Can" variants are the only stand-alone AAA gun-laying radars.
FIRE_CAN_VARIANTS = ["AAA Fire Can SON-9", "AAA SON-9 Fire Can"]
# A SAM search radar that must NOT be usable to cue AAA guns.
SAM_SEARCH_RADAR_VARIANT = "SAM Patriot STR"

AAA_SITE_LAYOUT = Path("resources/layouts/anti_air/AAA_Site.yaml")


def _faction_with(*units: GroundUnitType) -> Faction:
    """Minimal Faction stand-in exposing just what possible_types_for_faction reads."""
    return cast(
        Faction,
        SimpleNamespace(
            name="Test Faction",
            accessible_units=list(units),
            has_access_to_dcs_type=lambda dcs_type: False,
        ),
    )


def _aaa_radar_slot() -> TgoLayoutUnitGroup:
    """Mirror the generic AAA Site radar slot after the fix."""
    return TgoLayoutUnitGroup(
        name="AAA Site Radar",
        layout_units=[],
        unit_classes=[UnitClass.AAA_RADAR],
        optional=True,
    )


def test_fire_can_radars_are_aaa_radar() -> None:
    for variant in FIRE_CAN_VARIANTS:
        assert GroundUnitType.named(variant).unit_class is UnitClass.AAA_RADAR


def test_aaa_radar_is_still_anti_air() -> None:
    # Reclassifying must not drop the Fire Can from anti-air handling.
    assert UnitClass.AAA_RADAR in ANTI_AIR_UNIT_CLASSES


def test_sam_search_radar_class_unchanged() -> None:
    # Leave-alone/negative case: SAM search radars stay SearchRadar.
    assert GroundUnitType.named(SAM_SEARCH_RADAR_VARIANT).unit_class is (
        UnitClass.SEARCH_RADAR
    )


def test_aaa_radar_slot_rejects_sam_search_radar() -> None:
    # A faction whose only radar is a SAM search radar gets no radar for the AAA
    # slot rather than a useless Patriot STR. The slot is optional, so this is empty.
    patriot = GroundUnitType.named(SAM_SEARCH_RADAR_VARIANT)
    faction = _faction_with(patriot)
    assert _aaa_radar_slot().possible_types_for_faction(faction) == []


def test_aaa_radar_slot_accepts_fire_can() -> None:
    fire_can = GroundUnitType.named(FIRE_CAN_VARIANTS[0])
    patriot = GroundUnitType.named(SAM_SEARCH_RADAR_VARIANT)
    # Even when a SAM search radar is also accessible, only the Fire Can is offered.
    faction = _faction_with(fire_can, patriot)
    assert _aaa_radar_slot().possible_types_for_faction(faction) == [
        fire_can.dcs_unit_type
    ]


def test_aaa_site_layout_requires_aaa_radar() -> None:
    # Guard the layout file itself: the radar slot must ask for AAA radars only.
    data: dict[str, Any] = yaml.safe_load(AAA_SITE_LAYOUT.read_text(encoding="utf-8"))
    radar_slots = [
        unit_group
        for group in data["groups"]
        for unit_group in next(iter(group.values()))
        if unit_group["name"] == "AAA Site Radar"
    ]
    assert radar_slots, "AAA Site layout no longer has a radar slot"
    for slot in radar_slots:
        assert slot["unit_classes"] == [UnitClass.AAA_RADAR.value]

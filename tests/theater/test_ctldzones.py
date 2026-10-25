from typing import Any
from unittest.mock import MagicMock

import pytest
from dcs import Point
from dcs.terrain.caucasus import Caucasus

from game.ato.flightplans._common_ctld import generate_random_ctld_point
from game.theater.controlpoint import Airfield, Carrier, Fob, OffMapSpawn, Player
from game.theater.ctldzones import (
    AIRFIELD_ZONE_OFFSET_METERS,
    DEFAULT_ZONES_OPTION,
    FOB_ZONE_OFFSET_METERS,
    apply_default_ctld_zones,
    ctld_zone_unavailable_reason,
    default_zones_enabled,
)


class AllLand:
    def is_on_land(self, point: Point, ignore_exclusion: bool = False) -> bool:
        return True


class NoLand:
    def is_on_land(self, point: Point, ignore_exclusion: bool = False) -> bool:
        return False


@pytest.fixture(scope="module")
def terrain() -> Caucasus:
    return Caucasus()


def _airfield(terrain: Caucasus, name: str, zones: Any = None) -> Airfield:
    airport = terrain.airports[name]
    # MizCampaignLoader passes [] when the campaign declares no "<name> CTLD" zone.
    return Airfield(
        airport,
        theater=None,  # type: ignore
        starting_coalition=Player.BLUE,
        ctld_zones=[] if zones is None else zones,
    )


def _fob(terrain: Caucasus, name: str, zones: Any = None) -> Fob:
    at = terrain.airports["Batumi"].position.point_from_heading(45, 20000)
    return Fob(
        name,
        at,
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
        ctld_zones=[] if zones is None else zones,
    )


def test_campaign_without_ctld_zones_gets_defaults_at_bases_and_farps(
    terrain: Caucasus,
) -> None:
    batumi = _airfield(terrain, "Batumi")
    kobuleti = _airfield(terrain, "Kobuleti")
    farp = _fob(terrain, "FARP London")

    warnings = apply_default_ctld_zones([batumi, kobuleti, farp], AllLand(), True)

    assert warnings == []
    for cp in (batumi, kobuleti):
        assert cp.ctld_zones
        assert cp.ctld_zones_generated
        for position, radius in cp.ctld_zones:
            assert radius > 0
            distance = position.distance_to_point(cp.position)
            assert distance == pytest.approx(AIRFIELD_ZONE_OFFSET_METERS, abs=1)
    assert farp.ctld_zones
    assert farp.ctld_zones_generated
    for position, _ in farp.ctld_zones:
        assert position.distance_to_point(farp.position) == pytest.approx(
            FOB_ZONE_OFFSET_METERS, abs=1
        )


def test_airfield_zones_are_beside_the_runway(terrain: Caucasus) -> None:
    batumi = _airfield(terrain, "Batumi")
    apply_default_ctld_zones([batumi], AllLand(), True)
    runway_heading = terrain.airports["Batumi"].runways[0].main.heading
    assert batumi.ctld_zones is not None
    for position, _ in batumi.ctld_zones:
        heading = batumi.position.heading_between_point(position)
        offset = (heading - runway_heading) % 180
        assert offset == pytest.approx(90, abs=1)


def test_designer_zones_are_kept(terrain: Caucasus) -> None:
    designer = [(terrain.airports["Batumi"].position, 500.0)]
    batumi = _airfield(terrain, "Batumi", zones=list(designer))

    apply_default_ctld_zones([batumi], AllLand(), True)
    apply_default_ctld_zones([batumi], AllLand(), False)

    assert batumi.ctld_zones == designer
    assert not batumi.ctld_zones_generated


def test_disabled_option_keeps_current_behavior(terrain: Caucasus) -> None:
    batumi = _airfield(terrain, "Batumi")
    apply_default_ctld_zones([batumi], AllLand(), False)
    assert batumi.ctld_zones == []


def test_disabling_the_option_removes_generated_zones(terrain: Caucasus) -> None:
    batumi = _airfield(terrain, "Batumi")
    apply_default_ctld_zones([batumi], AllLand(), True)
    first = list(batumi.ctld_zones or [])
    apply_default_ctld_zones([batumi], AllLand(), True)
    assert batumi.ctld_zones == first  # idempotent

    apply_default_ctld_zones([batumi], AllLand(), False)
    assert batumi.ctld_zones == []
    assert not batumi.ctld_zones_generated


def test_generated_zones_feed_ctld_points(terrain: Caucasus) -> None:
    batumi = _airfield(terrain, "Batumi")
    apply_default_ctld_zones([batumi], AllLand(), True)
    assert batumi.ctld_zones is not None
    point = generate_random_ctld_point(batumi)
    assert any(
        point.distance_to_point(position) <= radius + 1
        for position, radius in batumi.ctld_zones
    )


def test_warning_when_no_land_around_base(terrain: Caucasus) -> None:
    farp = _fob(terrain, "FARP Sea")
    warnings = apply_default_ctld_zones([farp], NoLand(), True)
    assert farp.ctld_zones == []
    assert len(warnings) == 1
    assert "FARP Sea CTLD" in warnings[0]
    assert "Transport" in warnings[0]


def test_reason_for_ships_and_off_map_spawns() -> None:
    carrier = Carrier(name="CVN", at=Point(0, 0, None), theater=None, starts_blue=Player.BLUE)  # type: ignore
    off_map = OffMapSpawn(name="Off map", position=Point(0, 0, None), theater=None, starts_blue=Player.BLUE)  # type: ignore
    for cp in (carrier, off_map):
        reason = ctld_zone_unavailable_reason(cp)
        assert reason is not None
        assert "Transport" in reason
    # Not CTLD-capable: silently skipped when applying.
    assert apply_default_ctld_zones([carrier, off_map], AllLand(), True) == []


def test_no_reason_when_zones_can_exist(terrain: Caucasus) -> None:
    batumi = _airfield(terrain, "Batumi")
    assert ctld_zone_unavailable_reason(batumi, AllLand()) is None


def test_default_zones_enabled_reads_plugin_options() -> None:
    options = {"ctld": True, DEFAULT_ZONES_OPTION: True}
    settings = MagicMock()
    settings.plugin_option.side_effect = lambda key: options[key]
    assert default_zones_enabled(settings)

    options[DEFAULT_ZONES_OPTION] = False
    assert not default_zones_enabled(settings)

    options[DEFAULT_ZONES_OPTION] = True
    options["ctld"] = False
    assert not default_zones_enabled(settings)

    settings.plugin_option.side_effect = KeyError
    assert not default_zones_enabled(settings)


def test_game_turn_initialization_applies_option(terrain: Caucasus) -> None:
    from types import SimpleNamespace

    from game.game import Game

    batumi = _airfield(terrain, "Batumi")
    settings = MagicMock()
    settings.plugin_option.return_value = True
    fake_game = SimpleNamespace(
        theater=SimpleNamespace(
            controlpoints=[batumi], is_on_land=lambda p, ignore_exclusion=False: True
        ),
        settings=settings,
    )
    Game.update_default_ctld_zones(fake_game)  # type: ignore[arg-type]
    assert batumi.ctld_zones_generated


def test_plugin_declares_default_zones_option_off_by_default() -> None:
    import json
    from pathlib import Path

    plugin = json.loads(Path("resources/plugins/ctld/plugin.json").read_text())
    options = {o["mnemonic"]: o["defaultValue"] for o in plugin["specificOptions"]}
    assert options["defaultzones"] is False

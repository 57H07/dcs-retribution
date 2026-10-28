"""PER-01.3: inoperative ground units after persistent damage."""

from types import SimpleNamespace
from typing import Any, cast

import pytest
from dcs.mapping import Point
from dcs.vehicles import AirDefence, Armor
from dcs.statics import Fortification

from game.debriefing import Debriefing, GroundLosses
from game.missiongenerator.tgogenerator import GroundObjectGenerator
from game.point_with_heading import PointWithHeading
from game.settings import Settings
from game.sidc import Status
from game.sim.gameupdateevents import GameUpdateEvents
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.grounddamage import (
    GroundDamageOutcome,
    accelerated_repair_cost,
    ground_damage_outcome,
    process_inoperative_repairs,
)
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import VehicleGroupGroundObject
from game.theater.theatergroup import TheaterGroup, TheaterUnit
from game.utils import Heading


@pytest.mark.parametrize(
    "life,destroy,expected",
    [
        (1.0, True, GroundDamageOutcome()),
        (0.85, True, GroundDamageOutcome()),
        (0.8, True, GroundDamageOutcome(inoperative_turns=1)),
        (0.7, True, GroundDamageOutcome(inoperative_turns=1)),
        (0.51, True, GroundDamageOutcome(inoperative_turns=1)),
        (0.5, True, GroundDamageOutcome(inoperative_turns=2)),
        (0.21, True, GroundDamageOutcome(inoperative_turns=2)),
        (0.2, True, GroundDamageOutcome(destroyed=True)),
        (0.15, True, GroundDamageOutcome(destroyed=True)),
        (0.0, True, GroundDamageOutcome(destroyed=True)),
        (0.15, False, GroundDamageOutcome(inoperative_turns=3)),
        (0.7, False, GroundDamageOutcome(inoperative_turns=1)),
    ],
)
def test_ground_damage_tiers(
    life: float, destroy: bool, expected: GroundDamageOutcome
) -> None:
    assert ground_damage_outcome(life, destroy) == expected


def _ground_object() -> VehicleGroupGroundObject:
    location = PresetLocation(
        name="loc", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    control_point = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    # Only the owner is needed; a full Coalition needs a Game.
    setattr(control_point, "_coalition", SimpleNamespace(player=Player.BLUE))
    return VehicleGroupGroundObject(
        name="armor", location=location, control_point=control_point, task=None
    )


def _unit(ground_object: Any, unit_type: Any = Armor.M_1_Abrams) -> TheaterUnit:
    unit = TheaterUnit(
        id=len(list(ground_object.units)) + 1,
        name="unit",
        type=unit_type,
        position=PointWithHeading.from_point(Point(0, 0, None), Heading(0)),  # type: ignore
        ground_object=ground_object,
    )
    if not ground_object.groups:
        ground_object.groups.append(
            TheaterGroup(1, "group", unit.position, [], ground_object)
        )
    ground_object.groups[0].units.append(unit)
    return unit


def test_inoperative_countdown() -> None:
    unit = _unit(_ground_object())
    events = GameUpdateEvents()
    unit.make_inoperative(1, current_turn=5, events=events)
    assert unit.inoperative
    assert unit.ground_object in events.updated_tgos

    process_inoperative_repairs([unit.ground_object], 6, GameUpdateEvents())
    assert unit.inoperative
    assert unit.inoperative_turns_remaining(6) == 1

    events = GameUpdateEvents()
    process_inoperative_repairs([unit.ground_object], 7, events)
    assert unit.operational
    assert unit.ground_object in events.updated_tgos


def test_new_damage_keeps_longer_countdown() -> None:
    unit = _unit(_ground_object())
    unit.make_inoperative(3, current_turn=1, events=GameUpdateEvents())
    unit.make_inoperative(1, current_turn=2, events=GameUpdateEvents())
    assert unit.operational_on_turn == 5


def test_kill_and_revive_clear_inoperative() -> None:
    unit = _unit(_ground_object())
    unit.make_inoperative(2, current_turn=1, events=GameUpdateEvents())
    unit.kill(GameUpdateEvents())
    assert not unit.inoperative and unit.operational_on_turn is None
    unit.revive(GameUpdateEvents())
    assert unit.operational


def test_inoperative_unit_has_no_threat_and_shows_damaged() -> None:
    ground_object = _ground_object()
    unit = _unit(ground_object, AirDefence.M1097_Avenger)
    assert unit.threat_range.meters > 0
    status_before = ground_object.sidc_status
    assert status_before is Status.PRESENT

    unit.make_inoperative(1, current_turn=1, events=GameUpdateEvents())
    assert unit.threat_range.meters == 0
    assert unit.detection_range.meters == 0
    assert not ground_object.has_aa
    assert ground_object.max_threat_range().meters == 0
    assert ground_object.sidc_status is Status.PRESENT_DAMAGED
    assert "[INOPERATIVE]" in unit.display_name


def test_old_save_unit_is_operational() -> None:
    unit = _unit(_ground_object())
    state = dict(unit.__dict__)
    del state["operational_on_turn"]
    restored = TheaterUnit.__new__(TheaterUnit)
    restored.__dict__.update(state)
    assert restored.operational_on_turn is None
    assert restored.operational


def test_accelerated_repair_cost_is_half_price() -> None:
    unit = _unit(_ground_object())
    assert unit.unit_type is not None
    assert accelerated_repair_cost(unit) * 2 >= unit.unit_type.price


def _debriefing(units: dict[str, TheaterUnit], game: Any) -> Debriefing:
    debriefing = Debriefing.__new__(Debriefing)
    debriefing.game = game
    debriefing.ground_losses = GroundLosses()
    debriefing.unit_map = cast(
        Any,
        SimpleNamespace(
            theater_units=lambda name: (
                SimpleNamespace(theater_unit=units[name]) if name in units else None
            )
        ),
    )
    return debriefing


def test_unit_at_30_percent_inoperative_one_turn_then_operational() -> None:
    unit = _unit(_ground_object())
    game = SimpleNamespace(turn=4)
    debriefing = _debriefing({"tank": unit}, game)
    debriefing.inoperative_ground_units = debriefing.apply_ground_damage(
        {"tank": 0.7}, destroy_heavily_damaged=True
    )
    assert not list(debriefing.ground_object_losses)

    processor = MissionResultsProcessor(cast(Any, game))
    processor.commit_ground_damage(debriefing, GameUpdateEvents())
    assert unit.alive and unit.inoperative

    # Turn 5: the next mission, the unit is out of action.
    process_inoperative_repairs([unit.ground_object], 5, GameUpdateEvents())
    assert unit.inoperative
    # Turn 6: repaired.
    process_inoperative_repairs([unit.ground_object], 6, GameUpdateEvents())
    assert unit.operational


def test_unit_at_85_percent_destroyed_by_default() -> None:
    unit = _unit(_ground_object())
    game = SimpleNamespace(turn=1, settings=Settings())
    debriefing = _debriefing({"tank": unit}, game)
    inoperative = debriefing.apply_ground_damage({"tank": 0.15}, True)
    assert inoperative == []
    assert [loss.theater_unit for loss in debriefing.ground_object_losses] == [unit]

    MissionResultsProcessor.commit_ground_losses(debriefing, GameUpdateEvents())
    assert not unit.alive


def test_unit_at_85_percent_inoperative_three_turns_with_setting() -> None:
    unit = _unit(_ground_object())
    debriefing = _debriefing({"tank": unit}, SimpleNamespace(turn=1))
    inoperative = debriefing.apply_ground_damage({"tank": 0.15}, False)
    assert [(d.theater_unit, d.turns) for d in inoperative] == [(unit, 3)]
    assert not list(debriefing.ground_object_losses)


def test_buildings_and_unknown_units_ignored() -> None:
    ground_object = _ground_object()
    building = _unit(ground_object, Fortification.Barracks_2)
    debriefing = _debriefing({"bunker": building}, SimpleNamespace(turn=1))
    assert debriefing.apply_ground_damage({"bunker": 0.1, "other": 0.1}, True) == []
    assert not list(debriefing.ground_object_losses)


def test_inoperative_unit_spawns_as_static() -> None:
    ground_object = _ground_object()
    healthy = _unit(ground_object)
    damaged = _unit(ground_object)
    damaged.make_inoperative(1, current_turn=1, events=GameUpdateEvents())

    game = SimpleNamespace(
        iads_considerate_culling=lambda _: False,
        settings=SimpleNamespace(plugin_option=lambda _: False),
    )
    generator = GroundObjectGenerator(
        ground_object, None, game, None, None  # type: ignore[arg-type]
    )
    statics: list[TheaterUnit] = []
    vehicles: list[TheaterUnit] = []
    setattr(generator, "create_static_group", statics.append)
    setattr(
        generator,
        "create_vehicle_group",
        lambda _name, units: vehicles.extend(units),
    )
    generator.generate()
    assert statics == [damaged]
    assert vehicles == [healthy]


def test_debriefing_lists_damaged_units() -> None:
    ground_object = _ground_object()
    tank = _unit(ground_object)
    sam = _unit(ground_object, AirDefence.M1097_Avenger)
    scratched = _unit(ground_object)
    game = SimpleNamespace(turn=1, settings=Settings())
    debriefing = _debriefing({"tank": tank, "sam": sam, "scratched": scratched}, game)
    debriefing.damaged_aircraft = []
    debriefing.apply_ground_damage(
        {"tank": 0.15, "sam": 0.4, "scratched": 0.9, "unknown": 0.5}, True
    )

    reports = debriefing.damaged_unit_reports()
    assert [(r.player, r.damage_percent, r.unavailability) for r in reports] == [
        (Player.BLUE, 85, "Destroyed"),
        (Player.BLUE, 60, "Inoperative (2 turns)"),
        (Player.BLUE, 10, "Operational"),
    ]
    assert all(r.unit_type.endswith("(armor)") for r in reports)
    assert "Avenger" in reports[1].unit_type


def test_debriefing_has_no_damaged_units_when_setting_off() -> None:
    debriefing = _debriefing({}, SimpleNamespace(turn=1, settings=Settings()))
    debriefing.damaged_aircraft = []
    state: Any = SimpleNamespace(damaged_units={"tank": 0.1})
    debriefing.apply_ground_damage(
        Debriefing.persistent_damaged_units(state, False), True
    )
    assert debriefing.damaged_unit_reports() == []

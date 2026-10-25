"""Building repairs (PER-02): cost, delay, income during works, strikes."""

from types import SimpleNamespace
from typing import Any, cast

import pytest
from dcs.mapping import Point
from dcs.statics import Fortification
from dcs.vehicles import AirDefence

from game.income import Income
from game.point_with_heading import PointWithHeading
from game.procurement import ProcurementAi
from game.settings import Settings
from game.sim.gameupdateevents import GameUpdateEvents
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.presetlocation import PresetLocation
from game.theater.repairs import (
    begin_repair,
    building_repair_cost,
    building_repair_turns,
    buy_repair,
    cancel_repairs,
    process_repairs,
)
from game.theater.theatergroundobject import BuildingGroundObject, SamGroundObject
from game.theater.theatergroup import TheaterGroup, TheaterUnit
from game.utils import Heading


class FakeGame:
    """The parts of Game that the repair code touches."""

    def __init__(self) -> None:
        self.settings = Settings()
        self.destroyed_units: list[dict[str, Any]] = []
        self.control_points: list[OffMapSpawn] = []
        self.messages: list[str] = []
        self.theater = SimpleNamespace(
            terrain=None,
            control_points_for=self.control_points_for,
            player_points=lambda: self.control_points_for(Player.BLUE),
            enemy_points=lambda: self.control_points_for(Player.RED),
            iads_network=SimpleNamespace(update_tgo=lambda tgo, events: None),
        )

    def control_points_for(self, player: Player) -> list[OffMapSpawn]:
        return [cp for cp in self.control_points if cp.captured == player]

    def get_destroyed_units(self) -> list[dict[str, Any]]:
        return self.destroyed_units

    def message(self, text: str, *args: Any) -> None:
        self.messages.append(text)


def make_control_point(game: FakeGame, player: Player) -> OffMapSpawn:
    cp = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=player,
    )
    cp._coalition = cast(Any, SimpleNamespace(game=game, player=player, budget=0.0))
    game.control_points.append(cp)
    return cp


def make_building(
    cp: OffMapSpawn, category: str, statics: int = 2
) -> BuildingGroundObject:
    location = PresetLocation(
        name=category, position=Point(1000, 1000, None), heading=Heading(0)  # type: ignore
    )
    tgo = BuildingGroundObject(
        name=category,
        category=category,
        location=location,
        control_point=cp,
        task=None,
    )
    units = [
        TheaterUnit(
            id=i,
            name=f"{category}-{i}",
            type=Fortification.Workshop_A,
            position=PointWithHeading.from_point(
                Point(1000 + 100 * i, 1000, None), Heading(0)  # type: ignore
            ),
            ground_object=tgo,
        )
        for i in range(statics)
    ]
    tgo.groups.append(TheaterGroup(0, category, units[0].position, units, tgo))
    cp.connected_objectives.append(tgo)
    return tgo


def building_income(game: FakeGame, player: Player) -> float:
    return Income(cast(Any, game), player).total_buildings


def end_turn(game: FakeGame, tgo: BuildingGroundObject) -> float:
    """Mirrors Game.finish_turn: income is paid, then repairs progress."""
    income = building_income(game, tgo.control_point.captured)
    process_repairs(cast(Any, game), tgo, GameUpdateEvents())
    return income


@pytest.fixture
def game() -> FakeGame:
    return FakeGame()


@pytest.mark.parametrize(
    "category,turns",
    [("ammo", 3), ("fuel", 3), ("factory", 6), ("oil", 6), ("warehouse", 4)],
)
def test_default_delays_by_category(category: str, turns: int) -> None:
    assert building_repair_turns(category, Settings()) == turns


def test_delay_multiplier() -> None:
    settings = Settings()
    settings.building_repair_delay_multiplier = 1.5
    assert building_repair_turns("factory", settings) == 9
    assert building_repair_turns("ammo", settings) == 5  # 4.5 rounded up
    settings.building_repair_delay_multiplier = 0
    assert building_repair_turns("factory", settings) == 0


def test_cost_is_income_times_multiplier() -> None:
    settings = Settings()
    assert building_repair_cost("factory", settings) == 2.5
    settings.building_repair_cost_multiplier = 2
    assert building_repair_cost("factory", settings) == 5
    assert building_repair_cost("not-a-building", settings) == 0


def test_captured_destroyed_factory_repair(game: FakeGame) -> None:
    cp = make_control_point(game, Player.BLUE)
    factory = make_building(cp, "factory")
    for unit in factory.statics:
        unit.alive = False
    coalition = cast(Any, cp.coalition)
    coalition.budget = 100.0

    for unit in list(factory.statics):
        assert buy_repair(
            cast(Any, game), unit, factory.repair_cost(), GameUpdateEvents()
        )
    assert coalition.budget == 95.0

    # No income during the 6 turns of works.
    for _ in range(6):
        assert end_turn(game, factory) == 0
    assert all(unit.alive for unit in factory.statics)
    assert end_turn(game, factory) == 5.0


def test_strike_during_works_restarts_repair(game: FakeGame) -> None:
    cp = make_control_point(game, Player.BLUE)
    factory = make_building(cp, "factory")
    repaired, struck = list(factory.statics)
    repaired.alive = False
    begin_repair(cast(Any, game), repaired, GameUpdateEvents())
    for _ in range(3):
        end_turn(game, factory)
    assert repaired.repair_turns_remaining == 3

    debriefing = SimpleNamespace(
        game=game,
        ground_object_losses=[SimpleNamespace(theater_unit=struck)],
        scenery_object_losses=[],
    )
    MissionResultsProcessor.commit_ground_losses(
        cast(Any, debriefing), GameUpdateEvents()
    )

    assert not struck.alive
    assert repaired.repair_turns_remaining == 6


def test_instant_repair_removes_nearby_carcass(game: FakeGame) -> None:
    game.settings.building_repair_delay_multiplier = 0
    cp = make_control_point(game, Player.BLUE)
    depot = make_building(cp, "ammo", statics=1)
    (unit,) = depot.statics
    unit.alive = False
    near = {"x": unit.position.x + 5, "z": unit.position.y, "type": "x"}
    far = {"x": unit.position.x + 500, "z": unit.position.y, "type": "x"}
    game.destroyed_units.extend([near, far])

    begin_repair(cast(Any, game), unit, GameUpdateEvents())

    assert unit.alive
    assert unit.repair_turns_remaining is None
    assert game.destroyed_units == [far]


def test_repair_needs_budget(game: FakeGame) -> None:
    cp = make_control_point(game, Player.BLUE)
    factory = make_building(cp, "factory", statics=1)
    (unit,) = factory.statics
    unit.alive = False
    cast(Any, cp.coalition).budget = 1.0

    assert not buy_repair(cast(Any, game), unit, 2.5, GameUpdateEvents())
    assert unit.repair_turns_remaining is None
    assert cast(Any, cp.coalition).budget == 1.0


def test_capture_cancels_repairs(game: FakeGame) -> None:
    cp = make_control_point(game, Player.RED)
    factory = make_building(cp, "factory", statics=1)
    (unit,) = factory.statics
    unit.alive = False
    begin_repair(cast(Any, game), unit, GameUpdateEvents())
    cancel_repairs(factory)
    assert unit.repair_turns_remaining is None
    assert not unit.alive


def make_procurement(
    game: FakeGame, player: Player, manage_buildings: bool
) -> ProcurementAi:
    ai = object.__new__(ProcurementAi)
    ai.game = cast(Any, game)
    ai.is_player = player
    ai.manage_runways = False
    ai.manage_front_line = False
    ai.manage_aircraft = False
    ai.manage_buildings = manage_buildings
    ai.manage_ground_objects = False
    return ai


def test_ai_building_repair_disabled_by_default() -> None:
    assert not Settings().ai_building_repairs


def test_ai_spends_nothing_when_building_repair_disabled(game: FakeGame) -> None:
    cp = make_control_point(game, Player.RED)
    factory = make_building(cp, "factory")
    for unit in factory.statics:
        unit.alive = False

    budget = make_procurement(game, Player.RED, manage_buildings=False).spend_budget(
        1000
    )

    assert budget == 1000
    assert all(unit.repair_turns_remaining is None for unit in factory.statics)


def test_ai_repairs_buildings_within_budget_share(
    game: FakeGame, monkeypatch: pytest.MonkeyPatch
) -> None:
    cp = make_control_point(game, Player.RED)
    factory = make_building(cp, "factory")
    for unit in factory.statics:
        unit.alive = False
    ai = make_procurement(game, Player.RED, manage_buildings=True)
    monkeypatch.setattr(
        ProcurementAi, "building_repair_priority", lambda self, tgo: 1.0
    )

    # 15 % of 20 = 3: enough for one 2.5M building, not two.
    assert ai.spend_budget(20) == 17.5
    pending = [u for u in factory.statics if u.repair_turns_remaining == 6]
    assert len(pending) == 1


def test_old_unit_without_repair_field_loads(game: FakeGame) -> None:
    cp = make_control_point(game, Player.BLUE)
    (unit,) = make_building(cp, "ammo", statics=1).statics
    # Unpickling restores the saved __dict__, which predates the new field.
    state = unit.__dict__.copy()
    del state["repair_turns_remaining"]
    restored = TheaterUnit.__new__(TheaterUnit)
    restored.__dict__.update(state)
    assert restored.repair_turns_remaining is None


def test_old_settings_without_repair_fields_load() -> None:
    state = Settings().__dict__.copy()
    for key in [
        "building_repair_cost_multiplier",
        "building_repair_delay_multiplier",
        "ai_building_repairs",
        "ai_ground_unit_repairs",
        "ground_unit_repair_turns",
    ]:
        del state[key]
    settings = Settings.__new__(Settings)
    settings.__setstate__(state)
    assert settings.building_repair_delay_multiplier == 1.0
    assert not settings.ai_building_repairs
    assert not settings.ai_ground_unit_repairs
    assert settings.ground_unit_repair_turns == 0


@pytest.mark.parametrize("enabled", [False, True])
def test_enemy_coalition_follows_ai_building_repair_setting(
    monkeypatch: pytest.MonkeyPatch, enabled: bool
) -> None:
    import game.coalition
    from game.coalition import Coalition

    calls: list[tuple[Any, ...]] = []

    class RecordingAi:
        def __init__(self, *args: Any) -> None:
            calls.append(args)

        def spend_budget(self, budget: float) -> float:
            return budget

    monkeypatch.setattr(game.coalition, "ProcurementAi", RecordingAi)
    settings = Settings()
    settings.ai_building_repairs = enabled
    coalition = SimpleNamespace(
        player=Player.RED,
        game=SimpleNamespace(settings=settings),
        faction=None,
        budget=10.0,
    )
    Coalition.plan_procurement(cast(Any, coalition))
    (args,) = calls
    manage_buildings = args[6]
    assert manage_buildings is enabled


def make_sam_site(cp: OffMapSpawn) -> SamGroundObject:
    location = PresetLocation(
        name="sam", position=Point(5000, 5000, None), heading=Heading(0)  # type: ignore
    )
    sam = SamGroundObject(name="sam", location=location, control_point=cp, task=None)
    types = [
        AirDefence.x_5p73_s_125_ln,
        AirDefence.x_5p73_s_125_ln,
        AirDefence.snr_s_125_tr,
        AirDefence.p_19_s_125_sr,
    ]
    units = [
        TheaterUnit(
            id=100 + i,
            name=f"sam-{i}",
            type=unit_type,
            position=PointWithHeading.from_point(
                Point(5000 + 50 * i, 5000, None), Heading(0)  # type: ignore
            ),
            ground_object=sam,
            alive=False,
        )
        for i, unit_type in enumerate(types)
    ]
    sam.groups.append(TheaterGroup(1, "sam", units[0].position, units, sam))
    cp.connected_objectives.append(sam)
    return sam


def alive(tgo: SamGroundObject) -> list[TheaterUnit]:
    return [unit for unit in tgo.units if unit.alive]


def test_ai_ground_unit_repair_disabled_by_default() -> None:
    assert not Settings().ai_ground_unit_repairs
    assert Settings().ground_unit_repair_turns == 0


def test_ai_spends_nothing_on_ground_units_when_disabled(game: FakeGame) -> None:
    cp = make_control_point(game, Player.RED)
    sam = make_sam_site(cp)
    ai = make_procurement(game, Player.RED, manage_buildings=False)
    ai.manage_ground_objects = False

    assert ai.spend_budget(1000) == 1000
    assert not any(u.alive or u.repair_turns_remaining for u in sam.units)


def test_ai_repairs_search_radar_before_launchers(
    game: FakeGame, monkeypatch: pytest.MonkeyPatch
) -> None:
    cp = make_control_point(game, Player.RED)
    sam = make_sam_site(cp)
    ai = make_procurement(game, Player.RED, manage_buildings=False)
    ai.manage_ground_objects = True
    monkeypatch.setattr(
        ProcurementAi, "ground_object_repair_priority", lambda self, tgo: 10.0
    )
    launcher_a, launcher_b, track_radar, search_radar = sam.units

    # 40 % of 40 = 16: one radar (14M), even though launchers (6M) are cheaper.
    assert ai.repair_ground_objects(40) == 26
    assert alive(sam) == [search_radar]

    ai.repair_ground_objects(40)
    assert alive(sam) == [track_radar, search_radar]


def test_ai_ground_unit_repair_respects_delay(
    game: FakeGame, monkeypatch: pytest.MonkeyPatch
) -> None:
    game.settings.ground_unit_repair_turns = 2
    cp = make_control_point(game, Player.RED)
    sam = make_sam_site(cp)
    ai = make_procurement(game, Player.RED, manage_buildings=False)
    monkeypatch.setattr(
        ProcurementAi, "ground_object_repair_priority", lambda self, tgo: 10.0
    )
    *_, search_radar = sam.units

    ai.repair_ground_objects(40)
    assert search_radar.repair_turns_remaining == 2
    process_repairs(cast(Any, game), sam, GameUpdateEvents())
    assert not search_radar.alive
    process_repairs(cast(Any, game), sam, GameUpdateEvents())
    assert search_radar.alive

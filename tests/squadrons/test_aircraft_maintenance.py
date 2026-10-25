"""PER-01.2: damaged aircraft go into squadron maintenance batches."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest
from dcs.planes import F_16C_50

from game.ato.flighttype import FlightType
from game.db.database import Database
from game.dcs.aircrafttype import AircraftType
from game.dcs.countries import country_with_name
from game.debriefing import DamagedAircraft, DamagedUnitReport, Debriefing
from game.procurement import ProcurementAi
from game.settings import Settings
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.squadrons import Squadron
from game.squadrons.maintenance import (
    aircraft_maintenance_turns,
    expedited_repair_cost,
)
from game.squadrons.operatingbases import OperatingBases
from game.theater.player import Player
from game.unitmap import FlyingUnit, UnitMap


@pytest.fixture
def settings() -> Settings:
    settings = Settings()
    settings.persistent_damage = True
    return settings


@pytest.fixture
def squadron(settings: Settings) -> Squadron:
    home = MagicMock(name="Home")
    home.is_friendly.return_value = True
    home.unclaimed_parking.return_value = 100
    coalition = MagicMock()
    coalition.player = Player.BLUE
    coalition.game.settings = settings
    coalition.faction.locales = None
    aircraft = next(AircraftType.for_dcs_type(F_16C_50))
    squadron = Squadron(
        name="Viper",
        nickname=None,
        country=country_with_name("USA"),
        role="test",
        aircraft=aircraft,
        max_size=16,
        livery=None,
        livery_set=[],
        primary_task=FlightType.STRIKE,
        auto_assignable_mission_types=set(aircraft.iter_task_capabilities()),
        radio_presets={},
        operating_bases=OperatingBases.default_for_aircraft(aircraft),
        female_pilot_percentage=0,
        pilot_pool=[],
        coalition=coalition,
        flight_db=Database(),
        settings=settings,
        location=home,
    )
    squadron.populate_for_turn_0(squadrons_start_full=False)
    squadron.owned_aircraft = 4
    squadron.untasked_aircraft = 4
    return squadron


def _commit_damage(
    squadron: Squadron, settings: Settings, damaged_units: dict[str, float]
) -> None:
    """Runs the mission results step for the given damaged units, all flown by
    ``squadron``."""
    flight = MagicMock()
    flight.squadron = squadron
    flight.unit_type = squadron.aircraft
    unit_map = UnitMap()
    for name in damaged_units:
        unit_map.aircraft[name] = FlyingUnit(flight, None)
    unit_map.aircraft["Undamaged wingman"] = FlyingUnit(flight, None)
    debriefing: Any = SimpleNamespace(
        damaged_aircraft=Debriefing.find_damaged_aircraft(damaged_units, unit_map)
    )
    game = MagicMock()
    game.settings = settings
    MissionResultsProcessor(game).commit_aircraft_damage(debriefing)


def _next_turn(squadron: Squadron) -> None:
    """The squadron's part of finishing a turn and initializing the next one."""
    squadron.end_turn()
    squadron.return_all_pilots_and_aircraft()


@pytest.mark.parametrize(
    "life,write_off,expected",
    [
        (1.0, False, 0),
        (0.81, False, 0),
        (0.8, False, 1),
        (0.65, False, 1),
        (0.51, False, 1),
        (0.5, False, 2),
        (0.21, False, 2),
        (0.2, False, 3),
        (0.0, False, 3),
        (0.2, True, None),
        (0.15, True, None),
        (0.21, True, 2),
    ],
)
def test_aircraft_damage_tiers(
    life: float, write_off: bool, expected: Optional[int]
) -> None:
    assert aircraft_maintenance_turns(life, write_off) == expected


def test_f16_at_35_percent_damage_misses_one_turn(
    squadron: Squadron, settings: Settings
) -> None:
    # Turn N: one F-16 comes back with 35 % damage.
    _commit_damage(squadron, settings, {"Viper 1-1": 0.65})

    _next_turn(squadron)  # Turn N+1
    assert squadron.owned_aircraft == 4
    assert squadron.aircraft_in_maintenance == 1
    assert squadron.available_aircraft == 3
    assert squadron.untasked_aircraft == 3
    assert squadron.maintenance_batches == [(1, 1)]
    assert not squadron.can_fulfill_flight(4)

    _next_turn(squadron)  # Turn N+2
    assert squadron.aircraft_in_maintenance == 0
    assert squadron.untasked_aircraft == 4
    assert squadron.maintenance_batches == []


def test_heavy_damage_keeps_aircraft_three_turns(
    squadron: Squadron, settings: Settings
) -> None:
    _commit_damage(squadron, settings, {"a": 0.1, "b": 0.15, "c": 0.4})
    available = []
    for _ in range(4):
        _next_turn(squadron)
        available.append(squadron.untasked_aircraft)
    # Two aircraft for 3 turns, one (60 % damage) for 2 turns.
    assert available == [1, 1, 2, 4]


def test_aircraft_at_85_percent_written_off(
    squadron: Squadron, settings: Settings
) -> None:
    settings.persistent_damage_aircraft_write_off = True
    _commit_damage(squadron, settings, {"Viper 1-1": 0.15})
    assert squadron.owned_aircraft == 3
    assert squadron.destroyed_aircraft == 1
    assert squadron.aircraft_in_maintenance == 0
    _next_turn(squadron)
    assert squadron.untasked_aircraft == 3


def test_light_damage_has_no_effect(squadron: Squadron, settings: Settings) -> None:
    _commit_damage(squadron, settings, {"Viper 1-1": 0.9})
    _next_turn(squadron)
    assert squadron.untasked_aircraft == 4


def test_no_damage_without_setting() -> None:
    state: Any = SimpleNamespace(damaged_units={"Viper 1-1": 0.1})
    damaged_units = Debriefing.persistent_damaged_units(state, False)
    unit_map = UnitMap()
    unit_map.aircraft["Viper 1-1"] = FlyingUnit(MagicMock(), None)
    assert Debriefing.find_damaged_aircraft(damaged_units, unit_map) == []


def test_damaged_ground_units_are_not_aircraft() -> None:
    flying = FlyingUnit(MagicMock(), None)
    unit_map = UnitMap()
    unit_map.aircraft["Viper 1-1"] = flying
    damaged = Debriefing.find_damaged_aircraft(
        {"SA-11 TELAR": 0.3, "Viper 1-1": 0.6}, unit_map
    )
    assert damaged == [DamagedAircraft(flying, "Viper 1-1", 0.6)]


def test_maintenance_trimmed_when_aircraft_lost(squadron: Squadron) -> None:
    squadron.send_to_maintenance(2, 3)
    squadron.send_to_maintenance(1, 1)
    squadron.owned_aircraft = 2
    _next_turn(squadron)
    assert squadron.maintenance_batches == [(2, 3)]
    assert squadron.untasked_aircraft == 0


def test_expedite_maintenance(squadron: Squadron) -> None:
    squadron.send_to_maintenance(1, 2)
    _next_turn(squadron)
    assert squadron.untasked_aircraft == 3
    expected = expedited_repair_cost(squadron.aircraft.price, 2)
    assert squadron.expedited_repair_cost == expected > 0
    assert squadron.expedite_maintenance() == 1
    assert squadron.untasked_aircraft == 4
    assert squadron.aircraft_in_maintenance == 0
    assert squadron.expedited_repair_cost == 0


def _procurement(squadron: Squadron) -> ProcurementAi:
    procurement = ProcurementAi.__new__(ProcurementAi)
    procurement.game = MagicMock()
    procurement.is_player = Player.RED
    procurement.air_wing = MagicMock()
    procurement.air_wing.iter_squadrons.return_value = [squadron]
    return procurement


def test_procurement_pays_for_repair(squadron: Squadron) -> None:
    squadron.send_to_maintenance(1, 3)
    _next_turn(squadron)
    cost = squadron.expedited_repair_cost
    assert _procurement(squadron).repair_aircraft(cost + 5) == 5
    assert squadron.untasked_aircraft == 4


def test_procurement_skips_unaffordable_repair(squadron: Squadron) -> None:
    squadron.send_to_maintenance(1, 3)
    _next_turn(squadron)
    cost = squadron.expedited_repair_cost
    assert _procurement(squadron).repair_aircraft(cost - 1) == cost - 1
    assert squadron.aircraft_in_maintenance == 1


def test_old_squadron_save_loads(squadron: Squadron) -> None:
    state = dict(squadron.__dict__)
    del state["maintenance_batches"]
    del state["new_maintenance_batches"]
    loaded = Squadron.__new__(Squadron)
    loaded.__setstate__(state)
    assert loaded.maintenance_batches == []
    assert loaded.new_maintenance_batches == []
    assert loaded.available_aircraft == loaded.owned_aircraft == 4


def test_old_settings_load_with_new_options_off() -> None:
    state = Settings().__dict__.copy()
    del state["persistent_damage_aircraft_write_off"]
    del state["expedited_aircraft_repair"]
    settings = Settings()
    settings.__setstate__(state)
    assert settings.persistent_damage_aircraft_write_off is False
    assert settings.expedited_aircraft_repair is False


def test_maintenance_summary_groups_batches_by_turns(squadron: Squadron) -> None:
    assert squadron.maintenance_summary == []
    assert squadron.maintenance_text == ""
    squadron.send_to_maintenance(1, 3)
    squadron.send_to_maintenance(1, 1)
    _next_turn(squadron)
    squadron.send_to_maintenance(1, 2)
    assert squadron.maintenance_summary == [(1, 1), (1, 2), (1, 3)]
    _next_turn(squadron)
    # The 1-turn batch is done and the 3-turn one counted down; (1, 2) was new.
    assert squadron.maintenance_summary == [(2, 2)]
    squadron.send_to_maintenance(1, 1)
    assert squadron.maintenance_summary == [(1, 1), (2, 2)]
    assert squadron.maintenance_text == (
        "1 in maintenance (1 turn), 2 in maintenance (2 turns)"
    )


def test_player_buys_expedited_maintenance(squadron: Squadron) -> None:
    squadron.send_to_maintenance(2, 2)
    _next_turn(squadron)
    cost = squadron.expedited_repair_cost
    squadron.coalition.budget = cost - 1
    assert squadron.buy_expedited_maintenance() == 0
    assert squadron.aircraft_in_maintenance == 2

    squadron.coalition.budget = cost + 10
    assert squadron.buy_expedited_maintenance() == 2
    assert squadron.coalition.budget == 10
    assert squadron.untasked_aircraft == 4
    assert squadron.buy_expedited_maintenance() == 0
    assert squadron.coalition.budget == 10


def test_damaged_aircraft_report(squadron: Squadron) -> None:
    flight = MagicMock()
    flight.squadron = squadron
    flight.unit_type = squadron.aircraft
    unit = FlyingUnit(flight, None)
    report = DamagedUnitReport.for_aircraft(
        DamagedAircraft(unit, "Viper 1-1", 0.65), write_off=False
    )
    assert report.player is Player.BLUE
    assert report.unit_type == f"{squadron.aircraft.display_name} (Viper)"
    assert report.damage_percent == 35
    assert report.unavailability == "In maintenance (1 turn)"

    heavy = DamagedAircraft(unit, "Viper 1-2", 0.15)
    assert (
        DamagedUnitReport.for_aircraft(heavy, write_off=False).unavailability
        == "In maintenance (3 turns)"
    )
    assert (
        DamagedUnitReport.for_aircraft(heavy, write_off=True).unavailability
        == "Written off"
    )
    light = DamagedAircraft(unit, "Viper 1-3", 0.9)
    assert (
        DamagedUnitReport.for_aircraft(light, write_off=False).unavailability
        == "Available"
    )

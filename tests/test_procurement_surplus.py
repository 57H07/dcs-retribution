"""The AI spends its surplus budget filling squadrons and on allowed repairs."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from dcs.planes import F_16C_50

from game.ato.flighttype import FlightType
from game.db.database import Database
from game.dcs.aircrafttype import AircraftType
from game.dcs.countries import country_with_name
from game.procurement import AircraftProcurementRequest, ProcurementAi
from game.settings import Settings
from game.squadrons import Squadron
from game.squadrons.operatingbases import OperatingBases
from game.theater.player import Player

RESERVE = 100


@pytest.fixture
def settings() -> Settings:
    settings = Settings()
    settings.ai_surplus_reserve = RESERVE
    return settings


class Base:
    """A control point with a fixed amount of parking."""

    def __init__(self, parking: int) -> None:
        self.parking = parking
        self.squadrons: list[Squadron] = []
        self.mock = MagicMock(name="Base")
        self.mock.is_friendly.return_value = True
        self.mock.unclaimed_parking.side_effect = self.unclaimed_parking

    def unclaimed_parking(self, _: Any) -> int:
        return self.parking - sum(s.expected_size_next_turn for s in self.squadrons)


def make_squadron(
    settings: Settings,
    base: Base,
    owned: int = 2,
    max_size: int = 4,
    tasks: set[FlightType] | None = None,
) -> Squadron:
    coalition = MagicMock()
    coalition.player = Player.RED
    coalition.game.settings = settings
    coalition.faction.locales = None
    aircraft = next(AircraftType.for_dcs_type(F_16C_50))
    squadron = Squadron(
        name=f"Viper {len(base.squadrons)}",
        nickname=None,
        country=country_with_name("Russia"),
        role="test",
        aircraft=aircraft,
        max_size=max_size,
        livery=None,
        livery_set=[],
        primary_task=FlightType.STRIKE,
        auto_assignable_mission_types=(
            tasks if tasks is not None else {FlightType.STRIKE}
        ),
        radio_presets={},
        operating_bases=OperatingBases.default_for_aircraft(aircraft),
        female_pilot_percentage=0,
        pilot_pool=[],
        coalition=coalition,
        flight_db=Database(),
        settings=settings,
        location=base.mock,
    )
    squadron.populate_for_turn_0(squadrons_start_full=False)
    squadron.owned_aircraft = owned
    squadron.untasked_aircraft = owned
    base.squadrons.append(squadron)
    return squadron


def make_procurement(
    settings: Settings,
    squadrons: list[Squadron],
    requests: list[AircraftProcurementRequest] | None = None,
    manage_buildings: bool = False,
    manage_ground_objects: bool = False,
    owned_points: list[Any] | None = None,
) -> ProcurementAi:
    procurement = ProcurementAi.__new__(ProcurementAi)
    procurement.game = MagicMock()
    procurement.game.settings = settings
    procurement.game.turn = 5
    procurement.game.coalition_for.return_value.procurement_requests = requests or []
    procurement.game.theater.control_points_for.return_value = []
    procurement.game.theater.enemy_points.return_value = owned_points or []
    procurement.is_player = Player.RED
    procurement.air_wing = MagicMock()
    procurement.air_wing.iter_squadrons.return_value = squadrons
    procurement.threat_zones = MagicMock()
    procurement.threat_zones.threatened.return_value = False
    procurement.manage_runways = False
    procurement.manage_front_line = False
    procurement.manage_aircraft = True
    procurement.manage_buildings = manage_buildings
    procurement.manage_ground_objects = manage_ground_objects
    return procurement


def price(squadron: Squadron) -> int:
    return squadron.aircraft.price


def test_fills_squadrons_up_to_max_size(settings: Settings) -> None:
    base = Base(parking=100)
    a = make_squadron(settings, base)
    b = make_squadron(settings, base)
    budget = RESERVE + 10 * price(a) + 3

    left = make_procurement(settings, [a, b]).spend_budget(budget)

    assert a.pending_deliveries == 2
    assert b.pending_deliveries == 2
    assert left == budget - 4 * price(a)


def test_spreads_purchases_over_squadrons(settings: Settings) -> None:
    base = Base(parking=100)
    a = make_squadron(settings, base, max_size=8)
    b = make_squadron(settings, base, max_size=8)

    make_procurement(settings, [a, b]).spend_budget(RESERVE + 2 * price(a))

    assert a.pending_deliveries == 1
    assert b.pending_deliveries == 1


def test_emptiest_squadron_first(settings: Settings) -> None:
    base = Base(parking=100)
    full = make_squadron(settings, base, owned=3, max_size=4)
    empty = make_squadron(settings, base, owned=0, max_size=4)

    make_procurement(settings, [full, empty]).spend_budget(RESERVE + 2 * price(full))

    assert empty.pending_deliveries == 2
    assert full.pending_deliveries == 0


def test_requested_mission_types_first(settings: Settings) -> None:
    base = Base(parking=100)
    strike = make_squadron(settings, base, tasks={FlightType.STRIKE})
    cap = make_squadron(settings, base, tasks={FlightType.BARCAP})
    request = AircraftProcurementRequest(MagicMock(), FlightType.BARCAP, 2)

    make_procurement(settings, [strike, cap], [request]).spend_budget(
        RESERVE + 2 * price(cap)
    )

    assert cap.pending_deliveries == 2
    assert strike.pending_deliveries == 0


def test_respects_parking(settings: Settings) -> None:
    base = Base(parking=5)
    a = make_squadron(settings, base, max_size=8)
    b = make_squadron(settings, base, max_size=8)

    make_procurement(settings, [a, b]).spend_budget(RESERVE + 20 * price(a))

    assert a.pending_deliveries + b.pending_deliveries == 1


def test_respects_pilot_availability(settings: Settings) -> None:
    settings.enable_squadron_pilot_limits = True
    settings.squadron_pilot_limit = 3
    base = Base(parking=100)
    a = make_squadron(settings, base, owned=2, max_size=8)
    assert a.expected_pilots_next_turn == 3

    make_procurement(settings, [a]).spend_budget(RESERVE + 20 * price(a))

    assert a.pending_deliveries == 1


def test_skips_relocating_squadrons(settings: Settings) -> None:
    base = Base(parking=100)
    a = make_squadron(settings, base)
    a.destination = MagicMock()

    make_procurement(settings, [a]).spend_budget(RESERVE + 20 * price(a))

    assert a.pending_deliveries == 0


def test_keeps_the_reserve(settings: Settings) -> None:
    base = Base(parking=100)
    a = make_squadron(settings, base)
    budget = RESERVE + price(a) - 1

    assert make_procurement(settings, [a]).spend_budget(budget) == budget
    assert a.pending_deliveries == 0


def test_disabled_keeps_the_surplus(settings: Settings) -> None:
    settings.ai_surplus_spending = False
    base = Base(parking=100)
    a = make_squadron(settings, base)
    budget = RESERVE + 20 * price(a)

    assert make_procurement(settings, [a]).spend_budget(budget) == budget
    assert a.pending_deliveries == 0


def test_spends_expedited_aircraft_repair_when_enabled(settings: Settings) -> None:
    settings.expedited_aircraft_repair = True
    base = Base(parking=100)
    a = make_squadron(settings, base, owned=4, max_size=4)
    a.send_to_maintenance(1, 3)
    a.process_maintenance()
    cost = a.expedited_repair_cost

    left = make_procurement(settings, [a]).spend_surplus(RESERVE + cost)

    assert left == RESERVE
    assert a.aircraft_in_maintenance == 0


def _dead_building(cost: float) -> tuple[float, float, MagicMock]:
    unit = MagicMock(name="building")
    return 1.0, cost, unit


def test_repairs_all_buildings_with_surplus_when_enabled(settings: Settings) -> None:
    candidates = [_dead_building(40), _dead_building(40)]
    procurement = make_procurement(settings, [], manage_buildings=True)
    procurement.building_repair_candidates = lambda: candidates  # type: ignore

    with patch("game.procurement.begin_repair") as begin_repair:
        left = procurement.spend_surplus(RESERVE + 85)

    # The normal pass is capped to a share of the budget; the surplus is not.
    assert begin_repair.call_count == 2
    assert left == RESERVE + 5


def test_no_building_repairs_when_disabled(settings: Settings) -> None:
    procurement = make_procurement(settings, [], manage_buildings=False)
    procurement.building_repair_candidates = (  # type: ignore
        lambda: [_dead_building(40)]
    )

    with patch("game.procurement.begin_repair") as begin_repair:
        assert procurement.spend_surplus(RESERVE + 85) == RESERVE + 85

    begin_repair.assert_not_called()


def _inoperative_unit(unit_price: int, turns: int) -> MagicMock:
    unit = MagicMock(name="vehicle")
    unit.inoperative = True
    unit.is_vehicle = True
    unit.ground_object.is_naval_control_point = False
    unit.unit_type.price = unit_price
    unit.inoperative_turns_remaining.return_value = turns
    return unit


def _procurement_with_units(
    settings: Settings, units: list[MagicMock], manage_ground_objects: bool
) -> ProcurementAi:
    ground_object = MagicMock()
    ground_object.is_friendly.return_value = True
    ground_object.units = units
    control_point = MagicMock()
    control_point.ground_objects = [ground_object]
    procurement = make_procurement(
        settings,
        [],
        manage_ground_objects=manage_ground_objects,
        owned_points=[control_point],
    )
    procurement.ground_object_repair_candidates = lambda: []  # type: ignore
    return procurement


def test_pays_inoperative_ground_repairs_when_enabled(settings: Settings) -> None:
    settings.persistent_damage_paid_ground_repair = True
    long_wait = _inoperative_unit(100, turns=3)
    short_wait = _inoperative_unit(100, turns=1)
    procurement = _procurement_with_units(
        settings, [short_wait, long_wait], manage_ground_objects=True
    )

    left = procurement.spend_surplus(RESERVE + 60)

    long_wait.end_inoperative.assert_called_once()
    short_wait.end_inoperative.assert_not_called()
    assert left == RESERVE + 10


def test_no_inoperative_ground_repairs_when_paid_repair_disabled(
    settings: Settings,
) -> None:
    settings.persistent_damage_paid_ground_repair = False
    unit = _inoperative_unit(100, turns=3)
    procurement = _procurement_with_units(settings, [unit], manage_ground_objects=True)

    assert procurement.spend_surplus(RESERVE + 60) == RESERVE + 60
    unit.end_inoperative.assert_not_called()


def test_defaults() -> None:
    settings = Settings()
    assert settings.ai_surplus_spending is True
    assert settings.ai_building_repairs is False
    assert settings.ai_ground_unit_repairs is False
    assert settings.expedited_aircraft_repair is False
    assert settings.persistent_damage_paid_ground_repair is False

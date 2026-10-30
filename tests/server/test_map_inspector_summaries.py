"""WEB-01.3: base and ground object summaries of the map inspector."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from dcs.mapping import Point
from fastapi import HTTPException

from game.config import RUNWAY_REPAIR_COST
from game.server.controlpoints.routes import get_control_point_summary
from game.server.controlpoints.summary import (
    ControlPointSummaryJs,
    distance_to_front_nm,
)
from game.server.tgos.routes import get_tgo_summary
from game.server.tgos.summary import TgoSummaryJs, readable
from game.theater.controlpoint import RunwayStatus
from game.utils import nautical_miles


def _point(x: float, y: float = 0) -> Point:
    return Point(x, y, None)  # type: ignore[arg-type]


def _game(front_lines: list[Point] | None = None, budget: float = 1000) -> Any:
    conflicts = [SimpleNamespace(position=p) for p in front_lines or []]
    return SimpleNamespace(
        theater=SimpleNamespace(
            conflicts=lambda: iter(conflicts),
            find_control_point_by_id=lambda _id: None,
        ),
        blue=SimpleNamespace(budget=budget),
        db=SimpleNamespace(tgos=SimpleNamespace(get=lambda _id: {}[_id])),
    )


def _cp(
    blue: bool = True,
    category: str = "airfield",
    runway: RunwayStatus | None = None,
    destroyable: bool = True,
    parking: int = 25,
    present: int = 18,
    front: bool = True,
    factory: bool = True,
) -> Any:
    runway = runway or RunwayStatus()
    return SimpleNamespace(
        id=uuid4(),
        name="Krymsk",
        captured=SimpleNamespace(is_blue=blue),
        sidc=lambda: "10031000001213000000",
        category=category,
        position=_point(0),
        runway_is_destroyable=destroyable,
        runway_status=runway,
        runway_can_be_repaired=runway.needs_repair,
        total_aircraft_parking=lambda _type: parking,
        allocated_aircraft=lambda _type: SimpleNamespace(total_present=present),
        has_active_frontline=front,
        base=SimpleNamespace(total_armor=30),
        frontline_unit_count_limit=24,
        active_ammo_depots_count=2,
        total_ammo_depots_count=3,
        active_fuel_depots_count=1,
        total_fuel_depots_count=1,
        can_recruit_ground_units=lambda _game: factory,
    )


def test_distance_to_closest_front_in_nautical_miles() -> None:
    game = _game([_point(nautical_miles(30).meters), _point(nautical_miles(12).meters)])
    assert distance_to_front_nm(game, _point(0)) == pytest.approx(12, abs=0.1)


def test_no_distance_without_front_line() -> None:
    assert distance_to_front_nm(_game(), _point(0)) is None


def test_friendly_airfield_summary() -> None:
    game = _game([_point(nautical_miles(12).meters)])
    summary = ControlPointSummaryJs.for_control_point(game, _cp())
    assert summary.name == "Krymsk"
    assert summary.category == "Airfield"
    assert summary.distance_to_front_nm == pytest.approx(12, abs=0.1)
    assert summary.runway is not None and summary.runway.state == "operational"
    assert summary.parking is not None
    assert (summary.parking.current, summary.parking.total) == (18, 25)
    assert summary.ground_units is not None
    assert (summary.ground_units.current, summary.ground_units.total) == (30, 24)
    assert (summary.ammo_depots.current, summary.ammo_depots.total) == (2, 3)
    assert summary.can_buy_aircraft and summary.can_buy_ground_units
    assert not summary.can_repair_runway
    assert summary.runway_repair_cost == RUNWAY_REPAIR_COST


def test_damaged_runway_can_be_repaired_when_affordable() -> None:
    cp = _cp(runway=RunwayStatus(damaged=True))
    summary = ControlPointSummaryJs.for_control_point(_game(), cp)
    assert summary.runway is not None and summary.runway.state == "damaged"
    assert summary.can_repair_runway
    assert summary.can_afford_runway_repair
    poor = ControlPointSummaryJs.for_control_point(_game(budget=10), cp)
    assert not poor.can_afford_runway_repair


def test_runway_under_repair() -> None:
    cp = _cp(runway=RunwayStatus(damaged=True, repair_turns_remaining=3))
    summary = ControlPointSummaryJs.for_control_point(_game(), cp)
    assert summary.runway is not None
    assert summary.runway.state == "repairing"
    assert summary.runway.repair_turns_remaining == 3
    assert not summary.can_repair_runway


def test_carrier_without_runway_or_front() -> None:
    cp = _cp(category="cv", destroyable=False, front=False)
    summary = ControlPointSummaryJs.for_control_point(_game(), cp)
    assert summary.category == "Carrier"
    assert summary.runway is None
    assert summary.ground_units is None


def test_enemy_base_offers_no_action() -> None:
    cp = _cp(blue=False, runway=RunwayStatus(damaged=True))
    summary = ControlPointSummaryJs.for_control_point(_game(), cp)
    assert not summary.blue
    assert not summary.can_buy_aircraft
    assert not summary.can_buy_ground_units
    assert not summary.can_repair_runway


def test_base_without_parking() -> None:
    summary = ControlPointSummaryJs.for_control_point(_game(), _cp(parking=0))
    assert summary.parking is None
    assert not summary.can_buy_aircraft


def test_unknown_base_is_404() -> None:
    with pytest.raises(HTTPException) as error:
        get_control_point_summary(uuid4(), _game())
    assert error.value.status_code == 404


def _tgo(task: str | None, category: str = "aa") -> Any:
    ground_object = SimpleNamespace(
        task=SimpleNamespace(description=task) if task else None
    )
    return SimpleNamespace(
        id=uuid4(),
        name="SA-10 Krasnodar",
        control_point=SimpleNamespace(
            id=uuid4(), name="Krasnodar", captured=SimpleNamespace(is_blue=False)
        ),
        sidc=lambda: "10061500001301000000",
        groups=[SimpleNamespace(ground_object=ground_object)],
        category=category,
        position=_point(0),
        alive_unit_count=5,
        unit_count=8,
        is_dead=False,
    )


def test_tgo_summary() -> None:
    summary = TgoSummaryJs.for_tgo(_game([_point(1852)]), _tgo("LORAD"))
    assert summary.category == "LORAD"
    assert summary.control_point_name == "Krasnodar"
    assert not summary.blue
    assert (summary.units.current, summary.units.total) == (5, 8)
    assert summary.distance_to_front_nm == pytest.approx(1, abs=0.01)


def test_tgo_category_falls_back_on_the_tgo_category() -> None:
    assert TgoSummaryJs.for_tgo(_game(), _tgo(None, "armor")).category == "Armor"
    assert TgoSummaryJs.for_tgo(_game(), _tgo(None, "aa")).category == "Air defense"


def test_readable_category() -> None:
    assert readable("EarlyWarningRadar") == "Early Warning Radar"
    assert readable("SHORAD") == "SHORAD"


def test_unknown_tgo_is_404() -> None:
    with pytest.raises(HTTPException) as error:
        get_tgo_summary(uuid4(), _game())
    assert error.value.status_code == 404

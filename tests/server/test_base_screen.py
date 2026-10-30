"""WEB-02.1: base screen status and repair commands."""

from __future__ import annotations

import asyncio
import json
from collections.abc import MutableMapping
from types import SimpleNamespace
from typing import Any, Iterator
from uuid import uuid4

import pytest
from dcs.mapping import Point

from game.commands import (
    RUNWAY_REPAIR_ID,
    CommandError,
    base_repairs,
    order_all_repairs,
    order_repair,
)
from game.config import RUNWAY_REPAIR_COST, RUNWAY_REPAIR_TURNS
from game.server import GameContext
from game.server.app import app
from game.server.controlpoints.base import BaseJs, base_tabs
from game.server.eventstream import EventStream
from game.server.security import ApiKeyManager
from game.sim import GameUpdateEvents
from game.theater.controlpoint import RunwayStatus
from game.theater.theatergroundobject import BuildingGroundObject


class _Type:
    def __init__(self, display_name: str, task: str = "") -> None:
        self.display_name = display_name
        self.dcs_unit_type = SimpleNamespace(task_default=SimpleNamespace(name=task))


class _Unit:
    def __init__(
        self, ground_object: Any, alive: bool = False, anti_air: bool = False
    ) -> None:
        self.ground_object = ground_object
        self.alive = alive
        self.is_static = True
        self.is_anti_air = anti_air
        self.repair_turns_remaining: int | None = None
        self.unit_name = "unit"


class _Depot(BuildingGroundObject):
    """A building ground object without a theater behind it."""

    def __init__(self, name: str, category: str, dead: int, price: float) -> None:
        self.id = uuid4()
        self.name = name
        self.category = category
        self.price = price
        self._units = [_Unit(self, alive=i >= dead) for i in range(dead + 1)]

    @property
    def statics(self) -> Iterator[Any]:
        yield from self._units

    @property
    def units(self) -> Iterator[Any]:
        yield from self._units

    def repair_cost(self) -> float:
        return self.price


class _Sam:
    def __init__(self) -> None:
        self.id = uuid4()
        self.name = "SA-15 Krymsk"
        self.category = "aa"
        task = SimpleNamespace(description="SHORAD")
        self.groups = [SimpleNamespace(ground_object=SimpleNamespace(task=task))]
        self.units = [_Unit(self, alive=True, anti_air=True)]
        self.alive_unit_count = 1
        self.unit_count = 2
        self.has_aa = True


class _Squadron:
    def __init__(self, in_maintenance: int, cost: int) -> None:
        self.id = uuid4()
        self.name = "40th TAB"
        self.aircraft = SimpleNamespace(display_name="MiG-29")
        self.aircraft_in_maintenance = in_maintenance
        self.maintenance_summary = [(1, 1), (in_maintenance - 1, 2)]
        self.expedited_repair_cost = cost
        self.released = 0

    def expedite_maintenance(self) -> int:
        self.released = self.aircraft_in_maintenance
        self.aircraft_in_maintenance = 0
        return self.released


class _Cp:
    def __init__(
        self,
        blue: bool = True,
        runway: RunwayStatus | None = None,
        ground_objects: list[Any] | None = None,
        squadrons: list[Any] | None = None,
    ) -> None:
        self.id = uuid4()
        self.name = "Krymsk"
        self.captured = SimpleNamespace(is_blue=blue)
        self.category = "airfield"
        self.position = Point(0, 0, None)  # type: ignore[arg-type]
        self.runway_is_destroyable = True
        self.runway_status = runway or RunwayStatus()
        self.ground_objects = ground_objects or []
        self.squadrons = squadrons or []
        self.has_active_frontline = False
        self.can_deploy_ground_units = True
        self.base = SimpleNamespace(total_armor=2, armor={_Type("T-72"): 2})
        self._aircraft = SimpleNamespace(
            total_present=10, present={_Type("MiG-29", "CAP"): 10}
        )
        self.frontline_unit_count_limit = 24
        self.active_ammo_depots_count = 1
        self.total_ammo_depots_count = 1
        self.active_fuel_depots_count = 0
        self.total_fuel_depots_count = 1

    def sidc(self) -> str:
        return "10031000001213000000"

    @property
    def runway_can_be_repaired(self) -> bool:
        return self.runway_status.needs_repair

    def begin_runway_repair(self) -> None:
        self.runway_status.begin_repair()

    def total_aircraft_parking(self, _type: Any) -> int:
        return 25

    def allocated_aircraft(self, _type: Any) -> Any:
        return self._aircraft

    def can_recruit_ground_units(self, _game: Any) -> bool:
        return True


def _game(budget: float = 1000, expedited: bool = True, cp: Any = None) -> Any:
    return SimpleNamespace(
        blue=SimpleNamespace(budget=budget),
        settings=SimpleNamespace(
            expedited_aircraft_repair=expedited,
            building_repair_delay_multiplier=1.0,
            building_repair_cost_multiplier=1.0,
        ),
        theater=SimpleNamespace(
            conflicts=lambda: iter([]),
            find_control_point_by_id=lambda _id: cp if cp and cp.id == _id else None,
        ),
    )


def _damaged_base() -> tuple[_Cp, _Depot, _Squadron]:
    depot = _Depot("Fuel depot", "fuel", dead=2, price=2)
    squadron = _Squadron(in_maintenance=2, cost=15)
    cp = _Cp(
        runway=RunwayStatus(damaged=True),
        ground_objects=[depot, _Sam()],
        squadrons=[squadron],
    )
    return cp, depot, squadron


# --- repair list ------------------------------------------------------------


def test_lists_runway_buildings_and_aircraft_repairs() -> None:
    cp, depot, squadron = _damaged_base()
    repairs = base_repairs(_game(), cp)  # type: ignore[arg-type]
    assert [(r.id, r.kind, r.cost, r.turns, r.in_progress) for r in repairs] == [
        ("runway", "runway", RUNWAY_REPAIR_COST, RUNWAY_REPAIR_TURNS, False),
        (f"tgo:{depot.id}", "buildings", 4, 3, False),
        (f"squadron:{squadron.id}", "aircraft", 15, 0, False),
    ]
    assert repairs[1].label == "Fuel depot: 2 buildings"
    assert repairs[2].label == "2 damaged MiG-29s (40th TAB)"


def test_aircraft_maintenance_is_not_orderable_without_the_setting() -> None:
    cp, _, squadron = _damaged_base()
    repairs = base_repairs(_game(expedited=False), cp)  # type: ignore[arg-type]
    aircraft = repairs[-1]
    assert aircraft.in_progress and aircraft.cost == 0 and aircraft.turns == 2
    with pytest.raises(CommandError):
        order_repair(_game(expedited=False), cp, aircraft.id, GameUpdateEvents())  # type: ignore[arg-type]


def test_repairs_underway_are_listed_last_and_not_orderable() -> None:
    cp = _Cp(runway=RunwayStatus(damaged=True, repair_turns_remaining=2))
    repairs = base_repairs(_game(), cp)  # type: ignore[arg-type]
    assert [(r.id, r.turns, r.in_progress) for r in repairs] == [("runway", 2, True)]
    with pytest.raises(CommandError) as error:
        order_repair(_game(), cp, RUNWAY_REPAIR_ID, GameUpdateEvents())  # type: ignore[arg-type]
    assert "underway" in error.value.message


def test_enemy_base_has_no_repair_and_refuses_orders() -> None:
    cp = _Cp(blue=False, runway=RunwayStatus(damaged=True))
    assert base_repairs(_game(), cp) == []  # type: ignore[arg-type]
    with pytest.raises(CommandError) as error:
        order_repair(_game(), cp, RUNWAY_REPAIR_ID, GameUpdateEvents())  # type: ignore[arg-type]
    assert "not your base" in error.value.message


# --- repair commands ----------------------------------------------------------


def test_runway_repair_pays_and_starts_the_repair() -> None:
    cp = _Cp(runway=RunwayStatus(damaged=True))
    game = _game(budget=150)
    events = GameUpdateEvents()
    order_repair(game, cp, RUNWAY_REPAIR_ID, events)  # type: ignore[arg-type]
    assert game.blue.budget == 150 - RUNWAY_REPAIR_COST
    assert cp.runway_status.repair_turns_remaining == RUNWAY_REPAIR_TURNS
    assert cp in events.updated_control_points
    assert events.budget_updated


def test_runway_repair_is_refused_over_budget() -> None:
    cp = _Cp(runway=RunwayStatus(damaged=True))
    game = _game(budget=40)
    with pytest.raises(CommandError) as error:
        order_repair(game, cp, RUNWAY_REPAIR_ID, GameUpdateEvents())  # type: ignore[arg-type]
    assert error.value.status_code == 409
    assert error.value.message == (
        f"Repairing Runway costs ${RUNWAY_REPAIR_COST}M but you have only $40M available."
    )
    assert game.blue.budget == 40
    assert cp.runway_status.repair_turns_remaining is None


def test_building_repair_starts_every_destroyed_building() -> None:
    cp, depot, _ = _damaged_base()
    game = _game(budget=10)
    order_repair(game, cp, f"tgo:{depot.id}", GameUpdateEvents())  # type: ignore[arg-type]
    assert game.blue.budget == 6
    assert [u.repair_turns_remaining for u in depot.statics] == [3, 3, None]


def test_aircraft_repair_releases_the_aircraft() -> None:
    cp, _, squadron = _damaged_base()
    game = _game(budget=20)
    order_repair(game, cp, f"squadron:{squadron.id}", GameUpdateEvents())  # type: ignore[arg-type]
    assert game.blue.budget == 5
    assert squadron.released == 2


def test_repair_all_orders_everything_or_nothing() -> None:
    cp, depot, squadron = _damaged_base()
    total = RUNWAY_REPAIR_COST + 4 + 15
    poor = _game(budget=total - 1)
    with pytest.raises(CommandError) as error:
        order_all_repairs(poor, cp, GameUpdateEvents())  # type: ignore[arg-type]
    assert "Repairing everything" in error.value.message
    assert poor.blue.budget == total - 1
    assert cp.runway_status.repair_turns_remaining is None

    game = _game(budget=total)
    assert len(order_all_repairs(game, cp, GameUpdateEvents())) == 3  # type: ignore[arg-type]
    assert game.blue.budget == 0
    assert squadron.released == 2
    with pytest.raises(CommandError):
        order_all_repairs(game, cp, GameUpdateEvents())  # type: ignore[arg-type]


# --- status DTO ---------------------------------------------------------------


def test_base_status() -> None:
    cp, _, _ = _damaged_base()
    base = BaseJs.for_control_point(_game(budget=110), cp)  # type: ignore[arg-type]
    assert base.summary.name == "Krymsk"
    assert base.budget == 110
    assert [t.id for t in base.tabs] == ["airfield", "ground-forces"]
    assert [(a.name, a.category, a.operational) for a in base.air_defenses] == [
        ("SA-15 Krymsk", "SHORAD", True)
    ]
    assert [(r.kind, r.affordable) for r in base.repairs] == [
        ("runway", True),
        ("buildings", True),
        ("aircraft", True),
    ]
    assert base.repair_all_cost == RUNWAY_REPAIR_COST + 4 + 15
    assert not base.repair_all_affordable
    assert [(g.title, [(u.name, u.count) for u in g.units]) for g in base.intel] == [
        ("CAP", [("MiG-29", 10)]),
        ("Front line units", [("T-72", 2)]),
    ]
    poor = BaseJs.for_control_point(_game(budget=10), cp)  # type: ignore[arg-type]
    assert [r.affordable for r in poor.repairs] == [False, True, False]
    rich = BaseJs.for_control_point(_game(budget=500), cp)  # type: ignore[arg-type]
    assert rich.repair_all_affordable


def test_tabs_follow_the_qt_base_menu() -> None:
    assert [t.id for t in base_tabs(_Cp(blue=False))] == ["intel", "convoys"]  # type: ignore[arg-type]
    carrier = _Cp()
    carrier.can_deploy_ground_units = False
    assert [t.id for t in base_tabs(carrier)] == ["airfield"]  # type: ignore[arg-type]


# --- HTTP side ----------------------------------------------------------------


@pytest.fixture
def loaded(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, _Cp]:
    cp = _Cp(runway=RunwayStatus(damaged=True))
    game = _game(budget=150, cp=cp)
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=game), raising=False
    )
    published: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", published.append)
    return game, cp


def _request(method: str, path: str) -> tuple[int, Any]:
    messages: list[MutableMapping[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"x-api-key", ApiKeyManager.key().encode()),
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(body)


def test_get_base_route(loaded: tuple[Any, _Cp]) -> None:
    _, cp = loaded
    status, body = _request("GET", f"/control-points/{cp.id}/base")
    assert status == 200
    assert body["repairs"][0]["id"] == "runway"
    assert _request("GET", f"/control-points/{uuid4()}/base")[0] == 404


def test_repair_route_answers_the_new_status(loaded: tuple[Any, _Cp]) -> None:
    game, cp = loaded
    status, body = _request("POST", f"/control-points/{cp.id}/repairs/runway")
    assert status == 200
    assert body["summary"]["runway"]["state"] == "repairing"
    assert body["budget"] == 150 - RUNWAY_REPAIR_COST
    assert game.blue.budget == 150 - RUNWAY_REPAIR_COST


def test_repair_route_refuses_over_budget(loaded: tuple[Any, _Cp]) -> None:
    game, cp = loaded
    game.blue.budget = 10
    status, body = _request("POST", f"/control-points/{cp.id}/repair-all")
    assert status == 409
    assert "only $10M available" in body["detail"]

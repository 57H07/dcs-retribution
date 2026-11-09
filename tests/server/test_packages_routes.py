"""WEB-01.2: packages of both ATOs, create and delete package commands."""

from __future__ import annotations

import asyncio
import json
import pickle
from collections.abc import MutableMapping
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from game.ato.airtaaskingorder import AirTaskingOrder
from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.objectives import (
    CampaignObjective,
    CampaignObjectives,
    ObjectiveKind,
    ObjectiveState,
)
from game.commands import CommandError
from game.commands.packages import cancel_or_abort_package, delete_package
from game.db import Database
from game.gamelock import _GAME_LOCK
from game.server import GameContext
from game.server.app import app
from game.server.eventstream import EventStream
from game.server.packages.models import PackageJs
from game.server.security import ApiKeyManager
from game.sim import GameUpdateEvents
from game.theater.player import Player

TOT = datetime(2022, 5, 17, 7, 12)
NOW = datetime(2022, 5, 17, 6, 40)


# --- fakes -------------------------------------------------------------------


class _Flight:
    def __init__(
        self,
        task: FlightType = FlightType.BARCAP,
        cancelable: bool = True,
        missing_pilots: int = 0,
        clients: int = 0,
    ) -> None:
        self.id = uuid4()
        self.flight_type = task
        self.state = SimpleNamespace(cancelable=cancelable)
        self.unit_type = "F-16CM"
        self.count = 2
        self.client_count = clients
        self.missing_pilots = missing_pilots
        self.squadron = SimpleNamespace(name="VF-1")
        self.departure = SimpleNamespace(name="Krymsk")
        self.custom_name: str | None = None
        self.cargo = None
        self.returned = False
        self.aborted = False

    def return_pilots_and_aircraft(self) -> None:
        self.returned = True

    def abort(self) -> None:
        self.aborted = True


class _Transfers:
    def __init__(self) -> None:
        self.airlifts: dict[UUID, str] = {}
        self.cancelled: list[str] = []

    def player_airlift_for(self, flight: Any) -> str | None:
        return self.airlifts.get(flight.id)

    def cancel_transfer(self, transfer: str) -> None:
        self.cancelled.append(transfer)


class _Game:
    def __init__(self) -> None:
        self.blue = SimpleNamespace(
            player=Player.BLUE, ato=AirTaskingOrder(), transfers=_Transfers()
        )
        self.red = SimpleNamespace(
            player=Player.RED, ato=AirTaskingOrder(), transfers=_Transfers()
        )
        self.unculled = 0
        self.objectives = CampaignObjectives()

    @property
    def coalitions(self) -> list[Any]:
        return [self.blue, self.red]

    def compute_unculled_zones(self, events: GameUpdateEvents) -> None:
        self.unculled += 1


def _package(*flights: _Flight, target: str = "SA-11 Krasnodar East") -> Package:
    package = Package(SimpleNamespace(name=target), Database())  # type: ignore[arg-type]
    package.time_over_target = TOT
    for flight in flights:
        package.add_flight(flight)  # type: ignore[arg-type]
    return package


def _plan(coalition: Any, *flights: _Flight) -> Package:
    package = _package(*flights)
    coalition.ato.add_package(package)
    return package


# --- package ids ---------------------------------------------------------------


def test_packages_get_distinct_ids() -> None:
    assert _package().id != _package().id


def test_package_id_survives_save_and_load() -> None:
    package = _package()
    assert pickle.loads(pickle.dumps(package)).id == package.id


def test_old_saves_get_a_package_id() -> None:
    package = _package()
    del package.__dict__["id"]
    loaded = pickle.loads(pickle.dumps(package))
    assert isinstance(loaded.id, UUID)
    # Then kept across the next save.
    assert pickle.loads(pickle.dumps(loaded)).id == loaded.id


def test_cloned_package_gets_its_own_id() -> None:
    package = _package()
    assert Package.clone_package(package).id != package.id


# --- DTOs ----------------------------------------------------------------------


def test_package_dto_summarises_the_package() -> None:
    package = _package(
        _Flight(FlightType.DEAD, clients=1),
        _Flight(FlightType.SEAD_ESCORT, missing_pilots=1),
    )
    package.custom_name = "Hammer"
    js = PackageJs.for_package(_Game(), package, blue=True)  # type: ignore[arg-type]
    assert js.id == package.id
    assert js.blue
    assert js.task == "DEAD"
    assert js.description == "DEAD"
    assert js.custom_name == "Hammer"
    assert js.target == "SA-11 Krasnodar East"
    assert js.tot == TOT
    assert js.missing_pilots == 1
    assert [f.task for f in js.flights] == ["DEAD", "SEAD Escort"]
    first = js.flights[0]
    assert (first.aircraft, first.count, first.clients) == ("F-16CM", 2, 1)
    assert (first.squadron, first.departure) == ("VF-1", "Krymsk")


def test_empty_unscheduled_package_has_no_task_nor_tot() -> None:
    package = Package(SimpleNamespace(name="Krymsk"), Database())  # type: ignore[arg-type]
    js = PackageJs.for_package(_Game(), package, blue=False)  # type: ignore[arg-type]
    assert js.task is None
    assert js.tot is None
    assert js.description == "No mission"
    assert js.flights == []


def test_a_package_names_the_objectives_it_aims_at() -> None:
    """#194: the planner badges a package against an objective's target."""
    game = _Game()
    sam = SimpleNamespace(name="SA-11 Krasnodar East", id=uuid4())
    game.objectives.objectives = [
        CampaignObjective(
            "Blind them",
            ObjectiveKind.DESTROY,
            "IADS",
            None,
            ground_object_ids=[sam.id],
        ),
        CampaignObjective(
            "Done already",
            ObjectiveKind.DESTROY,
            "IADS",
            None,
            ground_object_ids=[sam.id],
            state=ObjectiveState.MET,
        ),
    ]
    package = Package(sam, Database())  # type: ignore[arg-type]
    elsewhere = _package()

    assert PackageJs.for_package(game, package, blue=True).objectives == [  # type: ignore[arg-type]
        "Blind them"
    ]
    assert PackageJs.for_package(game, elsewhere, blue=True).objectives == []  # type: ignore[arg-type]


def test_all_packages_of_both_coalitions() -> None:
    game = _Game()
    blue = _plan(game.blue, _Flight())
    red = _plan(game.red, _Flight(FlightType.STRIKE))
    packages = PackageJs.all_in_game(game)  # type: ignore[arg-type]
    assert [(p.id, p.blue) for p in packages] == [(blue.id, True), (red.id, False)]


# --- delete command ------------------------------------------------------------


def test_delete_removes_a_cancelable_package() -> None:
    game = _Game()
    flight = _Flight()
    package = _plan(game.blue, flight)
    events = GameUpdateEvents()

    assert delete_package(game, package.id, events, NOW)  # type: ignore[arg-type]

    assert game.blue.ato.packages == []
    assert flight.returned
    assert events.deleted_flights == {flight.id}
    assert game.unculled == 1


def test_delete_works_on_the_enemy_ato() -> None:
    game = _Game()
    package = _plan(game.red, _Flight())
    delete_package(game, package.id, GameUpdateEvents(), NOW)  # type: ignore[arg-type]
    assert game.red.ato.packages == []


def test_delete_cancels_the_player_airlift() -> None:
    game = _Game()
    flight = _Flight(FlightType.TRANSPORT)
    game.blue.transfers.airlifts[flight.id] = "convoy"
    package = _plan(game.blue, flight)
    cancel_or_abort_package(game, package, GameUpdateEvents())  # type: ignore[arg-type]
    assert game.blue.transfers.cancelled == ["convoy"]


def test_delete_aborts_flights_under_way() -> None:
    game = _Game()
    waiting = _Flight()
    flying = _Flight(cancelable=False)
    package = _plan(game.blue, waiting, flying)
    events = GameUpdateEvents()

    removed = cancel_or_abort_package(game, package, events, NOW)  # type: ignore[arg-type]

    assert not removed
    assert game.blue.ato.packages == [package]
    assert package.flights == [flying]
    assert flying.aborted
    assert events.deleted_flights == {waiting.id}
    assert events.updated_flights == {flying}


def test_delete_an_unknown_package_is_a_404() -> None:
    with pytest.raises(CommandError) as exc:
        delete_package(_Game(), uuid4(), GameUpdateEvents(), NOW)  # type: ignore[arg-type]
    assert exc.value.status_code == 404


# --- HTTP side -----------------------------------------------------------------


@pytest.fixture
def game(monkeypatch: pytest.MonkeyPatch) -> _Game:
    game = _Game()
    sim = SimpleNamespace(current_time_in_sim_if_game_loaded=NOW)
    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(game=game, sim_controller=sim),
        raising=False,
    )
    return game


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[GameUpdateEvents]:
    events: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", events.append)
    return events


def _request(method: str, path: str, body: Any = None) -> tuple[int, Any]:
    """Send one request through the whole ASGI app (key, routing, lock, errors)."""
    messages: list[MutableMapping[str, Any]] = []
    payload = b"" if body is None else json.dumps(body).encode()

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

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
            (b"content-type", b"application/json"),
            (b"x-api-key", ApiKeyManager.key().encode()),
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    data = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(data) if data else None


def test_list_packages_route(game: _Game) -> None:
    package = _plan(game.blue, _Flight(missing_pilots=2))
    _plan(game.red, _Flight(FlightType.STRIKE))
    status, body = _request("GET", "/packages/")
    assert status == 200
    assert [(p["blue"], p["task"]) for p in body] == [
        (True, "BARCAP"),
        (False, "Strike"),
    ]
    assert body[0]["id"] == str(package.id)
    assert body[0]["tot"] == "2022-05-17T07:12:00"
    assert body[0]["missing_pilots"] == 2


def test_list_packages_without_a_campaign(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    assert _request("GET", "/packages/") == (200, [])


def test_delete_route_publishes_the_deleted_flights(
    game: _Game, published: list[GameUpdateEvents]
) -> None:
    flight = _Flight()
    package = _plan(game.blue, flight)

    assert _request("DELETE", f"/packages/{package.id}") == (204, None)

    assert game.blue.ato.packages == []
    assert [events.deleted_flights for events in published] == [{flight.id}]


def test_delete_route_keeps_the_asap_tot_current(game: _Game) -> None:
    package = _plan(game.blue, _Flight(), _Flight(cancelable=False))
    package.auto_asap = True
    asap: list[datetime] = []
    package.set_tot_asap = asap.append  # type: ignore[method-assign,assignment]
    assert _request("DELETE", f"/packages/{package.id}") == (204, None)
    assert asap == [NOW]


def test_delete_route_unknown_package(game: _Game) -> None:
    assert _request("DELETE", f"/packages/{uuid4()}") == (
        404,
        {"detail": "This package is no longer planned."},
    )


def test_create_route_unknown_target(game: _Game) -> None:
    game.db = SimpleNamespace(front_lines=Database())  # type: ignore[attr-defined]
    status, body = _request(
        "POST", "/packages/", {"target_kind": "front-line", "target_id": str(uuid4())}
    )
    assert (status, body) == (404, {"detail": "This target no longer exists."})


def test_create_route_refuses_enemy_downed_pilots(game: _Game) -> None:
    pilot = SimpleNamespace(is_friendly=lambda player: player is Player.RED)
    pilot_id = uuid4()
    game.db = SimpleNamespace(downed_pilots=Database())  # type: ignore[attr-defined]
    game.db.downed_pilots.add(pilot_id, pilot)  # type: ignore[attr-defined]
    status, _ = _request(
        "POST",
        "/packages/",
        {"target_kind": "downed-pilot", "target_id": str(pilot_id)},
    )
    assert status == 409


def test_create_route_without_a_campaign(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    status, body = _request(
        "POST", "/packages/", {"target_kind": "tgo", "target_id": str(uuid4())}
    )
    assert (status, body) == (409, {"detail": "No campaign is loaded."})


def test_select_flight_route_tells_the_web_panel(
    monkeypatch: pytest.MonkeyPatch, published: list[GameUpdateEvents]
) -> None:
    """Clicking a flight plan on the map selects it in the web packages panel."""
    flight = _Flight()
    flights = Database[Any]()
    flights.add(flight.id, flight)
    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(game=SimpleNamespace(db=SimpleNamespace(flights=flights))),
        raising=False,
    )
    status, _ = _request("POST", f"/flights/{flight.id}/select")
    assert status == 200
    assert [events.selected_flight for events in published] == [flight.id]

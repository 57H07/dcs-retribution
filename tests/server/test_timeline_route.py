"""WEB-01.4: mission timeline read model and route."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from game.ato.flighttype import FlightType
from game.server import GameContext
from game.server.game.timeline import TimelineJs
from tests.server.test_command_view_commands import _request

START = datetime(2022, 5, 17, 6, 30)


def _minutes(m: float) -> datetime:
    return START + timedelta(minutes=m)


class _Plan:
    def __init__(self, startup: float, tot: float, landing: float | None) -> None:
        self._startup = _minutes(startup)
        self.tot = _minutes(tot)
        self._landing = None if landing is None else _minutes(landing)

    def startup_time(self) -> datetime:
        return self._startup

    @property
    def landing_time(self) -> datetime:
        if self._landing is None:
            raise NotImplementedError
        return self._landing


class _Flight:
    def __init__(
        self, startup: float, tot: float, landing: float | None = None
    ) -> None:
        self.id: UUID = uuid4()
        self.flight_plan = _Plan(startup, tot, landing)


class _Package:
    def __init__(
        self,
        *flights: _Flight,
        tot: float,
        task: FlightType | None = FlightType.STRIKE,
        target: str = "Ammo depot",
    ) -> None:
        self.id: UUID = uuid4()
        self.flights = list(flights)
        self.primary_task = task
        self.target = SimpleNamespace(name=target)
        self.time_over_target = _minutes(tot)


def _game(*packages: _Package) -> Any:
    return SimpleNamespace(
        conditions=SimpleNamespace(start_time=START),
        blue=SimpleNamespace(ato=SimpleNamespace(packages=list(packages))),
    )


def test_package_spans_first_startup_to_last_landing() -> None:
    lead = _Flight(startup=10, tot=40, landing=70)
    escort = _Flight(startup=5, tot=38, landing=80)
    planned = _Package(lead, escort, tot=40)
    timeline = TimelineJs.for_game(_game(planned))
    assert timeline.start_time == "06:30:00"
    [package] = timeline.packages
    assert package.id == str(planned.id)
    assert package.task == "Strike"
    assert package.target == "Ammo depot"
    assert (package.startup, package.tot, package.landing) == (300, 2400, 4800)
    assert package.flight_ids == [str(lead.id), str(escort.id)]


def test_plan_without_landing_ends_at_its_tot() -> None:
    timeline = TimelineJs.for_game(
        _game(_Package(_Flight(startup=0, tot=20, landing=None), tot=20))
    )
    assert timeline.packages[0].landing == 1200


def test_empty_packages_are_skipped_and_others_sorted_by_startup() -> None:
    late = _Package(_Flight(startup=30, tot=60, landing=90), tot=60, target="Late")
    early = _Package(
        _Flight(startup=-5, tot=20, landing=50),
        tot=20,
        task=FlightType.BARCAP,
        target="Early",
    )
    empty = _Package(tot=10, task=None, target="Empty")
    timeline = TimelineJs.for_game(_game(late, empty, early))
    assert [p.target for p in timeline.packages] == ["Early", "Late"]
    assert timeline.packages[0].startup == -300
    assert timeline.packages[0].task == "BARCAP"


def _load(monkeypatch: pytest.MonkeyPatch, game: Any) -> None:
    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(game=game, sim_controller=None),
        raising=False,
    )


def test_route_is_null_without_a_campaign(monkeypatch: pytest.MonkeyPatch) -> None:
    _load(monkeypatch, None)
    assert _request("GET", "/game/timeline") == (200, None)


def test_route(monkeypatch: pytest.MonkeyPatch) -> None:
    flight = _Flight(startup=10, tot=40, landing=70)
    package = _Package(flight, tot=40)
    _load(monkeypatch, _game(package))
    status, body = _request("GET", "/game/timeline")
    assert status == 200
    assert body == {
        "start_time": "06:30:00",
        "packages": [
            {
                "id": str(package.id),
                "task": "Strike",
                "target": "Ammo depot",
                "startup": 600,
                "tot": 2400,
                "landing": 4200,
                "flight_ids": [str(flight.id)],
            }
        ],
    }

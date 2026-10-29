"""WEB-01.1: top bar data and turn actions (take off, fix TOTs, sim speed)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import MutableMapping
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dcs.cloud_presets import CLOUD_PRESETS
from dcs.weather import Weather as PydcsWeather, Wind

from game.ato.flightstate import Uninitialized
from game.commands import (
    CommandError,
    fix_past_tots,
    flights_missing_pilots,
    generate_mission,
    max_player_count,
    packages_starting_in_the_past,
    set_sim_speed,
)
from game.commands import mission as mission_module
from game.gamelock import _GAME_LOCK
from game.server import GameContext
from game.server.app import app
from game.server.dependencies import QtCallbacks, QtContext, UiOptions
from game.server.eventstream import EventStream
from game.server.game import topbar
from game.server.game.topbar import (
    SimSpeedJs,
    TopBarJs,
    WeatherJs,
    economy_assessment,
    forces_assessment,
)
from game.settings.settings import FastForwardStopCondition
from game.sim import GameUpdateEvents
from game.sim.simspeedsetting import SimSpeedSetting
from game.server.security import ApiKeyManager
from game.timeofday import TimeOfDay
from game.utils import nautical_miles
from game.weather.clouds import Clouds
from game.weather.fog import Fog
from game.weather.wind import WindConditions

NOW = datetime(2022, 5, 17, 6, 40)


# --- fakes -------------------------------------------------------------------


class _State:
    def __init__(self, waiting: bool) -> None:
        self.is_waiting_for_start = waiting


class _Flight:
    def __init__(
        self,
        startup: datetime = NOW + timedelta(minutes=5),
        waiting: bool = True,
        missing_pilots: int = 0,
        client_count: int = 0,
        name: str = "F-16 x2",
    ) -> None:
        self.state: Any = _State(waiting)
        self.missing_pilots = missing_pilots
        self.client_count = client_count
        self.flight_plan = SimpleNamespace(startup_time=lambda: startup)
        self.name = name

    def __str__(self) -> str:
        return self.name


class _Target:
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name


class _Package:
    def __init__(self, *flights: _Flight, target: str = "Krasnodar") -> None:
        self.flights = list(flights)
        self.primary_task = "DEAD"
        self.target = _Target(target)
        self.time_over_target = NOW


class _Sim:
    """Stands in for SimController."""

    def __init__(self) -> None:
        self.current_time_in_sim = NOW
        self.current_time_in_sim_if_game_loaded: datetime | None = NOW
        self.completed = False
        self.simulation_speed = SimSpeedSetting.PAUSED
        self.calls: list[str] = []
        self.lock_held: list[bool] = []

    def run_to_first_contact(self) -> None:
        self.calls.append("first_contact")

    def generate_miz(self, output: Path) -> None:
        self.lock_held.append(_GAME_LOCK._is_owned())  # type: ignore[attr-defined]
        self.calls.append(f"miz:{output.name}")

    def set_simulation_speed(self, speed: SimSpeedSetting) -> None:
        self.calls.append(f"speed:{speed.name}")
        self.simulation_speed = speed


def _game(*packages: _Package, turn: int = 3) -> Any:
    def ato_has_clients() -> bool:
        return any(f.client_count for p in packages for f in p.flights)

    return SimpleNamespace(
        turn=turn,
        blue=SimpleNamespace(ato=SimpleNamespace(packages=list(packages))),
        settings=SimpleNamespace(
            fast_forward_stop_condition=FastForwardStopCondition.DISABLED
        ),
        ato_has_clients=ato_has_clients,
    )


@pytest.fixture(autouse=True)
def _no_mission_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mission_module.persistency, "mission_path_for", lambda name: Path("M") / name
    )


# --- game.commands.mission -----------------------------------------------------


def test_flights_missing_pilots_lists_each_flight() -> None:
    short = _Flight(missing_pilots=1)
    package = _Package(_Flight(), short)
    assert flights_missing_pilots(_game(package)) == [(package, short)]


def test_packages_starting_in_the_past() -> None:
    late = _Package(_Flight(), _Flight(startup=NOW - timedelta(minutes=1)))
    on_time = _Package(_Flight())
    airborne = _Package(_Flight(startup=NOW - timedelta(hours=1), waiting=False))
    uninitialized_flight = _Flight(startup=NOW - timedelta(hours=1))
    uninitialized_flight.state = Uninitialized.__new__(Uninitialized)
    uninitialized = _Package(uninitialized_flight)
    game = _game(late, on_time, airborne, uninitialized)
    assert packages_starting_in_the_past(game, NOW) == [late]


def test_fix_past_tots_moves_only_late_packages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Estimator:
        def __init__(self, package: _Package) -> None:
            self.package = package

        def earliest_tot(self, now: datetime) -> datetime:
            return now + timedelta(minutes=30)

    monkeypatch.setattr(mission_module, "TotEstimator", Estimator)
    late = _Package(_Flight(startup=NOW - timedelta(minutes=1)))
    on_time = _Package(_Flight())
    assert fix_past_tots(_game(late, on_time), NOW) == [late]
    assert late.time_over_target == NOW + timedelta(minutes=30)
    assert on_time.time_over_target == NOW


def test_max_player_count_sums_client_slots() -> None:
    game = _game(_Package(_Flight(client_count=2), _Flight(client_count=1)))
    assert max_player_count(game) == 3


def test_generate_mission_writes_the_miz() -> None:
    sim = _Sim()
    path = generate_mission(_game(_Package(_Flight())), sim)
    assert path == Path("M") / "retribution_nextturn.miz"
    assert sim.calls == ["miz:retribution_nextturn.miz"]


@pytest.mark.parametrize(
    "condition,fast_forwards",
    [
        (FastForwardStopCondition.DISABLED, False),
        (FastForwardStopCondition.MANUAL, False),
        (FastForwardStopCondition.PLAYER_STARTUP, True),
        (FastForwardStopCondition.FIRST_CONTACT, True),
    ],
)
def test_generate_mission_fast_forwards_when_set(
    condition: FastForwardStopCondition, fast_forwards: bool
) -> None:
    game = _game(_Package(_Flight()))
    game.settings.fast_forward_stop_condition = condition
    sim = _Sim()
    generate_mission(game, sim)
    assert ("first_contact" in sim.calls) is fast_forwards
    assert sim.calls[-1] == "miz:retribution_nextturn.miz"


def test_generate_mission_refuses_before_the_campaign_begins() -> None:
    sim = _Sim()
    with pytest.raises(CommandError, match="Begin the campaign"):
        generate_mission(_game(turn=0), sim)
    assert sim.calls == []


def test_generate_mission_refuses_missing_pilots() -> None:
    sim = _Sim()
    game = _game(_Package(_Flight(missing_pilots=1)))
    with pytest.raises(CommandError, match="missing pilots"):
        generate_mission(game, sim)
    assert sim.calls == []


# --- game.commands.sim ---------------------------------------------------------


def test_set_sim_speed_runs_the_sim() -> None:
    sim = _Sim()
    set_sim_speed(_game(), sim, SimSpeedSetting.X5)
    assert sim.calls == ["speed:X5"]


def test_set_sim_speed_refuses_before_the_campaign_begins() -> None:
    sim = _Sim()
    with pytest.raises(CommandError, match="Begin the campaign"):
        set_sim_speed(_game(turn=0), sim, SimSpeedSetting.X1)
    set_sim_speed(_game(turn=0), sim, SimSpeedSetting.PAUSED)
    assert sim.calls == ["speed:PAUSED"]


def test_set_sim_speed_refuses_a_complete_sim() -> None:
    sim = _Sim()
    sim.completed = True
    with pytest.raises(CommandError, match="complete"):
        set_sim_speed(_game(), sim, SimSpeedSetting.X1)


# --- DTOs ----------------------------------------------------------------------


def _conditions(clouds: Clouds | None, fog: Fog | None = None) -> Any:
    return SimpleNamespace(
        start_time=NOW,
        time_of_day=TimeOfDay.Dawn,
        weather=SimpleNamespace(
            clouds=clouds,
            fog=fog,
            wind=WindConditions(Wind(270, 5), Wind(280, 10), Wind(290, 20)),
        ),
    )


def test_weather_without_clouds() -> None:
    weather = WeatherJs.from_conditions(_conditions(None))
    assert weather.clouds == "Clear"
    assert weather.precipitation == "No rain"
    assert weather.fog == "No fog"
    assert weather.cloud_base_m is None
    assert [(w.altitude, w.direction, w.speed_kt) for w in weather.winds] == [
        ("GL", 270, 9),
        ("FL08", 280, 19),
        ("FL26", 290, 38),
    ]


def test_weather_gives_the_cloud_base_and_fog() -> None:
    clouds = Clouds(
        base=2400,
        density=4,
        thickness=500,
        precipitation=PydcsWeather.Preceptions.Thunderstorm,
    )
    fog = Fog(visibility=nautical_miles(2.04), thickness=100)
    weather = WeatherJs.from_conditions(_conditions(clouds, fog))
    assert weather.clouds == "Mostly Cloudy"
    assert weather.precipitation == "Thunderstorm"
    assert weather.fog == "Fog vis: 2.0nm"
    assert (weather.cloud_base_m, weather.cloud_base_ft) == (2400, 7874)


def test_weather_names_the_cloud_preset() -> None:
    preset = next(p.value for p in CLOUD_PRESETS.values() if "Rain" in p.value.name)
    clouds = Clouds(
        base=1000,
        density=0,
        thickness=0,
        precipitation=PydcsWeather.Preceptions.None_,
        preset=preset,
    )
    weather = WeatherJs.from_conditions(_conditions(clouds))
    assert weather.clouds == preset.description.splitlines()[0].split("##")[1].strip()
    assert weather.precipitation == "Rain"


@pytest.mark.parametrize(
    "own,enemy,text",
    [
        (10, 0, "enemy eliminated"),
        (5, 10, "outnumbered"),
        (7, 10, "slightly outnumbered"),
        (10, 10, "evenly matched"),
        (13, 10, "slight advantage"),
        (20, 10, "strong advantage"),
    ],
)
def test_forces_assessment(own: int, enemy: int, text: str) -> None:
    assert forces_assessment(own, enemy) == text


def test_economy_assessment() -> None:
    assert economy_assessment(10, 0) == "enemy economy ruined"
    assert economy_assessment(5, 10) == "strong disadvantage"
    assert economy_assessment(20, 10) == "strong advantage"


def _top_bar_game(turn: int = 4) -> Any:
    game = _game(_Package(_Flight(client_count=2)), turn=turn)
    game.campaign_name = "Slava Ukraini"
    game.theater = SimpleNamespace(terrain=SimpleNamespace(name="Caucasus"))
    game.blue.faction = SimpleNamespace(name="Ukraine 2020")
    game.blue.budget = 1240.456
    game.red = SimpleNamespace(faction=SimpleNamespace(name="Russia 2020"))
    game.conditions = _conditions(None)
    units = SimpleNamespace
    game.game_stats = SimpleNamespace(
        data_per_turn=[
            SimpleNamespace(
                allied_units=units(aircraft_count=96, vehicles_count=64),
                enemy_units=units(aircraft_count=132, vehicles_count=52),
            )
        ]
    )
    return game


@pytest.fixture
def fake_income(monkeypatch: pytest.MonkeyPatch) -> None:
    class Income:
        def __init__(self, game: Any, player: Any) -> None:
            self.total = 180.0 if player.name == "BLUE" else 90.0

    monkeypatch.setattr(topbar, "Income", Income)


def test_top_bar_dto(fake_income: None) -> None:
    bar = TopBarJs.from_game(_top_bar_game(), SimSpeedSetting.X2, NOW, True)
    assert bar.campaign_name == "Slava Ukraini"
    assert bar.theater == "Caucasus"
    assert (bar.player_faction, bar.enemy_faction) == ("Ukraine 2020", "Russia 2020")
    assert bar.turn == 4
    assert (bar.mission_start_date, bar.mission_start_time) == ("17 May 2022", "06:40")
    assert bar.time_of_day == "dawn"
    assert (bar.budget, bar.income) == (1240.46, 180.0)
    assert (bar.air.friendly, bar.air.enemy) == (96, 132)
    assert bar.air.assessment == "slightly outnumbered"
    assert bar.ground.assessment == "slight advantage"
    assert bar.economy == "strong advantage"
    assert bar.max_player_count == 2
    assert bar.sim.speed is SimSpeedJs.X2
    assert bar.sim.time == "06:40:00"
    assert bar.show_sim_speed_controls


def test_top_bar_gathers_intel_on_turn_zero(fake_income: None) -> None:
    bar = TopBarJs.from_game(_top_bar_game(turn=0), SimSpeedSetting.PAUSED, None, False)
    assert bar.air.assessment == bar.ground.assessment == "gathering intel"
    assert bar.sim.time is None


def test_sim_speed_mirrors_every_setting() -> None:
    for setting in SimSpeedSetting:
        assert SimSpeedJs.from_setting(setting).to_setting() is setting
        assert SimSpeedJs.from_setting(setting).value == setting.text.lower()


def test_budget_event_is_published_to_the_client() -> None:
    from game.server.eventstream.models import GameUpdateEventsJs

    events = GameUpdateEvents().update_budget()
    assert not events.empty
    assert GameUpdateEventsJs.from_events(events, None).budget_updated


# --- HTTP side -----------------------------------------------------------------


class _Recorder:
    def __init__(self) -> None:
        self.missions = 0
        self.lock_held: list[bool] = []

    def mission_generated(self) -> None:
        self.lock_held.append(_GAME_LOCK._is_owned())  # type: ignore[attr-defined]
        self.missions += 1

    def callbacks(self) -> QtCallbacks:
        def ignore(_: Any) -> None:
            pass

        return QtCallbacks(
            ignore, ignore, ignore, ignore, mission_generated=self.mission_generated
        )


@pytest.fixture
def sim() -> _Sim:
    return _Sim()


def _load(monkeypatch: pytest.MonkeyPatch, game: Any, sim: _Sim) -> None:
    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(game=game, sim_controller=sim),
        raising=False,
    )
    monkeypatch.setattr(QtContext, "_callbacks", None)


def _request(method: str, path: str, body: Any = None) -> tuple[int, Any]:
    messages: list[MutableMapping[str, Any]] = []
    payload = b"" if body is None else json.dumps(body).encode()

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(message)

    headers = [
        (b"host", b"testserver"),
        (b"x-api-key", ApiKeyManager.key().encode()),
    ]
    if body is not None:
        headers.append((b"content-type", b"application/json"))
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
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    raw = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(raw) if raw else None


def test_top_bar_route_is_null_without_a_campaign(
    monkeypatch: pytest.MonkeyPatch, sim: _Sim
) -> None:
    _load(monkeypatch, None, sim)
    assert _request("GET", "/game/top-bar") == (200, None)


def test_top_bar_route(
    monkeypatch: pytest.MonkeyPatch, sim: _Sim, fake_income: None
) -> None:
    _load(monkeypatch, _top_bar_game(), sim)
    monkeypatch.setattr(UiOptions, "show_sim_speed_controls", True)
    status, body = _request("GET", "/game/top-bar")
    assert status == 200
    assert body["turn"] == 4
    assert body["budget"] == 1240.46
    assert body["sim"] == {"speed": "paused", "time": "06:40:00"}
    assert body["show_sim_speed_controls"] is True
    assert body["weather"]["clouds"] == "Clear"


def test_mission_checks_route(monkeypatch: pytest.MonkeyPatch, sim: _Sim) -> None:
    game = _game(
        _Package(_Flight(missing_pilots=1, name="Viper")),
        _Package(_Flight(startup=NOW - timedelta(minutes=2)), target="Maykop"),
    )
    _load(monkeypatch, game, sim)
    status, body = _request("GET", "/game/mission/checks")
    assert status == 200
    assert body == {
        "has_player_pilots": False,
        "flights_missing_pilots": ["DEAD Krasnodar: Viper"],
        "packages_starting_in_the_past": ["DEAD Maykop"],
        "max_player_count": 0,
    }


def test_mission_checks_without_a_campaign(
    monkeypatch: pytest.MonkeyPatch, sim: _Sim
) -> None:
    _load(monkeypatch, None, sim)
    assert _request("GET", "/game/mission/checks") == (
        409,
        {"detail": "No campaign is loaded."},
    )


def test_fix_tots_route_publishes_the_flights(
    monkeypatch: pytest.MonkeyPatch, sim: _Sim
) -> None:
    class Estimator:
        def __init__(self, package: _Package) -> None:
            pass

        def earliest_tot(self, now: datetime) -> datetime:
            return now + timedelta(minutes=20)

    monkeypatch.setattr(mission_module, "TotEstimator", Estimator)
    late_flight = _Flight(startup=NOW - timedelta(minutes=2))
    late = _Package(late_flight)
    _load(monkeypatch, _game(late, _Package(_Flight())), sim)
    published: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", published.append)

    assert _request("POST", "/game/mission/fix-tots") == (
        200,
        {"packages": ["DEAD Krasnodar"]},
    )
    assert late.time_over_target == NOW + timedelta(minutes=20)
    assert [e.updated_flights for e in published] == [{late_flight}]


def test_generate_mission_route_opens_the_qt_waiting_window(
    monkeypatch: pytest.MonkeyPatch, sim: _Sim
) -> None:
    _load(monkeypatch, _game(_Package(_Flight())), sim)
    qt = _Recorder()
    monkeypatch.setattr(QtContext, "_callbacks", qt.callbacks())
    status, body = _request("POST", "/game/mission")
    assert status == 200
    assert body == {"path": str(Path("M") / "retribution_nextturn.miz")}
    assert sim.lock_held == [True]
    assert qt.missions == 1


def test_generate_mission_route_refuses_missing_pilots(
    monkeypatch: pytest.MonkeyPatch, sim: _Sim
) -> None:
    _load(monkeypatch, _game(_Package(_Flight(missing_pilots=2))), sim)
    qt = _Recorder()
    monkeypatch.setattr(QtContext, "_callbacks", qt.callbacks())
    status, body = _request("POST", "/game/mission")
    assert status == 409
    assert "missing pilots" in body["detail"]
    assert sim.calls == []
    assert qt.missions == 0


def test_sim_speed_route(monkeypatch: pytest.MonkeyPatch, sim: _Sim) -> None:
    _load(monkeypatch, _game(), sim)
    assert _request("PUT", "/game/sim/speed", {"speed": "10x"}) == (
        200,
        {"speed": "10x", "time": "06:40:00"},
    )
    assert sim.calls == ["speed:X10"]


def test_sim_speed_route_rejects_an_unknown_speed(
    monkeypatch: pytest.MonkeyPatch, sim: _Sim
) -> None:
    _load(monkeypatch, _game(), sim)
    status, _ = _request("PUT", "/game/sim/speed", {"speed": "3x"})
    assert status == 422
    assert sim.calls == []


def test_sim_speed_route_refuses_before_the_campaign_begins(
    monkeypatch: pytest.MonkeyPatch, sim: _Sim
) -> None:
    _load(monkeypatch, _game(turn=0), sim)
    status, body = _request("PUT", "/game/sim/speed", {"speed": "1x"})
    assert status == 409
    assert "Begin the campaign" in body["detail"]

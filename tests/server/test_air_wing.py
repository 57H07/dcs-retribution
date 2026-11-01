"""WEB-03: the air wing screen, against a real campaign where possible."""

from __future__ import annotations

import asyncio
import json
import pickle
from collections.abc import Iterator, MutableMapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from game import Game
from game.ato.flighttype import FlightType
from game.commands import (
    CommandError,
    create_player_pilot,
    find_squadron,
    livery_choices,
    rename_pilot,
    set_auto_assignable,
    set_pilot_on_leave,
    set_pilot_player,
    set_primary_task,
    set_squadron_livery,
    transfer_destinations,
    transfer_squadron,
)
from game.server import GameContext
from game.server.airwing.models import AirWingJs
from game.server.app import app
from game.server.dependencies import QtContext
from game.server.security import ApiKeyManager
from game.sim import GameUpdateEvents
from game.squadrons import Pilot, Squadron
from game.squadrons.pilot import PilotStatus
from game.theater.player import Player
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)


@pytest.fixture(scope="module")
def game(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Game]:
    missing = Path(tmp_path_factory.mktemp("payloads")) / "none"
    with repository_payloads_only(missing):
        yield generate_reference_game()


@pytest.fixture(autouse=True)
def _loaded(game: Game, monkeypatch: pytest.MonkeyPatch) -> None:
    sim = SimpleNamespace(current_time_in_sim=game.conditions.start_time)
    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(game=game, sim_controller=sim),
        raising=False,
    )
    monkeypatch.setattr(QtContext, "_callbacks", None)


def _blue(game: Game) -> list[Squadron]:
    return list(game.blue.air_wing.iter_squadrons())


def _transferable(game: Game) -> tuple[Squadron, Any]:
    """A squadron with an idle aircraft and a base it can go to."""
    for squadron in _blue(game):
        if squadron.destination is not None or squadron.untasked_aircraft == 0:
            continue
        for option in transfer_destinations(squadron):
            if option.refusal is None:
                return squadron, option.control_point
    pytest.fail("The reference game has no squadron that can transfer.")


def _request(method: str, path: str, body: Any = None) -> tuple[int, Any]:
    payload = b"" if body is None else json.dumps(body).encode()
    messages: list[MutableMapping[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(message)

    route, _, query = path.partition("?")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": route,
        "raw_path": route.encode(),
        "root_path": "",
        "query_string": query.encode(),
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
    raw = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(raw) if raw else None


def _sheet(game: Game, squadron: Squadron) -> dict[str, Any]:
    status, body = _request("GET", "/air-wing")
    assert status == 200
    for base in body["bases"]:
        for row in base["squadrons"]:
            if row["id"] == str(squadron.id):
                return cast(dict[str, Any], row)
    pytest.fail(f"{squadron} is not in the air wing.")


# --- Read model ----------------------------------------------------------------


def test_squadrons_are_grouped_by_base_with_their_sheet(game: Game) -> None:
    status, body = _request("GET", "/air-wing")
    assert status == 200
    squadrons = _blue(game)
    assert body["blue"] is True
    assert body["squadron_count"] == len(squadrons)
    assert body["aircraft_count"] == sum(s.owned_aircraft for s in squadrons)
    names = [base["name"] for base in body["bases"]]
    assert names == sorted(names)
    for base in body["bases"]:
        for row in base["squadrons"]:
            assert row["base"] == base["name"]
    squadron = squadrons[0]
    sheet = _sheet(game, squadron)
    assert sheet["name"] == str(squadron)
    assert sheet["aircraft"] == squadron.aircraft.display_name
    assert sheet["owned"] == squadron.owned_aircraft
    assert sheet["pilots_ready"] == len(squadron.active_pilots)
    assert sheet["sidc"][3] == "3"  # Friend.
    assert sheet["primary_task"] == squadron.primary_task.value
    tasks = {t["task"]: t["auto_assign"] for t in sheet["tasks"]}
    assert squadron.primary_task.value in tasks
    assert sheet["order"]["squadron_id"] == str(squadron.id)
    assert len(sheet["pilots"]) == len(squadron.current_roster)


def test_the_enemy_air_wing_has_no_orders(game: Game) -> None:
    status, body = _request("GET", "/air-wing?enemy=true")
    assert status == 200
    assert body["blue"] is False
    rows = [row for base in body["bases"] for row in base["squadrons"]]
    assert len(rows) == len(list(game.red.air_wing.iter_squadrons()))
    assert all(row["order"] is None for row in rows)
    assert rows[0]["sidc"][3] != "3"


def test_no_campaign_answers_null(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(GameContext, "_game_model", SimpleNamespace(game=None))
    assert _request("GET", "/air-wing") == (200, None)


def test_inventory_lists_idle_aircraft_and_flights(game: Game) -> None:
    body = AirWingJs.for_coalition(game, Player.BLUE)
    idle = [row for row in body.inventory if not row.allocated]
    assert len(idle) >= sum(s.untasked_aircraft for s in _blue(game))
    assert {row.task for row in idle} >= {"Idle"}
    assert len({row.key for row in body.inventory}) == len(body.inventory)


def test_pilot_statuses(game: Game) -> None:
    squadron = _blue(game)[1]
    roster = squadron.current_roster
    down, prisoner, injured, leave, dead = roster[:5]
    down.go_down()
    prisoner.go_down()
    base = game.red.air_wing.iter_squadrons().__next__().location
    prisoner.take_prisoner(base.id)
    injured.begin_recovery(2)
    leave.send_on_leave()
    dead.kill()

    pilots = {p["id"]: p for p in _sheet(game, squadron)["pilots"]}
    assert pilots[str(down.id)]["status_text"] == "Down · awaiting CSAR"
    assert pilots[str(down.id)]["status"] == "down"
    assert pilots[str(prisoner.id)]["status"] == "prisoner"
    assert pilots[str(prisoner.id)]["note"] == f"Held at {base.name}"
    assert pilots[str(prisoner.id)]["player_refusal"] is not None
    assert pilots[str(injured.id)]["return_turn"] == game.turn + 2
    assert (
        pilots[str(injured.id)]["status_text"] == f"Medical · back T{game.turn + 2:02d}"
    )
    assert pilots[str(injured.id)]["leave_refusal"] is not None
    assert pilots[str(leave.id)]["status"] == "leave"
    assert pilots[str(dead.id)]["status"] == "dead"
    assert pilots[str(dead.id)]["alive"] is False
    assert pilots[str(dead.id)]["player_refusal"] is not None
    # The fallen come last.
    assert list(pilots.values())[-1]["id"] == str(dead.id)

    injured.begin_recovery(1)
    assert "1 pilot back from medical" in _sheet(game, squadron)["next_turn"]


def test_next_turn_tells_arrivals(game: Game) -> None:
    squadron = _blue(game)[2]
    squadron.pending_deliveries = 2
    try:
        assert "2 aircraft arriving" in _sheet(game, squadron)["next_turn"]
    finally:
        squadron.pending_deliveries = 0


# --- Tasks and liveries --------------------------------------------------------


def test_primary_task_and_auto_assign_routes(game: Game) -> None:
    squadron = _blue(game)[0]
    base = f"/squadrons/{squadron.id}"
    task = next(t for t in FlightType if squadron.capable_of(t))
    assert _request("PUT", f"{base}/primary-task", {"task": task.value}) == (204, None)
    assert squadron.primary_task is task

    body = {"task": task.value, "enabled": True}
    assert _request("PUT", f"{base}/auto-assign", body) == (204, None)
    assert task in squadron.auto_assignable_mission_types
    assert squadron.can_auto_assign(task)
    body["enabled"] = False
    assert _request("PUT", f"{base}/auto-assign", body) == (204, None)
    assert task not in squadron.auto_assignable_mission_types

    status, refused = _request("PUT", f"{base}/primary-task", {"task": "Knitting"})
    assert (status, refused["detail"]) == (409, "Knitting is not a mission type.")


def test_a_task_the_aircraft_cannot_fly_is_refused(game: Game) -> None:
    squadron = next(
        s for s in _blue(game) if any(not s.capable_of(task) for task in FlightType)
    )
    task = next(t for t in FlightType if not squadron.capable_of(t))
    with pytest.raises(CommandError, match="cannot fly"):
        set_primary_task(squadron, task)
    with pytest.raises(CommandError, match="cannot fly"):
        set_auto_assignable(squadron, task, True)
    assert task not in squadron.auto_assignable_mission_types


def _liveried_squadron(**kwargs: Any) -> Any:
    class Livery:
        def __init__(self, name: str, countries: Any = None) -> None:
            self.id = name.lower()
            self.name = name
            self.countries = countries

        def __lt__(self, other: Any) -> bool:
            return self.name < other.name

    liveries = [Livery("Zulu"), Livery("Alpha"), Livery("Other", {"RUS"})]

    class Aircraft:
        dcs_unit_type = SimpleNamespace(iter_liveries=lambda: liveries)
        default_livery = None

    aircraft = Aircraft()
    faction = SimpleNamespace(
        country=SimpleNamespace(shortname="USA"), liveries_overrides={}
    )
    defaults = {
        "name": "VF-1",
        "aircraft": aircraft,
        "coalition": SimpleNamespace(faction=faction),
        "livery": None,
        "livery_set": [],
        "use_livery_set": False,
    }
    return SimpleNamespace(**{**defaults, **kwargs})


def test_livery_choices_follow_the_faction_and_the_squadron() -> None:
    squadron = _liveried_squadron(livery="ZULU")
    choices = livery_choices(squadron)
    assert [c.label for c in choices] == ["Alpha", "Zulu"]
    assert [c.selected for c in choices] == [False, True]

    set_squadron_livery(squadron, "alpha", False)
    assert squadron.livery == "alpha"
    with pytest.raises(CommandError, match="cannot use"):
        set_squadron_livery(squadron, "other", False)


def test_livery_set_comes_first_and_is_only_selected_when_used() -> None:
    squadron = _liveried_squadron(livery_set=["a"], use_livery_set=True, livery=None)
    choices = livery_choices(squadron)
    assert choices[0].use_livery_set and choices[0].selected

    squadron = _liveried_squadron(livery_set=["a"], livery="zulu")
    selected = [c.label for c in livery_choices(squadron) if c.selected]
    assert selected == ["Zulu"]


def test_liveries_route(game: Game) -> None:
    # No DCS install in the tests: whatever pydcs knows is a list, possibly empty.
    squadron = _blue(game)[0]
    status, body = _request("GET", f"/squadrons/{squadron.id}/liveries")
    assert status == 200
    assert isinstance(body, list)


# --- Transfers -----------------------------------------------------------------


def test_transfer_then_cancel_with_ferry_flights(game: Game) -> None:
    squadron, destination = _transferable(game)
    origin = squadron.location
    route = f"/squadrons/{squadron.id}/destination"

    status, options = _request("GET", f"/squadrons/{squadron.id}/destinations")
    assert status == 200
    assert str(destination.id) in [d["id"] for d in options["destinations"]]

    assert _request("PUT", route, {"destination_id": str(destination.id)}) == (
        204,
        None,
    )
    assert squadron.destination == destination
    ferries = [
        flight
        for package in game.blue.ato.packages
        for flight in package.flights
        if flight.squadron == squadron and flight.flight_type is FlightType.FERRY
    ]
    assert ferries
    sheet = _sheet(game, squadron)
    assert sheet["destination"] == destination.name
    assert f"Transfers to {destination.name}" in sheet["next_turn"]
    assert any(
        row.task == FlightType.FERRY.value and row.allocated
        for row in AirWingJs.for_coalition(game, Player.BLUE).inventory
    )

    assert _request("PUT", route, {"destination_id": None}) == (204, None)
    assert squadron.destination is None
    assert squadron.location == origin
    assert not any(
        flight.squadron == squadron and flight.flight_type is FlightType.FERRY
        for package in game.blue.ato.packages
        for flight in package.flights
    )


def test_transfer_publishes_what_changed(game: Game) -> None:
    squadron, destination = _transferable(game)
    origin = squadron.location
    now = game.conditions.start_time
    events = GameUpdateEvents()
    transfer_squadron(squadron, destination, now, events)
    try:
        assert events.new_flights
        assert {origin, destination} <= set(events.updated_control_points)
    finally:
        cancel = GameUpdateEvents()
        transfer_squadron(squadron, None, now, cancel)
    assert cancel.deleted_flights


def test_transfer_refused_without_room(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    squadron, destination = _transferable(game)
    squadron_owned = squadron.owned_aircraft
    assert squadron_owned > 0
    monkeypatch.setattr(
        "game.commands.squadrons.transfer_parking",
        lambda s, cp: SimpleNamespace(room=0, overflow=[]),
    )
    monkeypatch.setattr(
        type(destination), "unclaimed_parking", lambda self, parking_type: 1000
    )
    with pytest.raises(CommandError, match="additional slots required"):
        transfer_squadron(
            squadron, destination, game.conditions.start_time, GameUpdateEvents()
        )
    assert squadron.destination is None


def test_transfer_to_a_base_not_offered_is_refused(game: Game) -> None:
    squadron = _blue(game)[0]
    enemy_base = next(iter(game.red.air_wing.iter_squadrons())).location
    route = f"/squadrons/{squadron.id}/destination"
    status, body = _request("PUT", route, {"destination_id": str(enemy_base.id)})
    assert status == 409
    assert "cannot transfer" in body["detail"]
    status, _ = _request("PUT", route, {"destination_id": str(uuid4())})
    assert status == 404


def test_transfer_cheat_moves_at_once(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    squadron, destination = _transferable(game)
    origin = squadron.location
    monkeypatch.setattr(squadron.settings, "enable_transfer_cheat", True)
    now = game.conditions.start_time
    transfer_squadron(squadron, destination, now, GameUpdateEvents())
    try:
        assert squadron.location == destination
        assert squadron.destination is None
    finally:
        squadron.relocate_to(origin)


# --- Pilots --------------------------------------------------------------------


def test_player_flag_route(game: Game) -> None:
    squadron = next(s for s in _blue(game) if s.aircraft.flyable)
    pilot = next(p for p in squadron.current_roster if p.alive and not p.player)
    route = f"/squadrons/{squadron.id}/pilots/{pilot.id}"
    assert _request("PATCH", route, {"player": True}) == (204, None)
    assert pilot.player is True
    assert _request("PATCH", route, {"player": False}) == (204, None)
    assert pilot.player is False

    status, _ = _request("PATCH", f"/squadrons/{squadron.id}/pilots/{uuid4()}", {})
    assert status == 404
    status, _ = _request("PATCH", f"/squadrons/{uuid4()}/pilots/{pilot.id}", {})
    assert status == 404


def test_player_flag_refused_for_dead_and_prisoners(game: Game) -> None:
    squadron = _blue(game)[3]
    dead, prisoner = squadron.current_roster[:2]
    dead.kill()
    prisoner.go_down()
    prisoner.take_prisoner(uuid4())
    events = GameUpdateEvents()
    with pytest.raises(CommandError):
        set_pilot_player(squadron, dead, True, events)
    with pytest.raises(CommandError):
        set_pilot_player(squadron, prisoner, True, events)
    assert not prisoner.player


def test_player_flag_refused_for_an_aircraft_nobody_can_fly(
    game: Game,
) -> None:
    squadron = next(
        (s for s in game.blue.air_wing.iter_squadrons() if not s.aircraft.flyable),
        None,
    )
    if squadron is None:
        squadron = next(
            s for s in game.red.air_wing.iter_squadrons() if not s.aircraft.flyable
        )
    pilot = squadron.current_roster[0]
    with pytest.raises(CommandError, match="not flyable"):
        set_pilot_player(squadron, pilot, True, GameUpdateEvents())
    with pytest.raises(CommandError, match="not flyable"):
        create_player_pilot(squadron, "Me")


def test_leave_rules(game: Game, monkeypatch: pytest.MonkeyPatch) -> None:
    squadron = _blue(game)[4]
    pilot = squadron.current_roster[0]
    route = f"/squadrons/{squadron.id}/pilots/{pilot.id}"
    assert _request("PATCH", route, {"on_leave": True}) == (204, None)
    assert pilot.on_leave

    # The squadron filled up in the meantime: no room to come back.
    monkeypatch.setattr(squadron.settings, "enable_squadron_pilot_limits", True)
    monkeypatch.setattr(squadron.settings, "squadron_pilot_limit", 0)
    status, body = _request("PATCH", route, {"on_leave": False})
    assert (status, pilot.on_leave) == (409, True)
    assert "is full" in body["detail"]
    monkeypatch.undo()

    set_pilot_on_leave(squadron, pilot, False)
    assert pilot.status is PilotStatus.Active

    pilot.begin_recovery(2)
    with pytest.raises(CommandError, match="not on active duty"):
        set_pilot_on_leave(squadron, pilot, True)
    pilot.begin_recovery(0)


def test_rename_and_new_pilot_routes(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    squadron = next(s for s in _blue(game) if s.aircraft.flyable)
    monkeypatch.setattr(squadron.settings, "enable_squadron_pilot_limits", False)
    roster_size = len(squadron.current_roster)
    route = f"/squadrons/{squadron.id}/pilots"
    assert _request("POST", route, {"name": "  Maverick "}) == (204, None)
    assert len(squadron.current_roster) == roster_size + 1
    pilot = squadron.current_roster[-1]
    assert (pilot.name, pilot.player) == ("Maverick", True)

    assert _request("PATCH", f"{route}/{pilot.id}", {"name": "Goose"}) == (204, None)
    assert pilot.name == "Goose"
    status, body = _request("PATCH", f"{route}/{pilot.id}", {"name": "  "})
    assert (status, body["detail"]) == (409, "A pilot needs a name.")
    status, _ = _request("POST", route, {"name": ""})
    assert status == 409

    pilot.kill()
    with pytest.raises(CommandError, match="is dead"):
        rename_pilot(pilot, "Iceman")

    # Its career screen link.
    status, careers = _request("GET", "/careers/")
    assert status == 200
    assert str(pilot.id) in [career["pilot_id"] for career in careers]


def test_a_full_squadron_takes_no_new_pilot(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    squadron = next(s for s in _blue(game) if s.aircraft.flyable)
    monkeypatch.setattr(squadron.settings, "enable_squadron_pilot_limits", True)
    monkeypatch.setattr(squadron.settings, "squadron_pilot_limit", 0)
    assert "is full" in _sheet(game, squadron)["new_pilot_refusal"]
    status, body = _request("POST", f"/squadrons/{squadron.id}/pilots", {"name": "X"})
    assert status == 409
    assert "is full" in body["detail"]


# --- Buying (WEB-02.2) and repairs ---------------------------------------------


def test_buy_through_the_base_commands_shows_on_the_sheet(game: Game) -> None:
    squadron = next(s for s in _blue(game) if _sheet(game, s)["order"]["max_add"] > 0)
    budget = game.blue.budget
    route = f"/control-points/{squadron.location.id}/purchases/aircraft"
    order = {"orders": [{"squadron_id": str(squadron.id), "quantity": 1}]}
    assert _request("POST", route, order)[0] == 200
    sheet = _sheet(game, squadron)
    assert sheet["order"]["pending"] == 1
    assert "1 aircraft arriving" in sheet["next_turn"]
    assert game.blue.budget == budget - squadron.aircraft.price
    assert _request("DELETE", f"{route}/{squadron.id}")[0] == 200
    assert game.blue.budget == budget


def test_expedited_repair_is_offered_with_its_order_id(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    squadron = _blue(game)[0]
    assert _sheet(game, squadron)["repair"] is None
    squadron.send_to_maintenance(1, 2)
    monkeypatch.setattr(squadron.settings, "expedited_aircraft_repair", True)
    repair = _sheet(game, squadron)["repair"]
    assert repair["repair_id"] == f"squadron:{squadron.id}"
    assert repair["cost"] == squadron.expedited_repair_cost
    cp = squadron.location
    route = f"/control-points/{cp.id}/repairs/{repair['repair_id']}"
    assert _request("POST", route)[0] == 200
    assert squadron.aircraft_in_maintenance == 0
    assert _sheet(game, squadron)["repair"] is None


# --- Saves ---------------------------------------------------------------------


def test_pilots_of_old_saves_get_an_id() -> None:
    pilot = Pilot("Old timer")
    state = dict(pilot.__dict__)
    del state["id"]
    loaded = Pilot.__new__(Pilot)
    loaded.__setstate__(state)
    assert loaded.id is not None
    assert loaded == pilot  # The id is no part of a pilot's equality.
    assert pickle.loads(pickle.dumps(pilot)).id == pilot.id


def test_find_squadron_searches_both_coalitions(game: Game) -> None:
    for squadron in (
        next(iter(game.blue.air_wing.iter_squadrons())),
        next(iter(game.red.air_wing.iter_squadrons())),
    ):
        assert find_squadron(game, squadron.id) is squadron
    assert find_squadron(game, uuid4()) is None

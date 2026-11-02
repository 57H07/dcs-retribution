"""Issue #182: the Production & repairs screen, on a real generated game."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from game import Game
from game.commands.aircraftorders import AircraftOrder, order_aircraft
from game.commands.groundorders import GroundUnitOrder, order_ground_units
from game.commands.transfers import place_transfer
from game.config import RUNWAY_REPAIR_COST, RUNWAY_REPAIR_TURNS
from game.server import EventStream, GameContext
from game.sim import GameUpdateEvents
from game.squadrons import Squadron
from game.theater import ControlPoint
from game.theater.player import Player
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    NavalGroundObject,
)
from game.transfers import TransferOrder
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)
from tests.server.test_air_wing import _request
from tests.server.test_native_routes import _set_game


@pytest.fixture(scope="module")
def reference_game(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Game]:
    missing: Path = tmp_path_factory.mktemp("no_user_payloads")
    with repository_payloads_only(missing):
        yield generate_reference_game()


@pytest.fixture
def game(reference_game: Game, monkeypatch: pytest.MonkeyPatch) -> Iterator[Game]:
    sim = SimpleNamespace(
        current_time_in_sim_if_game_loaded=reference_game.conditions.start_time
    )
    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(game=reference_game, sim_controller=sim),
        raising=False,
    )
    monkeypatch.setattr(EventStream, "put_nowait", lambda events: None)
    budget = reference_game.blue.budget
    reference_game.blue.budget = 5000
    yield reference_game
    reference_game.blue.budget = budget


def _production() -> dict[str, Any]:
    status, body = _request("GET", "/production/")
    assert status == 200
    return body


def _groups(items: list[dict[str, Any]]) -> list[str]:
    return [item["group"] for item in items]


def _run(item: dict[str, Any]) -> tuple[int, Any]:
    return _request("POST", f"/production/items/{item['id']}/action")


def _squadron(game: Game) -> Squadron:
    return next(iter(game.blue.air_wing.iter_squadrons()))


def _base(game: Game) -> ControlPoint:
    return next(
        cp
        for cp in game.theater.control_points_for(Player.BLUE)
        if cp.runway_is_destroyable
    )


def test_no_campaign_has_no_production(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_game(monkeypatch, None)
    assert _request("GET", "/production/") == (200, None)


def test_an_aircraft_order_is_listed_and_cancelled_like_on_the_base(game: Game) -> None:
    squadron = _squadron(game)
    before = game.blue.budget
    order_aircraft(squadron.location, [AircraftOrder(squadron, 2)], GameUpdateEvents())
    paid = before - game.blue.budget
    assert paid == 2 * squadron.aircraft.price

    body = _production()
    item = next(i for i in body["in_progress"] if i["group"] == "aircraft-orders")
    assert item["label"].startswith(f"2 × {squadron.aircraft.display_name}")
    assert item["turns"] == 1
    assert item["base_id"] == str(squadron.location.id)
    assert item["action"]["cost"] == -paid
    assert body["next_end_turns"] == 1

    status, answer = _run(item)

    assert status == 200
    assert squadron.pending_deliveries == 0
    assert game.blue.budget == before
    assert "aircraft-orders" not in _groups(answer["in_progress"])


def test_a_ground_order_is_listed_and_cancelled(game: Game) -> None:
    base = _base(game)
    unit = next(iter(game.blue.faction.frontline_units))
    before = game.blue.budget
    order_ground_units(game, base, [GroundUnitOrder(unit, 3)], GameUpdateEvents())

    item = next(
        i for i in _production()["in_progress"] if i["group"] == "ground-orders"
    )
    assert item["label"] == f"3 × {unit.display_name}"

    assert _run(item)[0] == 200
    assert game.blue.budget == before
    assert base.ground_unit_orders.units.get(unit, 0) == 0


def test_a_damaged_runway_waits_then_runs_once_paid(game: Game) -> None:
    base = _base(game)
    base.runway_status.damage()
    try:
        before = game.blue.budget
        body = _production()
        item = next(
            i
            for i in body["to_handle"]
            if i["group"] == "damage" and i["base_id"] == str(base.id)
        )
        assert item["action"]["cost"] == RUNWAY_REPAIR_COST
        assert item["action"]["affordable"] is True

        status, answer = _run(item)

        assert status == 200
        assert game.blue.budget == before - RUNWAY_REPAIR_COST
        assert item["id"] not in [i["id"] for i in answer["to_handle"]]
        running = next(i for i in answer["in_progress"] if i["id"] == item["id"])
        assert running["turns"] == RUNWAY_REPAIR_TURNS
        assert running["action"] is None
        assert _run(running)[0] == 409
    finally:
        base.runway_status.repair()


def test_a_repair_too_expensive_is_refused_and_changes_nothing(game: Game) -> None:
    base = _base(game)
    base.runway_status.damage()
    game.blue.budget = 1
    try:
        item = next(
            i for i in _production()["to_handle"] if i["base_id"] == str(base.id)
        )
        assert item["action"]["affordable"] is False

        status, body = _run(item)

        assert status == 409
        assert "you have only" in body["detail"]
        assert game.blue.budget == 1
        assert base.runway_status.repair_turns_remaining is None
    finally:
        base.runway_status.repair()


def test_a_destroyed_building_is_listed_with_its_site(game: Game) -> None:
    site, unit = next(
        (tgo, tgo_unit)
        for cp in game.theater.control_points_for(Player.BLUE)
        for tgo in cp.ground_objects
        if isinstance(tgo, BuildingGroundObject) and tgo.repair_cost() > 0
        for tgo_unit in tgo.statics
    )
    unit.alive = False
    try:
        item = next(
            i for i in _production()["to_handle"] if i["tgo_id"] == str(site.id)
        )
        assert item["action"]["cost"] == site.repair_cost()
        assert item["group"] == "damage"
    finally:
        unit.alive = True


def test_aircraft_in_maintenance_show_their_turns(game: Game) -> None:
    squadron = next(s for s in game.blue.air_wing.iter_squadrons() if s.owned_aircraft)
    squadron.send_to_maintenance(1, 3)
    try:
        item = next(
            i for i in _production()["in_progress"] if i["group"] == "maintenance"
        )
        assert item["turns"] == 3
        assert item["base_id"] == str(squadron.location.id)
        assert item["action"] is None
    finally:
        squadron.new_maintenance_batches.clear()


def test_a_destroyed_site_unit_can_be_repaired_then_shows_its_turns(game: Game) -> None:
    site, unit = next(
        (tgo, tgo_unit)
        for cp in game.theater.control_points_for(Player.BLUE)
        for tgo in cp.ground_objects
        if not isinstance(tgo, BuildingGroundObject)
        for tgo_unit in tgo.units
        if tgo_unit.repairable and tgo_unit.unit_type is not None
    )
    assert unit.unit_type is not None
    price = unit.unit_type.price
    delay = game.settings.ground_unit_repair_turns
    game.settings.ground_unit_repair_turns = 3
    unit.alive = False
    before = game.blue.budget
    try:
        item = next(
            i for i in _production()["to_handle"] if i["tgo_id"] == str(site.id)
        )
        assert item["group"] == (
            "ships" if isinstance(site, NavalGroundObject) else "damage"
        )
        assert item["action"]["cost"] == price
        status, answer = _run(item)
        assert status == 200
        assert game.blue.budget == before - price
        running = next(i for i in answer["in_progress"] if i["tgo_id"] == str(site.id))
        assert running["group"] == "repairs"
        assert running["turns"] == 3
    finally:
        game.settings.ground_unit_repair_turns = delay
        unit.repair_turns_remaining = None
        unit.alive = True


def test_a_transfer_is_listed_and_cancelled(game: Game) -> None:
    origin = _base(game)
    destination = next(cp for cp in origin.connected_points if cp.captured.is_blue)
    unit = next(iter(game.blue.faction.frontline_units))
    origin.base.armor[unit] = origin.base.armor.get(unit, 0) + 3
    armor = origin.base.armor[unit]
    now = game.conditions.start_time
    place_transfer(game, TransferOrder(origin, destination, {unit: 3}), None, now)
    assert origin.base.armor.get(unit, 0) == armor - 3

    item = next(i for i in _production()["in_progress"] if i["group"] == "transfers")
    assert item["turns"] is None
    assert item["label"] == "3 ground units"
    assert item["action"]["cost"] == 0

    status, answer = _run(item)

    assert status == 200
    assert "transfers" not in _groups(answer["in_progress"])
    assert origin.base.armor.get(unit, 0) == armor
    origin.base.armor[unit] -= 3


def test_nothing_of_the_enemy_is_listed(game: Game) -> None:
    squadron = next(iter(game.red.air_wing.iter_squadrons()))
    squadron.pending_deliveries = 3
    enemy = next(iter(game.theater.control_points_for(Player.RED)))
    try:
        body = _production()
        items = body["in_progress"] + body["to_handle"]
        assert str(squadron.id) not in " ".join(i["id"] for i in items)
        assert str(enemy.id) not in [i["base_id"] for i in items]
    finally:
        squadron.pending_deliveries = 0


def test_an_unknown_item_is_a_404(game: Game) -> None:
    assert _request("POST", "/production/items/nope/action")[0] == 404


def test_the_map_opens_on_the_campaign(game: Game) -> None:
    bounds = game.theater.campaign_bounds()
    assert bounds is not None
    south_west, north_east = bounds
    center = game.theater.campaign_center()
    assert south_west.lat <= center.lat <= north_east.lat
    assert south_west.lng <= center.lng <= north_east.lng
    status, body = _request("GET", "/game/")
    assert status == 200
    assert body["map_center"]["lat"] == pytest.approx(center.lat)
    assert body["map_center"]["lng"] == pytest.approx(center.lng)

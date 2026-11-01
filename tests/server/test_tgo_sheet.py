"""WEB-08.3: ground object sheet, repairs, purchases and unit info on a real game."""

from __future__ import annotations

import asyncio
import json
import pickle
import random
from collections.abc import Iterator, MutableMapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from urllib.parse import urlencode

import pytest

from game import Game, persistency
from game.commands import (
    CommandError,
    SlotChoice,
    TgoPurchase,
    buy_ground_object_group,
    can_buy_or_sell,
    disband_ground_object,
    layout_slots,
    purchasable_force_groups,
    quote_purchase,
    repair_ground_unit,
    resale_value,
    resolve_purchase,
    rotate_ground_object,
    set_hidden_on_mfd,
    unit_status,
)
from game.data.groups import GroupRole
from game.dcs.aircrafttype import AircraftType
from game.dcs.groundunittype import GroundUnitType
from game.dcs.shipunittype import ShipUnitType
from game.dcs.unitbanners import MISSING_BANNER_PATH, existing_banner_for
from game.server import GameContext
from game.server.app import app
from game.server.dependencies import QtCallbacks, QtContext
from game.server.security import ApiKeyManager
from game.server.unitinfo.routes import UnitInfoJs
from game.sim import GameUpdateEvents
from game.theater import TheaterGroundObject
from game.theater.grounddamage import accelerated_repair_cost
from game.theater.player import Player
from game.theater.repairs import building_repair_cost
from game.theater.theatergroundobject import BuildingGroundObject, SamGroundObject
from game.theater.theatergroup import TheaterUnit
from game.utils import Heading
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)


@pytest.fixture(scope="module")
def saved_reference_game(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    saved_games = tmp_path_factory.mktemp("saved_games")
    random_state = random.getstate()
    previous_folder = persistency._dcs_saved_game_folder
    persistency._dcs_saved_game_folder = str(saved_games)
    try:
        with repository_payloads_only(Path(saved_games) / "no_user_payloads"):
            game = generate_reference_game()
    finally:
        persistency._dcs_saved_game_folder = previous_folder
        random.setstate(random_state)
    # Like persistency.save_game: the landmap is static data, not saved.
    landmap = game.theater.landmap
    game.theater.landmap = None
    saved = pickle.dumps(game)
    game.theater.landmap = landmap
    return saved


@pytest.fixture
def game(
    saved_reference_game: bytes, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Game]:
    """A fresh copy of the reference game, past turn 0 with money to spend."""
    copy: Game = pickle.loads(saved_reference_game)
    copy.turn = 1
    copy.blue.budget = 10_000
    copy.red.budget = 10_000
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=copy), raising=False
    )
    yield copy


def _site(
    game: Game, player: Player, accept: Callable[[TheaterGroundObject], bool]
) -> TheaterGroundObject:
    for cp in game.theater.controlpoints:
        if cp.captured is not player:
            continue
        for tgo in cp.ground_objects:
            if accept(tgo) and tgo.unit_count > 0:
                return tgo
    raise AssertionError(f"The reference game has no such site for {player}")


def _sam(game: Game, player: Player = Player.BLUE) -> SamGroundObject:
    tgo = _site(game, player, lambda t: isinstance(t, SamGroundObject))
    assert isinstance(tgo, SamGroundObject)
    return tgo


def _building(game: Game, player: Player = Player.BLUE) -> BuildingGroundObject:
    tgo = _site(
        game,
        player,
        lambda t: isinstance(t, BuildingGroundObject)
        and building_repair_cost(t.category, game.settings) > 0,
    )
    assert isinstance(tgo, BuildingGroundObject)
    return tgo


def _priced_unit(tgo: TheaterGroundObject) -> TheaterUnit:
    return next(u for u in tgo.units if u.unit_type and u.unit_type.price > 0)


def _kill(unit: TheaterUnit) -> None:
    unit.kill(GameUpdateEvents())


def _whole_layout_purchase(
    tgo: TheaterGroundObject, amount: int = 1
) -> tuple[str, str, list[SlotChoice]]:
    """The first force group and layout of a site, with `amount` of each type."""
    force_group = purchasable_force_groups(tgo)[0]
    layout = force_group.layouts[0]
    return (
        force_group.name,
        layout.name,
        [
            SlotChoice(slot.id, slot.options[0].id, min(amount, slot.max_amount))
            for slot in layout_slots(force_group, layout)
        ],
    )


def _purchase(tgo: TheaterGroundObject) -> TgoPurchase:
    return resolve_purchase(tgo, *_whole_layout_purchase(tgo))


def _request(
    method: str,
    path: str,
    body: Any = None,
    query: dict[str, str] | None = None,
) -> tuple[int, Any]:
    """Send one request through the whole ASGI app (routing, lock, errors, JSON)."""
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
        "query_string": urlencode(query or {}).encode(),
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
    content = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    try:
        return status, json.loads(content) if content else None
    except ValueError:
        return status, content


class TestRepairs:
    def test_a_destroyed_unit_costs_its_price(self, game: Game) -> None:
        tgo = _sam(game)
        unit = _priced_unit(tgo)
        assert unit.unit_type is not None
        price = unit.unit_type.price
        _kill(unit)
        status = unit_status(game, unit)
        assert (status.state, status.repair_cost) == ("destroyed", price)

        status = repair_ground_unit(game, tgo, unit.id, GameUpdateEvents())

        assert game.blue.budget == 10_000 - price
        # Ground unit repairs are instant by default.
        assert unit.alive and status.state == "operational"

    def test_a_delay_shows_as_repairing_and_cannot_be_paid_twice(
        self, game: Game
    ) -> None:
        game.settings.ground_unit_repair_turns = 3
        tgo = _sam(game)
        unit = _priced_unit(tgo)
        _kill(unit)
        assert unit_status(game, unit).repair_turns == 3

        status = repair_ground_unit(game, tgo, unit.id, GameUpdateEvents())

        assert (status.state, status.turns_remaining) == ("repairing", 3)
        assert not unit.alive
        with pytest.raises(CommandError):
            repair_ground_unit(game, tgo, unit.id, GameUpdateEvents())

    def test_not_enough_budget_changes_nothing(self, game: Game) -> None:
        tgo = _sam(game)
        unit = _priced_unit(tgo)
        _kill(unit)
        game.blue.budget = 0
        with pytest.raises(CommandError, match="costs"):
            repair_ground_unit(game, tgo, unit.id, GameUpdateEvents())
        assert not unit.alive and game.blue.budget == 0

    def test_an_enemy_unit_cannot_be_repaired(self, game: Game) -> None:
        tgo = _sam(game, Player.RED)
        unit = _priced_unit(tgo)
        _kill(unit)
        assert unit_status(game, unit).repair_cost is None
        with pytest.raises(CommandError):
            repair_ground_unit(game, tgo, unit.id, GameUpdateEvents())

    def test_an_inoperative_unit_needs_the_setting(self, game: Game) -> None:
        tgo = _sam(game)
        unit = _priced_unit(tgo)
        unit.make_inoperative(2, game.turn, GameUpdateEvents())
        price = accelerated_repair_cost(unit)

        game.settings.persistent_damage_paid_ground_repair = False
        status = unit_status(game, unit)
        assert (status.state, status.repair_cost) == ("inoperative", None)
        assert status.turns_remaining == 3

        game.settings.persistent_damage_paid_ground_repair = True
        assert unit_status(game, unit).repair_cost == price
        repair_ground_unit(game, tgo, unit.id, GameUpdateEvents())
        assert unit.operational and game.blue.budget == 10_000 - price

    def test_a_building_costs_the_site_repair_cost(self, game: Game) -> None:
        tgo = _building(game)
        building = next(iter(tgo.statics))
        _kill(building)
        cost = tgo.repair_cost()
        status = unit_status(game, building)
        assert status.repair_cost == cost and status.repair_turns > 0

        status = repair_ground_unit(game, tgo, building.id, GameUpdateEvents())

        assert status.state == "repairing"
        assert game.blue.budget == 10_000 - cost


class TestPurchases:
    def test_only_a_player_site_unless_the_setting_allows(self, game: Game) -> None:
        enemy = _sam(game, Player.RED)
        assert can_buy_or_sell(game, _sam(game))
        assert not can_buy_or_sell(game, enemy)
        game.settings.enable_enemy_buy_sell = True
        assert can_buy_or_sell(game, enemy)
        assert not can_buy_or_sell(game, _building(game))

    def test_the_old_group_is_credited(self, game: Game) -> None:
        tgo = _sam(game)
        credit = resale_value(tgo)
        assert credit == tgo.value
        purchase = _purchase(tgo)
        quote = quote_purchase(game, tgo, purchase)
        assert (quote.price, quote.credit) == (purchase.price, credit)
        assert quote.cost == purchase.price - credit

        buy_ground_object_group(game, tgo, purchase, GameUpdateEvents())

        assert game.blue.budget == 10_000 - quote.cost
        assert tgo.value == purchase.price
        assert tgo.unit_count == sum(line.amount for line in purchase.lines)

    def test_units_under_repair_are_credited(self, game: Game) -> None:
        game.settings.ground_unit_repair_turns = 3
        tgo = _sam(game)
        before = resale_value(tgo)
        unit = _priced_unit(tgo)
        assert unit.unit_type is not None
        _kill(unit)
        assert resale_value(tgo) == before - unit.unit_type.price
        unit.repair_turns_remaining = 2
        assert resale_value(tgo) == before

    def test_too_expensive_changes_nothing(self, game: Game) -> None:
        tgo = _sam(game)
        purchase = _purchase(tgo)
        game.blue.budget = purchase.price - resale_value(tgo) - 1
        budget = game.blue.budget
        groups = list(tgo.groups)
        assert not quote_purchase(game, tgo, purchase).affordable
        with pytest.raises(CommandError, match="costs"):
            buy_ground_object_group(game, tgo, purchase, GameUpdateEvents())
        assert tgo.groups == groups and game.blue.budget == budget

    def test_free_on_turn_zero(self, game: Game) -> None:
        game.turn = 0
        game.blue.budget = 0
        tgo = _sam(game)
        purchase = _purchase(tgo)
        quote = quote_purchase(game, tgo, purchase)
        assert quote.affordable and quote.cost == 0
        buy_ground_object_group(game, tgo, purchase, GameUpdateEvents())
        assert game.blue.budget == 0

    def test_the_new_group_heads_to_the_conflict(self, game: Game) -> None:
        tgo = _sam(game)
        expected = game.theater.heading_to_conflict_from(tgo.position) or tgo.heading
        tgo.heading = expected + Heading.from_degrees(90)
        buy_ground_object_group(game, tgo, _purchase(tgo), GameUpdateEvents())
        assert tgo.heading.degrees == expected.degrees

    def test_the_layout_limits_are_enforced(self, game: Game) -> None:
        tgo = _sam(game)
        force, layout, choices = _whole_layout_purchase(tgo)
        first = choices[0]
        slot = layout_slots(
            purchasable_force_groups(tgo)[0],
            purchasable_force_groups(tgo)[0].layouts[0],
        )[0]

        def with_first(choice: SlotChoice) -> list[SlotChoice]:
            return [choice, *choices[1:]]

        too_many = SlotChoice(first.slot, first.unit_type, slot.max_amount + 1)
        for refused in (
            with_first(too_many),
            with_first(SlotChoice(first.slot, first.unit_type, 0)),
            with_first(SlotChoice(first.slot, "not-a-unit", 1)),
            [*choices, SlotChoice(999, first.unit_type, 1)],
        ):
            with pytest.raises(CommandError):
                resolve_purchase(tgo, force, layout, refused)
        with pytest.raises(CommandError):
            resolve_purchase(tgo, "No such group", layout, choices)
        with pytest.raises(CommandError):
            resolve_purchase(tgo, force, "No such layout", choices)

    def test_a_required_slot_cannot_be_left_out(self, game: Game) -> None:
        tgo = _sam(game)
        for force_group in purchasable_force_groups(tgo):
            for layout in force_group.layouts:
                slots = layout_slots(force_group, layout)
                required = [slot for slot in slots if not slot.optional]
                if not required:
                    continue
                choices = [
                    SlotChoice(slot.id, slot.options[0].id, 1)
                    for slot in slots
                    if slot is not required[0]
                ]
                with pytest.raises(CommandError, match="required"):
                    resolve_purchase(tgo, force_group.name, layout.name, choices)
                return
        raise AssertionError("No layout with a required slot")

    def test_force_groups_fit_the_site(self, game: Game) -> None:
        tgo = _site(game, Player.BLUE, lambda t: isinstance(t, SamGroundObject))
        sam_groups = purchasable_force_groups(tgo)
        assert sam_groups
        assert all(
            set(group.tasks) & set(GroupRole.AIR_DEFENSE.tasks) for group in sam_groups
        )
        assert purchasable_force_groups(_building(game)) == []

    def test_disband_credits_the_group(self, game: Game) -> None:
        tgo = _sam(game)
        value = resale_value(tgo)
        assert disband_ground_object(game, tgo, GameUpdateEvents()) == value
        assert game.blue.budget == 10_000 + value
        assert tgo.groups == []
        with pytest.raises(CommandError):
            disband_ground_object(game, tgo, GameUpdateEvents())

    def test_only_the_enemy_replans(
        self, game: Game, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tgo = _sam(game)
        calls: list[dict[str, bool]] = []
        monkeypatch.setattr(
            game,
            "initialize_turn",
            lambda events, for_red, for_blue: calls.append(
                {"for_red": for_red, "for_blue": for_blue}
            ),
        )
        disband = _sam(game)
        repair_unit = _priced_unit(tgo)
        _kill(repair_unit)
        repair_ground_unit(game, tgo, repair_unit.id, GameUpdateEvents())
        assert calls == []

        package = SimpleNamespace(target=disband)
        monkeypatch.setattr(game.red.ato, "packages", [package])
        disband_ground_object(game, disband, GameUpdateEvents())
        assert calls == [{"for_red": True, "for_blue": False}]


class TestHeadingAndHiding:
    def test_only_a_player_site_turns(self, game: Game) -> None:
        tgo = _sam(game)
        rotate_ground_object(tgo, Heading.from_degrees(45), GameUpdateEvents())
        assert tgo.heading.degrees == 45
        with pytest.raises(CommandError):
            rotate_ground_object(
                _sam(game, Player.RED), Heading.from_degrees(45), GameUpdateEvents()
            )
        with pytest.raises(CommandError):
            rotate_ground_object(
                _building(game), Heading.from_degrees(45), GameUpdateEvents()
            )

    def test_only_an_enemy_air_defense_hides(self, game: Game) -> None:
        enemy = _sam(game, Player.RED)
        set_hidden_on_mfd(enemy, True, GameUpdateEvents())
        assert enemy.hide_on_mfd
        with pytest.raises(CommandError):
            set_hidden_on_mfd(_sam(game), True, GameUpdateEvents())


class TestRoutes:
    def test_sheet_of_a_player_site(self, game: Game) -> None:
        tgo = _sam(game)
        unit = _priced_unit(tgo)
        assert unit.unit_type is not None
        _kill(unit)
        status, body = _request("GET", f"/tgos/{tgo.id}/sheet")
        assert status == 200
        assert body["summary"]["id"] == str(tgo.id)
        assert body["is_building_site"] is False
        assert body["budget"] == 10_000
        assert body["can_buy"] is True
        assert body["disband_value"] == resale_value(tgo)
        assert body["hidden_on_mfd"] is None
        assert body["heading"]["can_adjust"] is True
        row = next(u for u in body["units"] if u["id"] == unit.id)
        assert row == {
            "id": unit.id,
            "name": unit.unit_type.display_name,
            "info_kind": "ground",
            "info_name": unit.unit_type.variant_id,
            "state": "destroyed",
            "turns_remaining": 0,
            "repair_cost": unit.unit_type.price,
            "repair_turns": 0,
            "repair_affordable": True,
        }

    def test_sheet_of_an_enemy_site(self, game: Game) -> None:
        tgo = _sam(game, Player.RED)
        status, body = _request("GET", f"/tgos/{tgo.id}/sheet")
        assert status == 200
        assert body["can_buy"] is False
        assert body["disband_value"] == 0
        assert body["hidden_on_mfd"] is False
        assert body["heading"]["can_adjust"] is False

    def test_sheet_of_a_building_site(self, game: Game) -> None:
        tgo = _building(game)
        status, body = _request("GET", f"/tgos/{tgo.id}/sheet")
        assert status == 200
        assert body["is_building_site"] is True
        assert body["heading"] is None
        assert body["can_buy"] is False
        statics = list(tgo.statics)
        per_building = body["income"]["per_building"]
        assert per_building > 0
        assert body["income"]["available"] == per_building * len(statics)
        assert body["income"]["receiving"] == per_building * len(statics)
        assert len(body["units"]) == len(statics)

    def test_unknown_site_and_unit(self, game: Game) -> None:
        missing = "00000000-0000-0000-0000-000000000000"
        assert _request("GET", f"/tgos/{missing}/sheet")[0] == 404
        tgo = _sam(game)
        status, body = _request("POST", f"/tgos/{tgo.id}/units/0/repair")
        assert status == 404
        assert "has no unit" in body["detail"]

    def test_repair_route(self, game: Game) -> None:
        tgo = _sam(game)
        unit = _priced_unit(tgo)
        assert unit.unit_type is not None
        _kill(unit)
        status, body = _request("POST", f"/tgos/{tgo.id}/units/{unit.id}/repair")
        assert status == 200
        assert body["budget"] == 10_000 - unit.unit_type.price
        assert next(u for u in body["units"] if u["id"] == unit.id)["state"] == (
            "operational"
        )
        status, body = _request("POST", f"/tgos/{tgo.id}/units/{unit.id}/repair")
        assert status == 409
        assert body["detail"] == "This unit cannot be repaired now."

    def test_heading_and_hidden_routes(self, game: Game) -> None:
        tgo = _sam(game)
        status, body = _request("PUT", f"/tgos/{tgo.id}/heading", {"degrees": 90})
        assert status == 200
        assert body["heading"]["degrees"] == 90
        enemy = _sam(game, Player.RED)
        assert _request("PUT", f"/tgos/{enemy.id}/heading", {"degrees": 90})[0] == 409

        status, body = _request(
            "PUT", f"/tgos/{enemy.id}/hidden-on-mfd", {"hidden": True}
        )
        assert status == 200
        assert body["hidden_on_mfd"] is True
        assert (
            _request("PUT", f"/tgos/{tgo.id}/hidden-on-mfd", {"hidden": True})[0] == 409
        )

    def test_purchase_routes(self, game: Game) -> None:
        tgo = _sam(game)
        status, options = _request("GET", f"/tgos/{tgo.id}/purchase-options")
        assert status == 200
        force_group = options["force_groups"][0]
        layout = force_group["layouts"][0]
        slot = layout["slots"][0]
        assert 1 <= slot["amount"] <= slot["max_amount"]
        assert slot["options"][0]["price"] >= 0

        body = {
            "force_group": force_group["name"],
            "layout": layout["name"],
            "choices": [
                {"slot": s["id"], "unit_type": s["options"][0]["id"], "amount": 1}
                for s in layout["slots"]
            ],
        }
        status, quote = _request("POST", f"/tgos/{tgo.id}/purchase/quote", body)
        assert status == 200
        assert quote["credit"] == resale_value(tgo)
        assert quote["cost"] == quote["price"] - quote["credit"]
        assert game.blue.budget == 10_000  # A quote changes nothing.

        status, sheet = _request("POST", f"/tgos/{tgo.id}/purchase", body)
        assert status == 200
        assert sheet["budget"] == 10_000 - quote["cost"]

        status, refused = _request(
            "POST", f"/tgos/{tgo.id}/purchase", {**body, "layout": "No such layout"}
        )
        assert status == 409
        assert "no layout" in refused["detail"]

    def test_purchase_refused_on_enemy_site(self, game: Game) -> None:
        tgo = _sam(game, Player.RED)
        force, layout, choices = _whole_layout_purchase(tgo)
        status, body = _request(
            "POST",
            f"/tgos/{tgo.id}/purchase",
            {
                "force_group": force,
                "layout": layout,
                "choices": [
                    {"slot": c.slot, "unit_type": c.unit_type, "amount": c.amount}
                    for c in choices
                ],
            },
        )
        assert status == 409
        assert "cannot buy" in body["detail"]

    def test_disband_route(self, game: Game) -> None:
        tgo = _sam(game)
        value = resale_value(tgo)
        status, body = _request("DELETE", f"/tgos/{tgo.id}/group")
        assert status == 200
        assert body["budget"] == 10_000 + value
        assert body["units"] == []
        assert _request("DELETE", f"/tgos/{tgo.id}/group")[0] == 409

    def test_the_qt_dialog_route_is_gone_in_web_mode(
        self, game: Game, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def ignore(*_: Any) -> None:
            pass

        tgo = _sam(game)
        monkeypatch.setattr(
            QtContext, "_callbacks", QtCallbacks(ignore, None, ignore, ignore)
        )
        assert _request("POST", f"/qt/info/tgo/{tgo.id}")[0] == 503

        opened: list[Any] = []
        monkeypatch.setattr(
            QtContext, "_callbacks", QtCallbacks(ignore, opened.append, ignore, ignore)
        )
        assert _request("POST", f"/qt/info/tgo/{tgo.id}")[0] == 200
        assert opened == [tgo]


class TestUnitInfo:
    def test_a_ground_unit(self, game: Game) -> None:
        unit = _priced_unit(_sam(game))
        assert unit.unit_type is not None
        status, body = _request(
            "GET",
            "/unit-info",
            query={"kind": "ground", "name": unit.unit_type.variant_id},
        )
        assert status == 200
        assert body["display_name"] == unit.unit_type.display_name
        assert body["role"] == unit.unit_type.role
        assert body["tasks"] == []
        assert "<a" not in body["description"]

    def test_an_aircraft_lists_its_tasks(self, game: Game) -> None:
        squadron = next(iter(game.blue.air_wing.iter_squadrons()))
        status, body = _request(
            "GET",
            "/unit-info",
            query={"kind": "aircraft", "name": squadron.aircraft.variant_id},
        )
        assert status == 200
        assert body["kind"] == "aircraft"
        assert body["tasks"]

    def test_every_unit_type_has_a_sheet(self) -> None:
        for dcs_type in GroundUnitType.each_dcs_type():
            for ground in GroundUnitType.for_dcs_type(dcs_type):
                UnitInfoJs.for_unit_type("ground", ground)
        for flying_type in AircraftType.each_dcs_type():
            for aircraft in AircraftType.for_dcs_type(flying_type):
                UnitInfoJs.for_unit_type("aircraft", aircraft)
        for ship_type in ShipUnitType.each_dcs_type():
            for ship in ShipUnitType.for_dcs_type(ship_type):
                UnitInfoJs.for_unit_type("ship", ship)

    def test_an_unknown_unit(self) -> None:
        status, _ = _request(
            "GET", "/unit-info", query={"kind": "ground", "name": "No such unit"}
        )
        assert status == 404

    def test_the_banner_falls_back_on_the_generic_one(self) -> None:
        assert existing_banner_for(_named_ground_type_without_banner()) == (
            MISSING_BANNER_PATH
        )

    def test_the_banner_route_answers_an_image(self, game: Game) -> None:
        unit = _priced_unit(_sam(game))
        assert unit.unit_type is not None
        status, content = _request(
            "GET",
            "/unit-info/banner",
            query={"kind": "ground", "name": unit.unit_type.variant_id},
        )
        assert status == 200
        assert isinstance(content, bytes) and content


def _named_ground_type_without_banner() -> GroundUnitType:
    for dcs_type in GroundUnitType.each_dcs_type():
        for unit_type in GroundUnitType.for_dcs_type(dcs_type):
            path = Path("resources/ui/units/vehicles/banners") / f"{dcs_type.id}.jpg"
            if not path.exists() and dcs_type.id not in (
                "(IDF Mods Project) BM-21 Grad 122mm",
                "(IDF Mods Project) Urgan BM-27 220mm",
                "(IDF Mods Project) 9A52 Smerch CM 300mm",
            ):
                return unit_type
    raise AssertionError("Every ground unit has a banner")

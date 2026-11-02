"""WEB-02.3: ground units, front lines, convoys, transfers and base actions.

Against a real `Game`: the reference campaign of `tests/flightplans/` (Israel at Ramat
David and Golan South, Syria at Golan North, Marj Ruhayyil and Damascus).
"""

from __future__ import annotations

import pickle
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from game import Game
from game.commands import CommandError
from game.commands.baseradios import BaseRadios, base_radios, set_base_radios
from game.commands.cheats import (
    cheat_capture,
    cheat_move_front_line,
    cheat_runway_state,
)
from game.commands.frontline import front_line_stance, set_front_line_stance
from game.commands.groundorders import (
    GroundUnitOrder,
    change_ground_unit_order,
    find_ground_unit_type,
    ground_unit_types,
    max_ground_units_to_add,
    order_ground_units,
)
from game.commands.transfers import (
    attackable_transport,
    can_plan_transport_mission,
    can_transfer_units,
    place_transfer,
    transfer_destinations,
    transferable_units,
)
from game.dcs.groundunittype import GroundUnitType
from game.game import TurnState
from game.ground_forces.combat_stance import CombatStance
from game.radio.ICLSContainer import ICLSContainer
from game.radio.Link4Container import Link4Container
from game.radio.TacanContainer import TacanContainer
from game.radio.tacan import TacanBand, TacanChannel
from game.server import GameContext
from game.server.controlpoints.groundforces import (
    BaseActionsJs,
    DepartingConvoyJs,
    GroundForcesJs,
    TransferOptionsJs,
)
from game.server.eventstream import EventStream
from game.sim import GameUpdateEvents
from game.theater import ControlPoint
from game.theater.player import Player
from game.transfers import Convoy, TransferOrder
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)
from .test_aircraft_orders import _request

NOW = datetime(2010, 6, 1, 8)


@pytest.fixture(scope="module")
def saved_game(tmp_path_factory: pytest.TempPathFactory) -> Iterator[bytes]:
    no_payloads = Path(tmp_path_factory.mktemp("no_user_payloads"))
    with repository_payloads_only(no_payloads):
        yield pickle.dumps(generate_reference_game())


@pytest.fixture
def game(saved_game: bytes) -> Game:
    """A fresh copy of the reference game, as loaded from a save."""
    loaded: Game = pickle.loads(saved_game)
    loaded.on_load()
    return loaded


def _cp(game: Game, name: str) -> ControlPoint:
    return next(cp for cp in game.theater.controlpoints if cp.name == name)


def _tank(cp: ControlPoint) -> GroundUnitType:
    """An orderable unit that costs something."""
    return next(u for u in ground_unit_types(cp) if u.price > 0)


def _stock(cp: ControlPoint, count: int = 5) -> GroundUnitType:
    unit_type = _tank(cp)
    cp.base.commission_units({unit_type: count})
    return unit_type


def _no_factory_after_turn_0(game: Game, monkeypatch: pytest.MonkeyPatch) -> None:
    game.turn = 3
    monkeypatch.setattr(ControlPoint, "has_factory", property(lambda self: False))


# --- orders -------------------------------------------------------------------


def test_order_pays_now_and_delivers_next_turn(game: Game) -> None:
    cp = _cp(game, "Ramat David")
    unit = _tank(cp)
    budget = game.blue.budget
    events = GameUpdateEvents()

    order_ground_units(game, cp, [GroundUnitOrder(unit, 3)], events)

    assert game.blue.budget == budget - 3 * unit.price
    assert cp.ground_unit_orders.pending_orders(unit) == 3
    assert cp.base.total_units_of_type(unit) == 0
    assert events.budget_updated
    assert cp in events.updated_control_points

    game.pass_turn(no_action=True)
    assert cp.ground_unit_orders.pending_orders(unit) == 0
    assert cp.base.total_units_of_type(unit) == 3


def test_cancelling_refunds_and_ground_units_are_never_sold(game: Game) -> None:
    cp = _cp(game, "Ramat David")
    unit = _tank(cp)
    budget = game.blue.budget
    events = GameUpdateEvents()
    order_ground_units(game, cp, [GroundUnitOrder(unit, 2)], events)

    order_ground_units(game, cp, [GroundUnitOrder(unit, -2)], events)
    assert game.blue.budget == budget
    assert cp.ground_unit_orders.pending_orders(unit) == 0

    cp.base.commission_units({unit: 4})
    with pytest.raises(CommandError, match="cannot be sold"):
        order_ground_units(game, cp, [GroundUnitOrder(unit, -1)], events)
    assert cp.base.total_units_of_type(unit) == 4
    assert game.blue.budget == budget


def test_refused_order_changes_nothing(game: Game) -> None:
    cp = _cp(game, "Ramat David")
    first, second = [u for u in ground_unit_types(cp) if u.price > 0][:2]
    game.blue.budget = first.price + second.price - 1
    budget = game.blue.budget
    events = GameUpdateEvents()

    with pytest.raises(CommandError, match="you have only"):
        order_ground_units(
            game, cp, [GroundUnitOrder(first, 1), GroundUnitOrder(second, 1)], events
        )

    assert game.blue.budget == budget
    assert cp.ground_unit_orders.pending_orders(first) == 0
    assert cp.ground_unit_orders.pending_orders(second) == 0
    assert not events.budget_updated


def test_cancellations_free_the_money_of_the_same_order(game: Game) -> None:
    cp = _cp(game, "Ramat David")
    unit = max(ground_unit_types(cp), key=lambda u: u.price)
    game.blue.budget = unit.price
    events = GameUpdateEvents()
    order_ground_units(game, cp, [GroundUnitOrder(unit, 1)], events)
    assert game.blue.budget == 0

    other = _tank(cp)
    order_ground_units(
        game, cp, [GroundUnitOrder(other, 1), GroundUnitOrder(unit, -1)], events
    )
    assert cp.ground_unit_orders.pending_orders(other) == 1
    assert cp.ground_unit_orders.pending_orders(unit) == 0


def test_no_factory_refuses_orders_after_turn_0(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    cp = _cp(game, "Ramat David")
    unit = _tank(cp)
    assert max_ground_units_to_add(game, cp, unit) > 0

    _no_factory_after_turn_0(game, monkeypatch)

    assert max_ground_units_to_add(game, cp, unit) == 0
    assert GroundForcesJs.for_control_point(game, cp).recruitment_refusal is not None
    with pytest.raises(CommandError, match="factory"):
        order_ground_units(game, cp, [GroundUnitOrder(unit, 1)], GameUpdateEvents())


def test_max_to_add_follows_the_budget(game: Game) -> None:
    cp = _cp(game, "Ramat David")
    unit = _tank(cp)
    game.blue.budget = unit.price * 2.5
    assert max_ground_units_to_add(game, cp, unit) == 2


def test_enemy_base_cannot_order(game: Game) -> None:
    cp = _cp(game, "Damascus")
    unit = _tank(cp)
    with pytest.raises(CommandError, match="not your base"):
        order_ground_units(game, cp, [GroundUnitOrder(unit, 1)], GameUpdateEvents())
    assert GroundForcesJs.for_control_point(game, cp).units == []


def test_empty_order_and_unknown_unit(game: Game) -> None:
    cp = _cp(game, "Ramat David")
    with pytest.raises(CommandError, match="empty"):
        order_ground_units(game, cp, [], GameUpdateEvents())
    with pytest.raises(CommandError, match="not a ground unit"):
        find_ground_unit_type(cp, "T-90 of another faction")


def test_qt_steps_keep_what_was_done_before_a_refusal(game: Game) -> None:
    cp = _cp(game, "Ramat David")
    unit = _tank(cp)
    game.blue.budget = unit.price * 2
    events = GameUpdateEvents()

    with pytest.raises(CommandError):
        change_ground_unit_order(game, cp, unit, 5, events)

    assert cp.ground_unit_orders.pending_orders(unit) == 2
    assert events.budget_updated


def test_ground_forces_read_model(game: Game) -> None:
    cp = _cp(game, "Golan South")
    unit = _stock(cp, 4)
    order_ground_units(game, cp, [GroundUnitOrder(unit, 2)], GameUpdateEvents())

    forces = GroundForcesJs.for_control_point(game, cp)

    row = next(r for r in forces.units if r.unit_id == unit.variant_id)
    assert (row.owned, row.pending, row.unit_cost) == (4, 2, unit.price)
    assert (forces.present, forces.ordered, forces.transferring) == (4, 2, 0)
    assert [line.enemy for line in forces.front_lines] == ["Golan North"]
    assert forces.front_lines[0].stance in forces.stance_options
    assert forces.deployable_limit == cp.frontline_unit_count_limit
    assert forces.reserve == max(4 - cp.frontline_unit_count_limit, 0)


# --- front lines --------------------------------------------------------------


def test_set_stance_on_a_real_front_line(game: Game) -> None:
    cp, enemy = _cp(game, "Golan South"), _cp(game, "Golan North")
    events = GameUpdateEvents()

    set_front_line_stance(cp, enemy, "BREAKTHROUGH", events)

    assert cp.stances[enemy.id] is CombatStance.BREAKTHROUGH
    assert front_line_stance(cp, enemy) is CombatStance.BREAKTHROUGH
    assert cp in events.updated_control_points


def test_stance_refusals(game: Game) -> None:
    cp, enemy = _cp(game, "Golan South"), _cp(game, "Golan North")
    with pytest.raises(CommandError, match="not a front line stance"):
        set_front_line_stance(cp, enemy, "PANIC", GameUpdateEvents())
    with pytest.raises(CommandError, match="no front line"):
        set_front_line_stance(cp, _cp(game, "Damascus"), "RETREAT", GameUpdateEvents())
    with pytest.raises(CommandError, match="no front line"):
        # The enemy side of the same front line.
        set_front_line_stance(enemy, cp, "RETREAT", GameUpdateEvents())


# --- transfers ----------------------------------------------------------------


def test_convoy_transfer_takes_the_units_out_of_the_origin(game: Game) -> None:
    origin, destination = _cp(game, "Ramat David"), _cp(game, "Golan South")
    unit = _stock(origin)

    place_transfer(game, TransferOrder(origin, destination, {unit: 3}), None, NOW)

    assert origin.base.total_units_of_type(unit) == 2
    transfer = next(iter(game.blue.transfers))
    assert transfer.destination == destination
    assert isinstance(transfer.transport, Convoy)
    allocated = destination.allocated_ground_units(game.blue.transfers)
    assert allocated.total_transferring == 3

    game.blue.transfers.cancel_transfer(transfer)
    assert origin.base.total_units_of_type(unit) == 5


@pytest.mark.parametrize(
    "count, message",
    [(6, "has 5"), (0, "at least one"), (-1, "negative")],
)
def test_transfer_limits(game: Game, count: int, message: str) -> None:
    origin, destination = _cp(game, "Ramat David"), _cp(game, "Golan South")
    unit = _stock(origin)
    with pytest.raises(CommandError, match=message):
        place_transfer(
            game, TransferOrder(origin, destination, {unit: count}), None, NOW
        )
    assert origin.base.total_units_of_type(unit) == 5
    assert not list(game.blue.transfers)


def test_transfer_refuses_enemy_bases(game: Game) -> None:
    origin, enemy = _cp(game, "Ramat David"), _cp(game, "Golan North")
    unit = _stock(origin)
    with pytest.raises(CommandError, match="cannot receive"):
        place_transfer(game, TransferOrder(origin, enemy, {unit: 1}), None, NOW)
    enemy.base.commission_units({unit: 1})
    with pytest.raises(CommandError, match="not your base"):
        place_transfer(game, TransferOrder(enemy, origin, {unit: 1}), None, NOW)


def test_transport_mission_with_a_real_squadron(game: Game) -> None:
    origin, destination = _cp(game, "Ramat David"), _cp(game, "Golan South")
    unit = _stock(origin, 1)
    options = TransferOptionsJs.for_control_point(game, origin, destination.id)
    assert options.destination_id == destination.id
    assert options.squadrons, "the UH-1H of Golan South can fly it"
    assert options.no_squadron_warning is None
    squadron = next(
        s
        for s in game.blue.air_wing.iter_squadrons()
        if s.id == options.squadrons[0].id
    )
    packages = len(game.blue.ato.packages)

    transfer = TransferOrder(origin, destination, {unit: 1}, request_airflift=True)
    place_transfer(game, transfer, squadron, NOW)

    assert transfer.player_requested
    assert len(game.blue.ato.packages) == packages + 1
    assert origin.base.total_units_of_type(unit) == 0


def test_transport_mission_over_the_capacity_changes_nothing(game: Game) -> None:
    origin, destination = _cp(game, "Ramat David"), _cp(game, "Golan South")
    unit = _stock(origin, 50)
    options = TransferOptionsJs.for_control_point(game, origin, destination.id)
    squadron = next(
        s
        for s in game.blue.air_wing.iter_squadrons()
        if s.id == options.squadrons[0].id
    )
    packages = len(game.blue.ato.packages)
    transfer = TransferOrder(origin, destination, {unit: 50}, request_airflift=True)

    with pytest.raises(CommandError, match="can carry"):
        place_transfer(game, transfer, squadron, NOW)

    assert origin.base.total_units_of_type(unit) == 50
    assert not list(game.blue.transfers)
    assert len(game.blue.ato.packages) == packages


def test_transfer_options_read_model(game: Game) -> None:
    origin = _cp(game, "Ramat David")
    unit = _stock(origin, 2)
    assert [cp.name for cp in transfer_destinations(game, origin)] == ["Golan South"]
    assert transferable_units(game, origin) == {unit: 2}
    assert can_transfer_units(game, origin)
    assert can_plan_transport_mission(origin)
    assert not can_transfer_units(game, _cp(game, "Damascus"))
    assert not can_plan_transport_mission(_cp(game, "Damascus"))


# --- departing convoys --------------------------------------------------------


def _enemy_convoy(game: Game) -> tuple[ControlPoint, ControlPoint, GroundUnitType]:
    origin, destination = _cp(game, "Damascus"), _cp(game, "Marj Ruhayyil")
    unit = _tank(origin)
    origin.base.commission_units({unit: 4})
    game.red.transfers.new_transfer(TransferOrder(origin, destination, {unit: 4}), NOW)
    return origin, destination, unit


def test_departing_convoys_of_an_enemy_base(game: Game) -> None:
    origin, destination, unit = _enemy_convoy(game)

    convoys = DepartingConvoyJs.departing_from(game, origin)

    assert len(convoys) == 1
    assert convoys[0].kind == "convoy"
    assert convoys[0].destination_id == destination.id
    assert convoys[0].size == 4
    assert [(u.name, u.count) for u in convoys[0].units] == [(unit.display_name, 4)]
    assert DepartingConvoyJs.departing_from(game, destination) == []


def test_attack_target_is_the_real_convoy(game: Game) -> None:
    origin, destination, _ = _enemy_convoy(game)
    target = attackable_transport(game, origin, destination, "convoy")
    assert isinstance(target, Convoy)
    assert target.origin == origin

    with pytest.raises(CommandError, match="no longer departing") as gone:
        attackable_transport(game, origin, destination, "cargo-ship")
    assert gone.value.status_code == 404


def test_player_convoys_cannot_be_attacked(game: Game) -> None:
    origin, destination = _cp(game, "Ramat David"), _cp(game, "Golan South")
    unit = _stock(origin)
    place_transfer(game, TransferOrder(origin, destination, {unit: 1}), None, NOW)
    with pytest.raises(CommandError, match="is yours"):
        attackable_transport(game, origin, destination, "convoy")


# --- cheats -------------------------------------------------------------------


def test_cheats_need_their_setting(game: Game) -> None:
    cp, enemy = _cp(game, "Golan South"), _cp(game, "Golan North")
    events = GameUpdateEvents()
    with pytest.raises(CommandError, match="not enabled"):
        cheat_move_front_line(game, cp, enemy, True, events)
    with pytest.raises(CommandError, match="not enabled"):
        cheat_capture(game, enemy, events)
    with pytest.raises(CommandError, match="not available"):
        cheat_runway_state(game, _cp(game, "Ramat David"), events)
    actions = BaseActionsJs.for_control_point(game, cp)
    assert actions.cheat_capture is None
    assert actions.cheat_runway is None


def test_front_line_cheat_moves_the_front_line(game: Game) -> None:
    game.settings.enable_frontline_cheats = True
    cp, enemy = _cp(game, "Golan South"), _cp(game, "Golan North")
    front_line = cp.front_line_with(enemy)
    before = front_line.position
    strength = cp.base.strength
    events = GameUpdateEvents()

    cheat_move_front_line(game, cp, enemy, False, events)

    assert cp.base.strength < strength
    assert front_line.position != before
    assert front_line in events.updated_front_lines


def test_capture_cheat_flips_the_base_and_replans(game: Game) -> None:
    game.settings.enable_base_capture_cheat = True
    enemy = _cp(game, "Golan North")
    assert BaseActionsJs.for_control_point(game, enemy).cheat_capture == "Capture"

    state = cheat_capture(game, enemy, GameUpdateEvents())

    assert enemy.captured.is_blue
    assert state is TurnState.CONTINUE


def test_capturing_the_last_base_ends_the_campaign(game: Game) -> None:
    game.settings.enable_base_capture_cheat = True
    state: TurnState = TurnState.CONTINUE
    for cp in list(game.theater.controlpoints):
        if cp.captured.is_red:
            state = cheat_capture(game, cp, GameUpdateEvents())
    assert state is TurnState.WIN


def test_runway_cheat_toggles_the_runway(game: Game) -> None:
    game.settings.enable_runway_state_cheat = True
    cp = _cp(game, "Ramat David")
    actions = BaseActionsJs.for_control_point(game, cp)
    assert actions.cheat_runway == "Destroy runway"

    cheat_runway_state(game, cp, GameUpdateEvents())

    assert not cp.runway_is_operational()
    assert BaseActionsJs.for_control_point(game, cp).cheat_runway == "Repair runway"
    cheat_runway_state(game, cp, GameUpdateEvents())
    assert cp.runway_is_operational()


# --- radios -------------------------------------------------------------------


class _Carrier(Link4Container, TacanContainer, ICLSContainer):
    """The radio side of a carrier: the reference campaign has none."""

    name = "CVN-74"
    captured = Player.BLUE
    id = uuid4()


def test_fob_frequency(game: Game) -> None:
    fob = _cp(game, "Golan South")
    events = GameUpdateEvents()
    set_base_radios(fob, BaseRadios(frequency_mhz=251.25), events)
    assert base_radios(fob).frequency_mhz == 251.25
    assert fob in events.updated_control_points

    actions = BaseActionsJs.for_control_point(game, fob)
    assert actions.radios is not None
    assert actions.radios.has_frequency and not actions.radios.has_tacan

    set_base_radios(fob, BaseRadios(), GameUpdateEvents())
    assert base_radios(fob).frequency_mhz is None


def test_fob_guard_frequency_warns(game: Game) -> None:
    fob = _cp(game, "Golan South")
    set_base_radios(fob, BaseRadios(frequency_mhz=243.0), GameUpdateEvents())
    actions = BaseActionsJs.for_control_point(game, fob)
    assert actions.radios is not None
    assert "guard" in actions.radios.warnings[0]


def test_enemy_and_airfield_have_no_radio_settings(game: Game) -> None:
    for name in ("Golan North", "Ramat David"):
        cp = _cp(game, name)
        assert BaseActionsJs.for_control_point(game, cp).radios is None
        with pytest.raises(CommandError, match="no radio settings"):
            set_base_radios(cp, BaseRadios(frequency_mhz=251.0), GameUpdateEvents())


def test_settings_the_base_does_not_have(game: Game) -> None:
    with pytest.raises(CommandError, match="cannot have a TACAN"):
        set_base_radios(
            _cp(game, "Golan South"),
            BaseRadios(tacan_channel=74, tacan_band="X"),
            GameUpdateEvents(),
        )


def test_carrier_radios() -> None:
    carrier: Any = _Carrier()
    set_base_radios(
        carrier,
        BaseRadios(
            frequency_mhz=127.5,
            tacan_channel=74,
            tacan_band="X",
            tacan_callsign="sta",
            icls_channel=9,
            icls_callsign="st",
            link4_mhz=336,
        ),
        GameUpdateEvents(),
    )
    assert carrier.tacan == TacanChannel(74, TacanBand.X)
    assert carrier.tcn_name == "STA"
    assert (carrier.icls_channel, carrier.icls_name) == (9, "ST")
    assert carrier.link4.hertz == 336_000_000
    assert base_radios(carrier).frequency_mhz == 127.5


@pytest.mark.parametrize(
    "radios, message",
    [
        (BaseRadios(frequency_mhz=400), "frequency"),
        (BaseRadios(frequency_mhz=29.9), "frequency"),
        (BaseRadios(link4_mhz=127), "Link 4"),
        (BaseRadios(tacan_channel=127, tacan_band="X"), "TACAN"),
        (BaseRadios(tacan_channel=0, tacan_band="X"), "TACAN"),
        (BaseRadios(tacan_channel=74, tacan_band="Z"), "band"),
        (BaseRadios(tacan_channel=74), "band"),
        (BaseRadios(tacan_channel=74, tacan_band="X", tacan_callsign="ABCD"), "call"),
        (BaseRadios(icls_channel=21), "ICLS"),
    ],
)
def test_radio_limits_change_nothing(radios: BaseRadios, message: str) -> None:
    carrier: Any = _Carrier()
    with pytest.raises(CommandError, match=message):
        set_base_radios(carrier, radios, GameUpdateEvents())
    assert base_radios(carrier) == BaseRadios()


# --- HTTP side ----------------------------------------------------------------


@pytest.fixture
def served(
    game: Game, monkeypatch: pytest.MonkeyPatch, sim_reloads: list[bool]
) -> dict[str, Any]:

    def ignore(_: Any) -> None:
        pass

    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(
            game=game,
            sim_controller=SimpleNamespace(current_time_in_sim_if_game_loaded=NOW),
        ),
        raising=False,
    )
    published: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", published.append)
    return {
        "game": game,
        "reloads": sim_reloads,
        "published": published,
    }


def test_order_route(served: dict[str, Any]) -> None:
    game = served["game"]
    cp = _cp(game, "Ramat David")
    unit = _tank(cp)
    path = f"/control-points/{cp.id}/purchases/ground-units"

    status, body = _request(
        "POST", path, {"orders": [{"unit_id": unit.variant_id, "quantity": 2}]}
    )

    assert status == 200
    row = next(r for r in body["units"] if r["unit_id"] == unit.variant_id)
    assert row["pending"] == 2
    assert body["ordered"] == 2
    assert served["published"][-1].budget_updated

    status, body = _request(
        "POST", path, {"orders": [{"unit_id": unit.variant_id, "quantity": -5}]}
    )
    assert status == 409
    assert "cannot be sold" in body["detail"]
    assert cp.ground_unit_orders.pending_orders(unit) == 2


def test_order_route_refuses_a_unit_of_another_faction(served: dict[str, Any]) -> None:
    cp = _cp(served["game"], "Ramat David")
    status, body = _request(
        "POST",
        f"/control-points/{cp.id}/purchases/ground-units",
        {"orders": [{"unit_id": "nope", "quantity": 1}]},
    )
    assert status == 409
    assert "not a ground unit" in body["detail"]


def test_reads(served: dict[str, Any]) -> None:
    cp = _cp(served["game"], "Golan South")
    status, body = _request("GET", f"/control-points/{cp.id}/ground-forces")
    assert status == 200
    assert body["front_lines"][0]["enemy"] == "Golan North"
    status, body = _request("GET", f"/control-points/{cp.id}/convoys")
    assert (status, body) == (200, [])
    status, body = _request("GET", f"/control-points/{cp.id}/transfer-options")
    assert status == 200
    assert body["destinations"][0]["name"] == "Ramat David"
    status, body = _request("GET", f"/control-points/{cp.id}/actions")
    assert status == 200
    assert body["can_transfer"] is True
    status, _ = _request("GET", f"/control-points/{uuid4()}/ground-forces")
    assert status == 404


def test_stance_route(served: dict[str, Any]) -> None:
    game = served["game"]
    cp, enemy = _cp(game, "Golan South"), _cp(game, "Golan North")
    path = f"/control-points/{cp.id}/front-lines/{enemy.id}/stance"
    status, body = _request("PUT", path, {"stance": "AMBUSH"})
    assert status == 200
    assert body["front_lines"][0]["stance"] == "AMBUSH"
    status, body = _request("PUT", path, {"stance": "PANIC"})
    assert status == 409


def test_transfer_route(served: dict[str, Any]) -> None:
    game = served["game"]
    origin, destination = _cp(game, "Ramat David"), _cp(game, "Golan South")
    unit = _stock(origin)
    new = {
        "origin_id": str(origin.id),
        "destination_id": str(destination.id),
        "units": [{"unit_id": unit.variant_id, "count": 2}],
    }

    status, body = _request("POST", "/transfers/", new)

    assert status == 200
    assert (body["origin"], body["destination"], body["size"]) == (
        "Ramat David",
        "Golan South",
        2,
    )
    assert origin.base.total_units_of_type(unit) == 3
    assert any(origin in e.updated_control_points for e in served["published"])

    status, body = _request("GET", "/transfers/")
    assert status == 200
    assert len(body) == 1


def test_transfer_route_refusals(served: dict[str, Any]) -> None:
    game = served["game"]
    origin, destination = _cp(game, "Ramat David"), _cp(game, "Golan South")
    unit = _stock(origin)
    new: dict[str, Any] = {
        "origin_id": str(origin.id),
        "destination_id": str(destination.id),
        "units": [{"unit_id": unit.variant_id, "count": 6}],
    }
    status, body = _request("POST", "/transfers/", new)
    assert status == 409
    assert "has 5" in body["detail"]

    new["units"][0]["count"] = 1
    status, body = _request(
        "POST", "/transfers/", new | {"squadron_id": str(uuid4()), "airlift": False}
    )
    assert status == 409
    assert "Only an airlift" in body["detail"]

    status, _ = _request(
        "POST", "/transfers/", new | {"squadron_id": str(uuid4()), "airlift": True}
    )
    assert status == 404
    status, _ = _request("POST", "/transfers/", new | {"origin_id": str(uuid4())})
    assert status == 404
    assert not list(game.blue.transfers)


def test_attack_convoy_route_plans_a_package_for_the_web_editor(
    served: dict[str, Any],
) -> None:
    game = served["game"]
    origin, destination, _ = _enemy_convoy(game)
    status, body = _request(
        "POST", f"/control-points/{origin.id}/convoys/{destination.id}/package"
    )
    assert status == 201
    package = game.blue.ato.packages[-1]
    assert body["id"] == str(package.id)
    assert isinstance(package.target, Convoy)
    game.blue.ato.remove_package(package)


def test_radios_route(served: dict[str, Any]) -> None:
    fob = _cp(served["game"], "Golan South")
    path = f"/control-points/{fob.id}/radios"
    status, body = _request("PUT", path, {"frequency_mhz": 251.25})
    assert status == 200
    assert body["radios"]["frequency_mhz"] == 251.25
    status, body = _request("PUT", path, {"frequency_mhz": 500})
    assert status == 409
    assert "frequency" in body["detail"]


def test_cheat_routes(served: dict[str, Any]) -> None:
    game = served["game"]
    cp, enemy = _cp(game, "Golan South"), _cp(game, "Golan North")

    status, body = _request("POST", f"/control-points/{enemy.id}/cheat/capture")
    assert status == 409
    assert "not enabled" in body["detail"]

    game.settings.enable_frontline_cheats = True
    status, _ = _request(
        "POST",
        f"/control-points/{cp.id}/front-lines/{enemy.id}/cheat",
        {"advance": True},
    )
    assert status == 204
    assert served["reloads"]

    game.settings.enable_runway_state_cheat = True
    airfield = _cp(game, "Ramat David")
    status, _ = _request("POST", f"/control-points/{airfield.id}/cheat/runway")
    assert status == 204
    assert not airfield.runway_is_operational()

    game.settings.enable_base_capture_cheat = True
    status, _ = _request("POST", f"/control-points/{enemy.id}/cheat/capture")
    assert status == 204
    assert enemy.captured.is_blue
    assert served["reloads"]

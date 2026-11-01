"""WEB-02.2: aircraft orders and squadron creation at a base."""

from __future__ import annotations

import asyncio
import json
from collections.abc import MutableMapping
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from dcs.helicopters import UH_1H
from dcs.planes import A_10C, F_16C_50

from game.ato.flighttype import FlightType
from game.commands import (
    AircraftOrder,
    AircraftPurchaseAdapter,
    CommandError,
    cancel_aircraft_orders,
    change_aircraft_order,
    create_squadron,
    max_aircraft_to_add,
    max_aircraft_to_remove,
    order_aircraft,
    squadron_choices,
)
from game.db.database import Database
from game.dcs.aircrafttype import AircraftType
from game.dcs.countries import country_with_name
from game.server import GameContext
from game.server.app import app
from game.server.controlpoints.aircraftorders import AirfieldJs
from game.server.eventstream import EventStream
from game.server.security import ApiKeyManager
from game.settings import Settings
from game.sim import GameUpdateEvents
from game.squadrons import Squadron
from game.squadrons.operatingbases import OperatingBases
from game.squadrons.squadrondef import SquadronDef
from game.theater import ParkingType
from game.theater.controlpoint import ControlPoint
from game.theater.player import Player
from .test_base_screen import _Cp, _game

VIPER: AircraftType
HOG: AircraftType
HUEY: AircraftType


@pytest.fixture(autouse=True)
def _load_aircraft() -> None:
    """Aircraft data needs the persistency setup of conftest: not at import time."""
    global VIPER, HOG, HUEY
    VIPER = next(AircraftType.for_dcs_type(F_16C_50))
    HOG = next(AircraftType.for_dcs_type(A_10C))
    HUEY = next(AircraftType.for_dcs_type(UH_1H))


def _def(aircraft: AircraftType, name: str, nickname: str | None = None) -> SquadronDef:
    return SquadronDef(
        name=name,
        nickname=nickname,
        country=country_with_name("USA"),
        role="test",
        aircraft=aircraft,
        livery=None,
        livery_set=[],
        auto_assignable_mission_types=set(aircraft.iter_task_capabilities()),
        radio_presets={},
        operating_bases=OperatingBases.default_for_aircraft(aircraft),
        female_pilot_percentage=0,
        pilot_pool=[],
    )


class _AirWing:
    def __init__(self) -> None:
        self.added: list[Squadron] = []
        self.squadron_defs: dict[AircraftType, list[SquadronDef]] = {}
        self.squadron_def_generator = SimpleNamespace(
            generate_for_aircraft=lambda aircraft: _def(aircraft, "Squadron 001")
        )

    def iter_squadrons(self) -> Any:
        return iter(self.added)

    def add_squadron(self, squadron: Squadron) -> None:
        self.added.append(squadron)


class _Coalition:
    def __init__(self, budget: float, settings: Settings) -> None:
        self.budget = budget
        self.player = Player.BLUE
        self.game = SimpleNamespace(settings=settings)
        self.air_wing = _AirWing()
        self.faction = SimpleNamespace(
            all_aircrafts=[VIPER, HOG, HUEY], locales=None, country=None
        )

    def adjust_budget(self, amount: float) -> None:
        self.budget += amount


class _AirBase(_Cp):
    """A base with `slots` fixed wing slots and 2 helicopter slots, real parking rules."""

    def __init__(self, budget: float, slots: int, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.slots = slots
        self.coalition = _Coalition(budget, settings)  # type: ignore[assignment]
        self.incapable: set[AircraftType] = set()
        del self.squadrons

    @property
    def squadrons(self) -> list[Squadron]:
        return [s for s in self.coalition.air_wing.added if s.location == self]

    @squadrons.setter
    def squadrons(self, _value: Any) -> None:
        pass

    @squadrons.deleter
    def squadrons(self) -> None:
        pass

    def total_aircraft_parking(self, parking_type: ParkingType) -> int:
        return self.slots + (2 if parking_type.include_rotary_wing else 0)

    def allocated_aircraft(self, parking_type: ParkingType) -> Any:
        return ControlPoint.allocated_aircraft(cast(ControlPoint, self), parking_type)

    def unclaimed_parking(self, parking_type: ParkingType) -> int:
        return ControlPoint.unclaimed_parking(cast(ControlPoint, self), parking_type)

    def _unclaimed_parking_in(self, parking_type: ParkingType) -> int:
        return ControlPoint._unclaimed_parking_in(
            cast(ControlPoint, self), parking_type
        )

    def can_operate(self, aircraft: AircraftType) -> bool:
        return aircraft not in self.incapable

    is_carrier = False
    is_lha = False


def _squadron(
    cp: _AirBase,
    aircraft: AircraftType | None = None,
    name: str = "Viper",
    owned: int = 0,
    max_size: int = 4,
) -> Squadron:
    aircraft = aircraft or VIPER
    squadron = Squadron(
        name=name,
        nickname=None,
        country=country_with_name("USA"),
        role="test",
        aircraft=aircraft,
        max_size=max_size,
        livery=None,
        livery_set=[],
        primary_task=FlightType.STRIKE,
        auto_assignable_mission_types=set(aircraft.iter_task_capabilities()),
        radio_presets={},
        operating_bases=OperatingBases.default_for_aircraft(aircraft),
        female_pilot_percentage=0,
        pilot_pool=[],
        coalition=cp.coalition,  # type: ignore[arg-type]
        flight_db=Database(),
        settings=cp.settings,
        location=cp,  # type: ignore[arg-type]
    )
    squadron.owned_aircraft = owned
    squadron.untasked_aircraft = owned
    cp.coalition.air_wing.added.append(squadron)
    return squadron


def _base(
    budget: float = 10_000, slots: int = 20, limits: bool = True
) -> tuple[Any, Settings]:
    settings = Settings()
    settings.enable_squadron_aircraft_limits = limits
    return _AirBase(budget, slots, settings), settings


def _order(cp: Any, squadron: Squadron, quantity: int) -> None:
    order_aircraft(cp, [AircraftOrder(squadron, quantity)], GameUpdateEvents())


# --- buying -------------------------------------------------------------------


def test_order_pays_and_books_the_delivery() -> None:
    cp, _ = _base()
    squadron = _squadron(cp)
    events = GameUpdateEvents()
    order_aircraft(cp, [AircraftOrder(squadron, 2)], events)
    assert squadron.pending_deliveries == 2
    assert squadron.owned_aircraft == 0
    assert cp.coalition.budget == 10_000 - 2 * VIPER.price
    assert events.budget_updated
    assert cp in events.updated_control_points


def test_budget_refuses_the_whole_order() -> None:
    cp, _ = _base(budget=VIPER.price * 1.5)
    squadron = _squadron(cp)
    with pytest.raises(CommandError) as error:
        _order(cp, squadron, 2)
    assert "you have only" in error.value.message
    assert squadron.pending_deliveries == 0
    assert cp.coalition.budget == VIPER.price * 1.5


def test_order_is_atomic_across_squadrons() -> None:
    cp, _ = _base(budget=VIPER.price * 2 + HOG.price - 1)
    viper, hog = _squadron(cp), _squadron(cp, HOG, "Hog")
    budget = cp.coalition.budget
    with pytest.raises(CommandError):
        order_aircraft(
            cp,
            [AircraftOrder(viper, 2), AircraftOrder(hog, 1)],
            GameUpdateEvents(),
        )
    assert viper.pending_deliveries == 0
    assert hog.pending_deliveries == 0
    assert cp.coalition.budget == budget


def test_parking_refuses_and_counts_other_orders() -> None:
    cp, _ = _base(slots=3)
    full = _squadron(cp, owned=2)
    other = _squadron(cp, HOG, "Hog")
    _order(cp, other, 1)
    with pytest.raises(CommandError) as error:
        _order(cp, full, 1)
    assert "No parking left" in error.value.message
    assert max_aircraft_to_add(cp, full) == 0


def test_parking_pools_are_shared_with_helicopters() -> None:
    # 3 + 2 = 5 slots in all: 4 helicopters leave 1, not the 3 fixed wing slots.
    cp, _ = _base(slots=3)
    _squadron(cp, HUEY, "Huey", owned=4, max_size=8)
    viper = _squadron(cp)
    assert max_aircraft_to_add(cp, viper) == 1
    _order(cp, viper, 1)
    with pytest.raises(CommandError):
        _order(cp, viper, 1)


def test_squadron_limit_follows_the_setting() -> None:
    cp, _ = _base()
    squadron = _squadron(cp, owned=3, max_size=4)
    with pytest.raises(CommandError) as error:
        _order(cp, squadron, 2)
    assert error.value.message == "Viper is full: 4 aircraft at most."

    cp, _ = _base(limits=False)
    squadron = _squadron(cp, owned=3, max_size=4)
    _order(cp, squadron, 2)
    assert squadron.pending_deliveries == 2
    assert AirfieldJs.for_control_point(cp).squadrons[0].max_aircraft is None


def test_base_rules() -> None:
    cp, _ = _base()
    squadron = _squadron(cp)
    with pytest.raises(CommandError) as error:
        order_aircraft(cp, [], GameUpdateEvents())
    assert error.value.message == "The order is empty."

    elsewhere, _ = _base()
    with pytest.raises(CommandError) as error:
        _order(elsewhere, squadron, 1)
    assert "not stationed" in error.value.message

    cp.captured = SimpleNamespace(is_blue=False)
    with pytest.raises(CommandError) as error:
        _order(cp, squadron, 1)
    assert "not your base" in error.value.message


# --- cancelling and selling ---------------------------------------------------


def test_removing_cancels_orders_then_sells() -> None:
    cp, _ = _base()
    squadron = _squadron(cp, owned=1)
    _order(cp, squadron, 1)
    assert max_aircraft_to_remove(squadron) == 2

    _order(cp, squadron, -1)
    assert squadron.pending_deliveries == 0
    assert squadron.untasked_aircraft == 1
    assert cp.coalition.budget == 10_000

    _order(cp, squadron, -1)
    assert squadron.pending_deliveries == -1
    assert squadron.untasked_aircraft == 0
    assert cp.coalition.budget == 10_000 + VIPER.price

    with pytest.raises(CommandError) as error:
        _order(cp, squadron, -1)
    assert "no aircraft to sell" in error.value.message


def test_removals_free_what_purchases_of_the_same_order_need() -> None:
    cp, _ = _base(budget=0)
    viper = _squadron(cp, owned=2)
    hog = _squadron(cp, HOG, "Hog")
    order_aircraft(
        cp,
        [AircraftOrder(hog, 1), AircraftOrder(viper, -2)],
        GameUpdateEvents(),
    )
    assert hog.pending_deliveries == 1
    assert cp.coalition.budget == 2 * VIPER.price - HOG.price


def test_cancel_pending_orders_and_sales() -> None:
    cp, _ = _base()
    squadron = _squadron(cp, owned=1)
    _order(cp, squadron, 3)
    cancel_aircraft_orders(cp, squadron, GameUpdateEvents())
    assert squadron.pending_deliveries == 0
    assert cp.coalition.budget == 10_000

    _order(cp, squadron, -1)
    cancel_aircraft_orders(cp, squadron, GameUpdateEvents())
    assert squadron.pending_deliveries == 0
    assert squadron.untasked_aircraft == 1
    assert cp.coalition.budget == 10_000

    with pytest.raises(CommandError) as error:
        cancel_aircraft_orders(cp, squadron, GameUpdateEvents())
    assert error.value.message == "Viper has no pending order."


def test_cancelling_a_sale_needs_the_money() -> None:
    cp, _ = _base(budget=0)
    squadron = _squadron(cp, owned=1)
    _order(cp, squadron, -1)
    cp.coalition.budget = 0
    with pytest.raises(CommandError):
        cancel_aircraft_orders(cp, squadron, GameUpdateEvents())
    assert squadron.pending_deliveries == -1


# --- Qt -----------------------------------------------------------------------


def test_qt_clicks_keep_what_fits() -> None:
    cp, _ = _base(slots=3)
    squadron = _squadron(cp)
    events = GameUpdateEvents()
    with pytest.raises(CommandError):
        change_aircraft_order(cp, squadron, 10, events)
    assert squadron.pending_deliveries == 3
    assert events.budget_updated


def test_qt_adapter_agrees_with_the_commands() -> None:
    cp, _ = _base(slots=1)
    squadron = _squadron(cp)
    adapter = AircraftPurchaseAdapter(cp)
    assert adapter.can_buy(squadron)
    _order(cp, squadron, 1)
    assert not adapter.can_buy(squadron)
    assert adapter.can_sell_or_cancel(squadron)


# --- DTO ----------------------------------------------------------------------


def test_airfield_rows_and_parking_after_delivery() -> None:
    cp, _ = _base(budget=VIPER.price * 2, slots=10)
    _squadron(cp, owned=2, max_size=3)
    _squadron(cp, HOG, "Hog", owned=1)
    transfer = _squadron(_base()[0], name="Incoming", owned=5)
    transfer.destination = cp
    cp.coalition.air_wing.added.append(transfer)

    airfield = AirfieldJs.for_control_point(cp)
    hog, viper = airfield.squadrons
    assert hog.squadron == "Hog"
    assert (viper.owned, viper.max_aircraft, viper.pending) == (2, 3, 0)
    assert viper.unit_cost == VIPER.price
    assert (viper.max_add, viper.max_remove) == (1, 2)
    assert airfield.parking_after_delivery.current == 3 + 5
    assert airfield.parking_after_delivery.total == 12
    assert [(i.squadron, i.owned) for i in airfield.incoming] == [("Incoming", 5)]


def test_enemy_base_shows_no_squadrons() -> None:
    cp, _ = _base()
    _squadron(cp)
    cp.captured = SimpleNamespace(is_blue=False)
    assert AirfieldJs.for_control_point(cp).squadrons == []
    assert squadron_choices(cp) == []


# --- squadron creation --------------------------------------------------------


def test_create_squadron_generates_one_with_pilots_and_no_aircraft() -> None:
    cp, settings = _base()
    events = GameUpdateEvents()
    squadron = create_squadron(
        SimpleNamespace(db=SimpleNamespace(flights=Database()), settings=settings),  # type: ignore[arg-type]
        cp,
        VIPER.variant_id,
        FlightType.BARCAP.value,
        None,
        events,
    )
    assert squadron in cp.coalition.air_wing.added
    assert squadron.location is cp
    assert squadron.primary_task is FlightType.BARCAP
    assert squadron.owned_aircraft == 0
    assert len(squadron.current_roster) == settings.squadron_pilot_limit
    assert cp in events.updated_control_points
    assert squadron in cp.squadrons


def test_create_squadron_claims_its_preset() -> None:
    cp, settings = _base()
    preset = _def(VIPER, "Triple Nickel", "Nickel")
    claimed = _def(VIPER, "Taken")
    claimed.claimed = True
    cp.coalition.air_wing.squadron_defs[VIPER] = [preset, claimed]
    game: Any = SimpleNamespace(
        db=SimpleNamespace(flights=Database()), settings=settings
    )
    viper = next(c for c in squadron_choices(cp) if c.aircraft == VIPER)
    assert [d.name for d in viper.presets] == ["Triple Nickel"]

    squadron = create_squadron(
        game,
        cp,
        VIPER.variant_id,
        FlightType.BARCAP.value,
        "Triple Nickel",
        GameUpdateEvents(),
    )
    assert squadron.name == "Triple Nickel"
    assert preset.claimed
    with pytest.raises(CommandError) as error:
        create_squadron(
            game,
            cp,
            VIPER.variant_id,
            FlightType.BARCAP.value,
            "Triple Nickel",
            GameUpdateEvents(),
        )
    assert "not available" in error.value.message


@pytest.mark.parametrize(
    "aircraft,task,message",
    [
        ("Not an aircraft", "BARCAP", "not in your faction"),
        (None, "Not a task", "cannot fly"),
    ],
)
def test_create_squadron_refuses_what_the_base_does_not_offer(
    aircraft: str | None, task: str, message: str
) -> None:
    cp, settings = _base()
    game: Any = SimpleNamespace(
        db=SimpleNamespace(flights=Database()), settings=settings
    )
    with pytest.raises(CommandError) as error:
        create_squadron(
            game, cp, aircraft or VIPER.variant_id, task, None, GameUpdateEvents()
        )
    assert message in error.value.message
    assert cp.coalition.air_wing.added == []


def test_choices_are_the_faction_aircraft_the_base_can_operate() -> None:
    cp, _ = _base()
    cp.incapable = {HUEY}
    names = [c.aircraft for c in squadron_choices(cp)]
    assert names == sorted([VIPER, HOG], key=lambda a: a.display_name)
    cp.coalition.faction.all_aircrafts = [HOG]
    assert [c.aircraft for c in squadron_choices(cp)] == [HOG]
    with pytest.raises(CommandError):
        create_squadron(
            SimpleNamespace(),  # type: ignore[arg-type]
            cp,
            VIPER.variant_id,
            FlightType.BARCAP.value,
            None,
            GameUpdateEvents(),
        )
    enemy, _ = _base()
    enemy.captured = SimpleNamespace(is_blue=False)
    with pytest.raises(CommandError) as error:
        create_squadron(
            SimpleNamespace(),  # type: ignore[arg-type]
            enemy,
            HOG.variant_id,
            FlightType.CAS.value,
            None,
            GameUpdateEvents(),
        )
    assert "not your base" in error.value.message


# --- HTTP side ----------------------------------------------------------------


@pytest.fixture
def loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, Squadron, list[GameUpdateEvents]]:
    cp, settings = _base(budget=VIPER.price * 3)
    squadron = _squadron(cp, owned=1)
    game = _game(budget=cp.coalition.budget, cp=cp)
    game.settings = settings
    game.db = SimpleNamespace(flights=Database())
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=game), raising=False
    )
    published: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", published.append)
    return cp, squadron, published


def _request(method: str, path: str, body: Any = None) -> tuple[int, Any]:
    payload = b"" if body is None else json.dumps(body).encode()
    messages: list[MutableMapping[str, Any]] = []

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
            (b"content-length", str(len(payload)).encode()),
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
    return status, json.loads(content) if content else None


def test_order_route(loaded: tuple[Any, Squadron, list[GameUpdateEvents]]) -> None:
    cp, squadron, published = loaded
    status, body = _request(
        "POST",
        f"/control-points/{cp.id}/purchases/aircraft",
        {"orders": [{"squadron_id": str(squadron.id), "quantity": 2}]},
    )
    assert status == 200
    row = body["airfield"]["squadrons"][0]
    assert (row["squadron"], row["owned"], row["pending"]) == ("Viper", 1, 2)
    assert row["unit_cost"] == VIPER.price
    assert squadron.pending_deliveries == 2
    assert published[-1].budget_updated


def test_order_route_refusals(
    loaded: tuple[Any, Squadron, list[GameUpdateEvents]],
) -> None:
    cp, squadron, _ = loaded
    status, body = _request(
        "POST",
        f"/control-points/{cp.id}/purchases/aircraft",
        {"orders": [{"squadron_id": str(squadron.id), "quantity": 4}]},
    )
    assert status == 409
    assert "you have only" in body["detail"]
    assert squadron.pending_deliveries == 0

    status, _ = _request(
        "POST",
        f"/control-points/{cp.id}/purchases/aircraft",
        {"orders": [{"squadron_id": str(uuid4()), "quantity": 1}]},
    )
    assert status == 404


def test_cancel_route(loaded: tuple[Any, Squadron, list[GameUpdateEvents]]) -> None:
    cp, squadron, published = loaded
    _order(cp, squadron, 1)
    path = f"/control-points/{cp.id}/purchases/aircraft/{squadron.id}"
    status, body = _request("DELETE", path)
    assert status == 200
    assert body["airfield"]["squadrons"][0]["pending"] == 0
    assert published[-1].budget_updated
    status, body = _request("DELETE", path)
    assert status == 409
    assert body["detail"] == "Viper has no pending order."


def test_squadron_routes(loaded: tuple[Any, Squadron, list[GameUpdateEvents]]) -> None:
    cp, _, _ = loaded
    cp.coalition.air_wing.squadron_defs[HOG] = [_def(HOG, "Flying Tigers", "Tigers")]
    status, choices = _request("GET", f"/control-points/{cp.id}/squadron-choices")
    assert status == 200
    hog = next(c for c in choices if c["aircraft"] == HOG.variant_id)
    assert hog["display_name"] == HOG.display_name
    assert FlightType.CAS.value in hog["tasks"]
    assert hog["presets"] == [
        {"name": "Flying Tigers", "label": "Flying Tigers (Tigers)"}
    ]

    status, body = _request(
        "POST",
        f"/control-points/{cp.id}/squadrons",
        {
            "aircraft": HOG.variant_id,
            "primary_task": FlightType.CAS.value,
            "preset": "Flying Tigers",
        },
    )
    assert status == 200
    assert "Flying Tigers" in [r["squadron"] for r in body["airfield"]["squadrons"]]

    status, body = _request(
        "POST",
        f"/control-points/{cp.id}/squadrons",
        {"aircraft": "Nope", "primary_task": FlightType.CAS.value},
    )
    assert status == 409
    assert "not in your faction" in body["detail"]

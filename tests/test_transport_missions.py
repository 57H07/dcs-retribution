"""Playable transport flights (TRN-01.3, #30)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from dcs import Point
from dcs.helicopters import CH_47D, UH_1H

from game import persistency
from game.ato.airtaaskingorder import AirTaskingOrder
from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.db.database import Database
from game.dcs.aircrafttype import AircraftType
from game.dcs.countries import country_with_name
from game.settings import Settings
from game.squadrons import Squadron
from game.squadrons.airwing import AirWing
from game.squadrons.operatingbases import OperatingBases
from game.theater.player import Player
from game.transfers import (
    AirliftPlanner,
    PendingTransfers,
    TransferOrder,
    airlift_squadrons,
    reassign_airlift,
)
from game.utils import nautical_miles

NOW = datetime(2026, 1, 1, 12)


def _control_point(name: str, x: float = 0) -> MagicMock:
    cp = MagicMock(name=name)
    cp.name = name
    cp.captured = Player.BLUE
    cp.position = Point(x, 0, None)  # type: ignore[arg-type]
    cp.is_friendly.side_effect = lambda player: player == Player.BLUE
    cp.can_operate.return_value = True
    cp.unclaimed_parking.return_value = 100
    cp.required_aircraft_start_type = None
    cp.is_fleet = False
    return cp


@pytest.fixture(autouse=True)
def _no_flight_plans(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Default loadouts read the saved-games folder; point it at a throwaway dir.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16884)
    # Routing needs a theater; these tests are about the transfer bookkeeping.
    monkeypatch.setattr(Flight, "recreate_flight_plan", lambda self: None)
    monkeypatch.setattr(Package, "set_tot_asap", lambda self, now: None)


class _World:
    """The slice of a Game that transfers and airlift planning use."""

    def __init__(self) -> None:
        self.settings = Settings()
        self.settings.enable_squadron_pilot_limits = True
        self.settings.squadron_pilot_limit = 12
        self.db = MagicMock()
        self.db.flights = Database()
        self.coalition = MagicMock()
        self.coalition.player = Player.BLUE
        self.coalition.ato = AirTaskingOrder()
        self.coalition.game = self
        self.coalition.faction.locales = None
        self.air_wing: AirWing = object.__new__(AirWing)
        self.air_wing.squadrons = {}
        self.coalition.air_wing = self.air_wing
        self.game: Any = MagicMock()
        self.game.settings = self.settings
        self.game.db = self.db
        self.game.coalition_for.return_value = self.coalition
        self.game.ato_for.return_value = self.coalition.ato
        self.game.air_wing_for.return_value = self.air_wing
        self.coalition.transfers = PendingTransfers(self.game, Player.BLUE)

    @property
    def transfers(self) -> PendingTransfers:
        return self.coalition.transfers

    def squadron(
        self,
        location: MagicMock,
        dcs_type: Any = UH_1H,
        auto_assignable: set[FlightType] | None = None,
        aircraft_count: int = 4,
    ) -> Squadron:
        aircraft = next(AircraftType.for_dcs_type(dcs_type))
        if auto_assignable is None:
            auto_assignable = set(aircraft.iter_task_capabilities())
        squadron = Squadron(
            name=f"{aircraft.variant_id} squadron",
            nickname=None,
            country=country_with_name("USA"),
            role="test",
            aircraft=aircraft,
            max_size=16,
            livery=None,
            livery_set=[],
            primary_task=FlightType.TRANSPORT,
            auto_assignable_mission_types=auto_assignable,
            radio_presets={},
            operating_bases=OperatingBases.default_for_aircraft(aircraft),
            female_pilot_percentage=0,
            pilot_pool=[],
            coalition=self.coalition,
            flight_db=self.db.flights,
            settings=self.settings,
            location=location,
        )
        squadron.populate_for_turn_0(squadrons_start_full=False)
        squadron.owned_aircraft = aircraft_count
        squadron.untasked_aircraft = aircraft_count
        self.air_wing.squadrons.setdefault(aircraft, []).append(squadron)
        return squadron


@pytest.fixture
def world() -> _World:
    return _World()


def _transfer_flight(
    world: _World, squadron: Squadron, units: int = 1
) -> tuple[TransferOrder, Flight]:
    """A transport flight as AirliftPlanner creates it after a unit transfer."""
    origin = _control_point("Origin")
    destination = _control_point("Destination", nautical_miles(30).meters)
    transfer = TransferOrder(origin, destination, {MagicMock(name="tank"): units})
    world.transfers.pending_transfers.append(transfer)
    planner = AirliftPlanner(world.game, transfer, destination)
    planner.create_airlift_flight(squadron)
    flight = planner.package.flights[0]
    return transfer, flight


def _replace_squadron(flight: Flight, squadron: Squadron) -> Flight:
    """Mirrors QFlightSlotEditor._change_squadron."""
    new_flight = Flight(
        flight.package,
        squadron,
        flight.count,
        flight.flight_type,
        flight.start_type,
        divert=None,
        cargo=flight.cargo,
    )
    reassign_airlift(flight, new_flight)
    flight.package.add_flight(new_flight)
    flight.package.remove_flight(flight)
    return new_flight


def test_transfer_generated_transport_flight_accepts_a_player_pilot(
    world: _World,
) -> None:
    squadron = world.squadron(_control_point("Home"))
    transfer, flight = _transfer_flight(world, squadron)

    pilot = flight.roster.pilot_at(0)
    assert pilot is not None
    pilot.player = True

    assert flight.client_count == 1
    assert flight.cargo is transfer
    # Mission generation finds the cargo (CTLD crates, unit map) through this.
    assert world.transfers.transfer_for_flight(flight) is transfer


def test_changing_the_squadron_keeps_the_cargo_and_its_delivery(
    world: _World,
) -> None:
    home = _control_point("Home")
    transfer, flight = _transfer_flight(world, world.squadron(home))
    destination = transfer.next_stop
    player_squadron = world.squadron(home, auto_assignable=set())

    new_flight = _replace_squadron(flight, player_squadron)

    assert new_flight.cargo is transfer
    assert transfer.transport is not None
    assert transfer.next_stop is destination
    assert world.transfers.transfer_for_flight(new_flight) is transfer
    assert world.transfers.transfer_for_flight(flight) is None

    # Delivery at turn end still happens.
    transfer.proceed()
    assert transfer.position is destination


def test_deleting_a_transfer_flight_still_releases_its_cargo(world: _World) -> None:
    transfer, flight = _transfer_flight(world, world.squadron(_control_point("Home")))
    flight.package.remove_flight(flight)
    # Re-planned by the AI next turn, as before.
    assert transfer.transport is None


def test_squadrons_kept_off_auto_planning_can_take_a_transfer_flight(
    world: _World,
) -> None:
    home = _control_point("Home")
    auto = world.squadron(home)
    player_only = world.squadron(home, dcs_type=CH_47D, auto_assignable=set())
    too_far = world.squadron(_control_point("Far", nautical_miles(250).meters))
    transfer, flight = _transfer_flight(world, auto)

    offered = airlift_squadrons(world.air_wing, transfer, transfer.next_stop, 1)

    assert player_only in offered
    assert auto in offered
    assert too_far not in offered
    # A squadron without enough free aircraft for the flight is not offered.
    assert player_only not in airlift_squadrons(
        world.air_wing, transfer, transfer.next_stop, 5
    )

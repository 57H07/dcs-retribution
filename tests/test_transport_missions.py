"""Playable transport flights (TRN-01.3, #30) and player Transport missions
(TRN-01.2, #29)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from dcs import Point
from dcs.helicopters import CH_47D, UH_1H
from dcs.planes import C_130

from game import persistency
from game.ato.airtaaskingorder import AirTaskingOrder
from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.package import Package
from game.db.database import Database
from game.debriefing import AirLosses, Debriefing, GroundLosses
from game.missiongenerator.kneeboard import TransportTaskPage
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.sim.simulationresults import SimulationResults
from game.unitmap import FlyingUnit, UnitMap
from game.dcs.aircrafttype import AircraftType
from game.dcs.countries import country_with_name
from game.settings import Settings
from game.squadrons import Squadron
from game.squadrons.airwing import AirWing
from game.squadrons.operatingbases import OperatingBases
from game.theater.controlpoint import Airfield
from game.theater.player import Player
from game.transfers import (
    AirliftPlanner,
    PendingTransfers,
    PlayerAirliftError,
    TransferOrder,
    airlift_squadrons,
    player_airlift_problem,
    reassign_airlift,
)
from game.utils import nautical_miles

NOW = datetime(2026, 1, 1, 12)


def _control_point(name: str, x: float = 0) -> MagicMock:
    # An airfield with designer CTLD zones, so helicopters can serve it.
    cp = MagicMock(spec=Airfield)
    cp.name = name
    cp.ctld_zones = [(Point(x, 500, None), 100.0)]  # type: ignore[arg-type]
    cp.base = MagicMock()
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


# --- Player-created Transport missions (TRN-01.2, #29) -----------------------------


def _base(cp: Any) -> MagicMock:
    """The mocked Base of a test control point."""
    return cast(MagicMock, cp.base)


def _player_mission(
    world: _World, squadron: Squadron, units: int = 1
) -> tuple[TransferOrder, Package]:
    origin = squadron.location
    destination = _control_point("Destination", nautical_miles(40).meters)
    tank = MagicMock(name="tank")
    tank.display_name = "M1A2"
    transfer = TransferOrder(origin, destination, {tank: units})
    package = world.transfers.new_player_airlift(transfer, squadron, NOW)
    return transfer, package


def test_transport_mission_between_two_friendly_bases_creates_a_flight_with_cargo(
    world: _World,
) -> None:
    # The player may use a squadron kept off auto-planning.
    squadron = world.squadron(
        _control_point("Origin"), dcs_type=C_130, auto_assignable=set()
    )

    transfer, package = _player_mission(world, squadron, units=3)

    assert package in world.coalition.ato.packages
    [flight] = package.flights
    assert flight.flight_type is FlightType.TRANSPORT
    assert flight.squadron is squadron
    assert flight.cargo is transfer
    assert flight.count == 2  # Two vehicles per cargo plane.
    assert transfer.player_requested and transfer.request_airflift
    assert transfer.next_stop is transfer.destination
    assert transfer in world.transfers.pending_transfers
    assert world.transfers.player_airlift_for(flight) is transfer
    _base(transfer.origin).commit_losses.assert_called_once_with(transfer.units)


def test_helicopter_transport_mission(world: _World) -> None:
    squadron = world.squadron(_control_point("Origin"), dcs_type=UH_1H)
    _, package = _player_mission(world, squadron, units=2)
    assert package.flights[0].count == 2  # One vehicle per helicopter.


def test_completed_transport_mission_delivers_the_cargo_next_turn(
    world: _World,
) -> None:
    squadron = world.squadron(_control_point("Origin"), dcs_type=C_130)
    transfer, _ = _player_mission(world, squadron, units=2)
    units = dict(transfer.units)
    delivered: list[dict[Any, int]] = []
    # disband_at clears the dict it hands over: record a copy.
    _base(transfer.destination).commission_units.side_effect = lambda u: (
        delivered.append(dict(u))
    )

    world.transfers.perform_transfers()

    assert delivered == [units]
    assert transfer not in world.transfers.pending_transfers


def _empty_debriefing() -> Debriefing:
    debriefing = Debriefing.__new__(Debriefing)
    debriefing.air_losses = AirLosses(player=[], enemy=[])
    debriefing.ground_losses = GroundLosses()
    return debriefing


def test_losing_the_transport_flight_kills_the_cargo(world: _World) -> None:
    squadron = world.squadron(_control_point("Origin"), dcs_type=C_130)
    transfer, package = _player_mission(world, squadron, units=2)
    [flight] = package.flights

    # Shot down in DCS: the unit map ties each aircraft to its slice of the cargo.
    unit_map = UnitMap()
    group = SimpleNamespace(
        units=[SimpleNamespace(name="Transport 1-1"), SimpleNamespace(name="1-2")]
    )
    unit_map.add_aircraft(cast(Any, group), flight)
    debriefing = _empty_debriefing()
    for name in ("Transport 1-1", "1-2"):
        airlift = unit_map.airlift_unit(name)
        assert airlift is not None
        debriefing.ground_losses.player_airlifts.append(airlift)

    MissionResultsProcessor.commit_airlift_losses(debriefing)

    assert transfer.size == 0
    world.transfers.perform_transfers()
    _base(transfer.destination).commission_units.assert_called_once_with({})


def test_transport_mission_shot_down_in_auto_resolve_loses_its_cargo(
    world: _World,
) -> None:
    squadron = world.squadron(_control_point("Origin"), dcs_type=C_130)
    transfer, package = _player_mission(world, squadron, units=2)
    [flight] = package.flights
    results = SimulationResults()
    for pilot in flight.roster.iter_pilots():
        results.air_losses.append(FlyingUnit(flight, pilot))
    debriefing = _empty_debriefing()

    debriefing.merge_simulation_results(results)
    MissionResultsProcessor.commit_airlift_losses(debriefing)

    assert transfer.size == 0


def test_cargo_larger_than_one_flight_is_refused_without_side_effects(
    world: _World,
) -> None:
    squadron = world.squadron(
        _control_point("Origin"), dcs_type=UH_1H, aircraft_count=2
    )
    with pytest.raises(PlayerAirliftError, match="can carry 2 units"):
        _player_mission(world, squadron, units=3)
    assert world.transfers.pending_transfers == []
    assert world.coalition.ato.packages == []
    _base(squadron.location).commit_losses.assert_not_called()


def test_helicopter_transport_needs_a_ctld_capable_destination(
    world: _World,
) -> None:
    squadron = world.squadron(_control_point("Origin"), dcs_type=UH_1H)
    ship = MagicMock(name="ship")
    ship.name = "CVN-74"
    ship.position = Point(1000, 0, None)  # type: ignore[arg-type]
    ship.can_operate.return_value = True
    transfer = TransferOrder(squadron.location, ship, {MagicMock(): 1})

    problem = player_airlift_problem(squadron, transfer, ship) or ""
    assert "Transport missions are unavailable" in problem
    with pytest.raises(PlayerAirliftError):
        world.transfers.new_player_airlift(transfer, squadron, NOW)


def test_ai_transfer_flights_are_not_player_transport_missions(
    world: _World,
) -> None:
    _, flight = _transfer_flight(world, world.squadron(_control_point("Home")))
    assert world.transfers.player_airlift_for(flight) is None


def test_deleted_transport_mission_returns_the_cargo_to_its_origin(
    world: _World,
) -> None:
    squadron = world.squadron(_control_point("Origin"), dcs_type=C_130)
    transfer, package = _player_mission(world, squadron, units=2)
    [flight] = package.flights
    units = dict(transfer.units)

    # What the ATO models do when the player deletes the flight.
    mission = world.transfers.player_airlift_for(flight)
    package.remove_flight(flight)
    assert mission is transfer
    world.transfers.cancel_transfer(mission)

    assert transfer not in world.transfers.pending_transfers
    _base(transfer.origin).commission_units.assert_called_once_with(units)


def test_old_saves_load_transfers_as_not_player_requested() -> None:
    transfer = TransferOrder(_control_point("A"), _control_point("B"), {})
    del transfer.__dict__["player_requested"]
    assert transfer.player_requested is False


def test_kneeboard_lists_zones_cargo_and_time_slot() -> None:
    def base(name: str) -> MagicMock:
        cp = MagicMock()
        cp.name = name
        cp.position.latlng.return_value.format_dms.return_value = f"{name} LL"
        return cp

    def waypoint(kind: FlightWaypointType, tot: datetime | None) -> Any:
        position = MagicMock()
        position.latlng.return_value.format_dms.return_value = f"{kind.name} LL"
        return SimpleNamespace(waypoint_type=kind, position=position, tot=tot)

    tank, apc = MagicMock(), MagicMock()
    tank.display_name, apc.display_name = "M1A2", "M113"
    origin, destination = base("Origin"), base("Destination")
    cargo = SimpleNamespace(
        origin=origin,
        destination=destination,
        transport=SimpleNamespace(destination=destination),
        units={tank: 1, apc: 2},
    )
    flight = SimpleNamespace(
        cargo=cargo,
        departure_delay=timedelta(minutes=5),
        waypoints=[
            waypoint(FlightWaypointType.TAKEOFF, None),
            waypoint(FlightWaypointType.PICKUP_ZONE, datetime(2026, 1, 1, 12, 10)),
            waypoint(FlightWaypointType.DROPOFF_ZONE, datetime(2026, 1, 1, 12, 40)),
        ],
    )
    page = TransportTaskPage(cast(Any, flight), datetime(2026, 1, 1, 12), False)

    assert page.stop_rows() == [
        ["Pickup", "1", "Origin CTLD zone", "PICKUP_ZONE LL", "12:10:00"],
        ["Drop-off", "2", "Destination CTLD zone", "DROPOFF_ZONE LL", "12:40:00"],
    ]
    assert page.cargo_rows() == [["M113", "2"], ["M1A2", "1"]]
    assert page.departure_time() == "12:05:00"

    # Fixed-wing transports have no CTLD zone waypoints: the bases are listed.
    flight.waypoints = []
    assert page.stop_rows()[1] == ["Drop-off", "", "Destination", "Destination LL", ""]

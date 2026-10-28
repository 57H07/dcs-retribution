"""Air logistics and base resupply (TRN-03, #32)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator, cast
from unittest.mock import MagicMock

import pytest
from dcs import Point
from dcs.helicopters import UH_1H
from dcs.planes import C_130

import game.ato.flightplans.airlift as airlift
from game import persistency
from game.ato.airtaaskingorder import AirTaskingOrder
from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.package import Package
from game.db.database import Database
from game.dcs.aircrafttype import AircraftType
from game.dcs.countries import country_with_name
from game.logistics import (
    LogisticsPlanner,
    base_is_cut_off,
    is_cut_off,
    plan_logistics,
)
from game.settings import AutoAtoBehavior, Settings
from game.squadrons import Squadron
from game.squadrons.airwing import AirWing
from game.squadrons.operatingbases import OperatingBases
from game.theater.base import Base
from game.theater.controlpoint import Airfield, ControlPointType, Fob
from game.theater.player import Player
from game.theater.transitnetwork import TransitNetwork
from game.transfers import PendingTransfers, TransferOrder, airlift_compatible
from game.utils import feet, nautical_miles

NOW = datetime(2026, 1, 1, 12)


@pytest.fixture(autouse=True)
def _no_flight_plans(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Default loadouts read the saved-games folder; point it at a throwaway dir.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16884)
    # Routing needs a theater; these tests are about the logistics decisions.
    monkeypatch.setattr(Flight, "recreate_flight_plan", lambda self: None)
    monkeypatch.setattr(Package, "set_tot_asap", lambda self, now: None)


def _tank(name: str) -> MagicMock:
    tank = MagicMock(name=name)
    tank.display_name = name
    return tank


TANK = _tank("M1A2")


def _cp(
    name: str,
    x_nm: float,
    fob: bool = False,
    front_line: bool = False,
    armor: int = 0,
) -> MagicMock:
    """A friendly base. FOBs host helicopters only."""
    cp = MagicMock(spec=Fob if fob else Airfield)
    cp.name = name
    cp.__str__.return_value = name  # type: ignore[attr-defined]
    cp.cptype = ControlPointType.FOB if fob else ControlPointType.AIRBASE
    cp.captured = Player.BLUE
    cp.position = Point(nautical_miles(x_nm).meters, 0, None)  # type: ignore[arg-type]
    cp.is_friendly.side_effect = lambda player: player == Player.BLUE
    cp.is_fleet = False
    cp.is_fob = fob
    cp.can_deploy_ground_units = True
    cp.has_active_frontline = front_line
    cp.frontline_unit_count_limit = 8
    cp.ctld_zones = [(cp.position, 100.0)]
    cp.unclaimed_parking.return_value = 100
    cp.required_aircraft_start_type = None
    if fob:
        cp.can_operate.side_effect = lambda a: a.dcs_unit_type.helicopter
    else:
        cp.can_operate.return_value = True
    cp.base = Base()
    if armor:
        cp.base.armor[TANK] = armor
    return cp


class _World:
    """The slice of a Game the logistics planner uses."""

    def __init__(self, bases: list[MagicMock], network: TransitNetwork) -> None:
        self.settings = Settings()
        self.settings.plan_logistics_missions = True
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
        self.game.transit_network_for.return_value = network
        self.game.theater.control_points_for.side_effect = lambda player: iter(bases)
        self.coalition.transfers = PendingTransfers(self.game, Player.BLUE)
        for cp in bases:
            cp.coalition = self.coalition

    @property
    def transfers(self) -> PendingTransfers:
        return self.coalition.transfers

    def transit_network_for(self, player: Player) -> TransitNetwork:
        return self.game.transit_network_for(player)

    def squadron(
        self, location: MagicMock, dcs_type: Any, aircraft_count: int = 4
    ) -> Squadron:
        aircraft = next(AircraftType.for_dcs_type(dcs_type))
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
            auto_assignable_mission_types=set(aircraft.iter_task_capabilities()),
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

    def flights(self) -> Iterator[Flight]:
        for package in self.coalition.ato.packages:
            yield from package.flights


def _campaign() -> tuple[_World, MagicMock, MagicMock, MagicMock]:
    """A rear airfield with reserves, a front-line airfield linked to it by road,
    and a FOB 150 NM away (beyond helicopter range) with no road.

    Both airfields host a UH-1H and a C-130 squadron.
    """
    rear = _cp("Rear", 0, armor=12)
    front = _cp("Front", 40, front_line=True, armor=6)
    fob = _cp("Remote FOB", 150, fob=True)
    network = TransitNetwork()
    network.link_road(rear, front)
    network.link_airport(rear, fob)
    network.link_airport(front, fob)
    world = _World([rear, front, fob], network)
    for base in (rear, front):
        world.squadron(base, UH_1H)
        world.squadron(base, C_130)
    return world, rear, front, fob


def test_no_logistics_flight_is_planned_by_default() -> None:
    world, *_ = _campaign()
    world.settings.plan_logistics_missions = Settings().plan_logistics_missions
    assert world.settings.plan_logistics_missions is False

    assert plan_logistics(world.game, Player.BLUE, NOW) == []
    assert not world.coalition.ato.packages
    assert not world.transfers.pending_transfers


def test_a_fob_without_road_gets_a_c130_resupply_flight() -> None:
    world, rear, _, fob = _campaign()

    packages = plan_logistics(world.game, Player.BLUE, NOW)

    to_fob = [p for p in packages if p.target is fob]
    assert len(to_fob) == 1
    [flight] = to_fob[0].flights
    assert flight.flight_type is FlightType.TRANSPORT
    assert flight.unit_type.dcs_unit_type is C_130
    transfer = flight.cargo
    assert transfer is not None
    assert transfer.origin is rear and transfer.destination is fob
    assert transfer.next_stop is fob
    assert transfer in world.transfers.pending_transfers
    # An ordinary airlift: mission generation and the player find its cargo.
    assert world.transfers.transfer_for_flight(flight) is transfer
    # The units leave the reserve now and are delivered at turn end.
    shipped = sum(t.size for t in world.transfers.pending_transfers)
    assert rear.base.total_armor == 12 - shipped
    size = transfer.size
    world.transfers.perform_transfers()
    assert fob.base.total_armor == size


def test_bases_without_road_are_resupplied_first() -> None:
    world, _, front, fob = _campaign()
    planner = LogisticsPlanner(world.game, Player.BLUE)

    targets = [t.base for t in planner.resupply_targets()]

    # The front-line airfield is short of units too, but it has a road.
    assert targets == [fob, front]


def test_helicopters_are_used_within_their_range() -> None:
    world, rear, front, fob = _campaign()
    fob.position = Point(nautical_miles(60).meters, 0, None)  # type: ignore[arg-type]

    packages = plan_logistics(world.game, Player.BLUE, NOW)

    [flight] = [p for p in packages if p.target is fob][0].flights
    assert flight.unit_type.dcs_unit_type is UH_1H


def test_fleet_share_caps_logistics_aircraft() -> None:
    world, *_ = _campaign()
    world.settings.logistics_transport_fleet_share = 25  # 25 % of 16 aircraft.

    plan_logistics(world.game, Player.BLUE, NOW)

    assert sum(f.count for f in world.flights()) <= 4

    world, *_ = _campaign()
    world.settings.logistics_transport_fleet_share = 0
    assert plan_logistics(world.game, Player.BLUE, NOW) == []


def test_no_flight_without_reserves() -> None:
    world, rear, *_ = _campaign()
    rear.base.armor.clear()
    assert plan_logistics(world.game, Player.BLUE, NOW) == []


def test_player_hq_follows_the_auto_planner_switch() -> None:
    world, *_ = _campaign()
    world.settings.auto_ato_behavior = AutoAtoBehavior.Disabled
    assert plan_logistics(world.game, Player.BLUE, NOW) == []


def test_resupply_never_exceeds_the_base_need() -> None:
    world, rear, front, fob = _campaign()
    # 6 units already on their way to the FOB.
    world.transfers.pending_transfers.append(TransferOrder(rear, fob, {TANK: 6}))

    plan_logistics(world.game, Player.BLUE, NOW)

    to_fob = [f for f in world.flights() if f.package.target is fob]
    assert [f.cargo.size for f in to_fob if f.cargo] == [2]


def test_airdrop_is_only_allowed_when_asked() -> None:
    world, rear, _, fob = _campaign()
    c130 = next(AircraftType.for_dcs_type(C_130))
    transfer = TransferOrder(rear, fob, {TANK: 1})
    # Default transfers keep refusing a cargo plane where it cannot land.
    assert not airlift_compatible(c130, rear, transfer, fob)
    assert airlift_compatible(c130, rear, transfer, fob, allow_airdrop=True)


def test_cut_off_bases() -> None:
    world, rear, front, fob = _campaign()
    isolated = _cp("Isolated FOB", 300, fob=True)
    network = world.game.transit_network_for(Player.BLUE)

    assert is_cut_off(isolated, network)
    assert not any(is_cut_off(cp, network) for cp in (rear, front, fob))
    # Checking does not add the base to the network.
    assert isolated not in network.nodes

    isolated.coalition = world.coalition
    assert base_is_cut_off(isolated)
    world.settings.plan_logistics_missions = False
    assert not base_is_cut_off(isolated)


# --- Flight plan -----------------------------------------------------------------


def test_airdrop_waypoint() -> None:
    fob = _cp("Remote FOB", 150, fob=True)
    waypoint = WaypointBuilder.airdrop(fob)
    assert waypoint.waypoint_type is FlightWaypointType.NAV
    assert waypoint.alt == feet(1000) and waypoint.alt_type == "RADIO"
    assert waypoint.flyover and waypoint.control_point is fob


class _FakeWaypointBuilder:
    def __init__(self, flight: Any) -> None:
        self.get_cruise_altitude = feet(10000)

    @staticmethod
    def _wp(name: str, position: Point | None = None) -> SimpleNamespace:
        return SimpleNamespace(name=name, position=position)

    def cargo_stop(self, cp: Any) -> SimpleNamespace:
        return self._wp("CARGOSTOP", cp.position)

    def airdrop(self, cp: Any) -> SimpleNamespace:
        return self._wp("AIRDROP", cp.position)

    def nav(self, position: Point, alt: Any, agl: bool) -> SimpleNamespace:
        return self._wp("NAV", position)

    def nav_path(self, *args: Any) -> list[SimpleNamespace]:
        return []

    def takeoff(self, cp: Any) -> SimpleNamespace:
        return self._wp("TAKEOFF", cp.position)

    def land(self, cp: Any) -> SimpleNamespace:
        return self._wp("LAND", cp.position)

    def divert(self, cp: Any) -> None:
        return None

    def bullseye(self) -> SimpleNamespace:
        return self._wp("BULLSEYE")


def _drop_off(
    monkeypatch: pytest.MonkeyPatch, dcs_type: Any, destination: MagicMock
) -> Any:
    monkeypatch.setattr(airlift, "WaypointBuilder", _FakeWaypointBuilder)
    home = _cp("Home", 0)
    cargo = SimpleNamespace(origin=home, next_stop=destination)
    aircraft = next(AircraftType.for_dcs_type(dcs_type))
    flight = SimpleNamespace(
        cargo=cargo,
        departure=home,
        arrival=home,
        divert=None,
        unit_type=aircraft,
        is_helo=aircraft.dcs_unit_type.helicopter,
    )
    builder = object.__new__(airlift.Builder)
    builder.flight = cast(Any, flight)
    return builder.layout().drop_off


def test_cargo_plane_airdrops_where_it_cannot_land(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    drop_off = _drop_off(monkeypatch, C_130, _cp("Remote FOB", 150, fob=True))
    assert drop_off.name == "AIRDROP"


def test_cargo_plane_still_lands_at_airfields(monkeypatch: pytest.MonkeyPatch) -> None:
    drop_off = _drop_off(monkeypatch, C_130, _cp("Front", 40))
    assert drop_off.name == "CARGOSTOP"

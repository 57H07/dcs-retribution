"""BUG-04: an aircraft must never be spawned on an occupied parking position.

An airfield offers two kinds of parking: DCS parking slots (from pydcs) and
campaign helipads / ground spawns. These tests check that the two reserve
each other, and that a shortage of pads never leaves stacked aircraft behind.
"""

import itertools
from typing import Any, Optional, Type
from unittest.mock import MagicMock

import pytest
from dcs import Mission, Point
from dcs.helicopters import UH_1H
from dcs.planes import A_10C
from dcs.terrain import Caucasus, NoParkingSlotError, ParkingSlot
from dcs.terrain.terrain import Airport
from dcs.unit import InvisibleFARP
from dcs.unitgroup import FlyingGroup, StaticGroup
from dcs.unittype import FlyingType

from game.ato.starttype import StartType
from game.missiongenerator.aircraft.flightgroupspawner import (
    FlightGroupSpawner,
    aircraft_half_extent,
)
from game.missiongenerator.missiondata import MissionData
from game.theater import Airfield, Fob


class SpawnContext:
    def __init__(self, cp_type: type = Airfield) -> None:
        self.mission = Mission(Caucasus())
        self.country = self.mission.country("USA")
        self.airport: Airport = self.mission.terrain.airports["Senaki-Kolkhi"]
        self.cp: Any = MagicMock(spec=cp_type)
        self.cp.name = "Test base"
        self.cp.airport = self.airport
        self.cp.dcs_airport = self.airport
        self.cp.coalition.game.theater.terrain = self.mission.terrain
        settings = self.cp.coalition.game.settings
        settings.ground_start_airbase_statics_farps_remove = False
        self.helipads: dict[Any, list[StaticGroup]] = {self.cp: []}
        self.ground_spawns: dict[Any, list[tuple[StaticGroup, Point]]] = {self.cp: []}
        self.ground_spawns_roadbase: dict[Any, list[tuple[StaticGroup, Point]]] = {
            self.cp: []
        }
        self.ground_spawns_large: dict[Any, list[tuple[StaticGroup, Point]]] = {
            self.cp: []
        }
        self.mission_data = MissionData()
        self._names = itertools.count()

    def pad(self, position: Point) -> StaticGroup:
        unit_id = self.mission.next_unit_id()
        pad = InvisibleFARP(unit_id=unit_id, terrain=self.mission.terrain)
        pad.position = Point(position.x, position.y, self.mission.terrain)
        group = StaticGroup(self.mission.next_group_id(), f"pad {unit_id}")
        group.add_unit(pad)
        return group

    def add_helipad_on(self, slot: ParkingSlot) -> StaticGroup:
        pad = self.pad(slot.position)
        self.helipads[self.cp].append(pad)
        return pad

    def spawner(self, aircraft: Type[FlyingType], count: int = 1) -> FlightGroupSpawner:
        flight: Any = MagicMock()
        flight.unit_type.dcs_unit_type = aircraft
        flight.count = count
        flight.callsign = None
        flight.state.spawn_type = StartType.COLD
        flight.arrival = self.cp
        return FlightGroupSpawner(
            flight,
            self.country,
            self.mission,
            self.helipads,
            self.ground_spawns_roadbase,
            self.ground_spawns_large,
            self.ground_spawns,
            self.mission_data,
        )

    def name(self) -> str:
        return f"flight {next(self._names)}"

    def heli_slots(self) -> list[ParkingSlot]:
        return self.airport.free_parking_slots(UH_1H)

    def aircraft_groups(self) -> list[FlyingGroup[Any]]:
        return [*self.country.helicopter_group, *self.country.plane_group]


def assert_no_overlap(
    pad_groups: list[FlyingGroup[Any]], slot_groups: list[FlyingGroup[Any]]
) -> None:
    for pad_group in pad_groups:
        for slot_group in slot_groups:
            for a in pad_group.units:
                for b in slot_group.units:
                    clearance = aircraft_half_extent(
                        a.unit_type
                    ) + aircraft_half_extent(b.unit_type)
                    distance = a.position.distance_to_point(b.position)
                    assert distance >= clearance, (
                        f"{a.name} (pad) and {b.name} (slot {b.parking_id}) are "
                        f"{distance:.1f} m apart, clearance is {clearance:.1f} m"
                    )


def test_helipad_spawn_blocks_overlapping_slots_on_a_saturated_base() -> None:
    ctx = SpawnContext()
    # Campaign helipads drawn right on top of DCS slots (as at Olf Orote).
    for slot in ctx.heli_slots()[:4]:
        ctx.add_helipad_on(slot)

    pad_groups = []
    for _ in range(2):
        group = ctx.spawner(UH_1H, count=2)._generate_at_cp_helipad(ctx.name(), ctx.cp)
        assert group is not None
        assert all(unit.parking is None for unit in group.units)
        pad_groups.append(group)

    # Saturate the base with parked aircraft until DCS runs out of slots.
    slot_groups = []
    for aircraft in (UH_1H, A_10C):
        while True:
            try:
                slot_groups.append(
                    ctx.spawner(aircraft)._generate_at_airfield(ctx.name(), ctx.cp)
                )
            except NoParkingSlotError:
                break
    assert slot_groups

    assert_no_overlap(pad_groups, slot_groups)


def test_occupied_slot_disqualifies_the_helipad_drawn_on_it() -> None:
    ctx = SpawnContext()
    slot_a, slot_b = ctx.heli_slots()[:2]
    pad_b = ctx.add_helipad_on(slot_b)
    ctx.add_helipad_on(slot_a)  # last in the list, so it would be used first

    parked = ctx.spawner(UH_1H)._generate_at_airfield(
        ctx.name(), ctx.cp, parking_slots=[slot_a]
    )

    group = ctx.spawner(UH_1H)._generate_at_cp_helipad(ctx.name(), ctx.cp)

    assert group is not None
    assert group.points[0].helipad_id == pad_b.units[0].id
    assert_no_overlap([group], [parked])


def test_helipad_shortage_falls_back_to_parking_without_leftover_group() -> None:
    ctx = SpawnContext()
    ctx.add_helipad_on(ctx.heli_slots()[0])

    group = ctx.spawner(UH_1H, count=2)._generate_at_cp_helipad(ctx.name(), ctx.cp)

    assert group is not None
    assert ctx.aircraft_groups() == [group]
    assert all(unit.parking is not None for unit in group.units)
    # The unused helipad is still available to someone else.
    assert len(ctx.helipads[ctx.cp]) == 1


def test_helipad_shortage_at_fob_leaves_no_group() -> None:
    ctx = SpawnContext(cp_type=Fob)
    ctx.add_helipad_on(ctx.heli_slots()[0])

    group = ctx.spawner(UH_1H, count=2)._generate_at_cp_helipad(ctx.name(), ctx.cp)

    assert group is None
    assert ctx.aircraft_groups() == []
    assert len(ctx.helipads[ctx.cp]) == 1


@pytest.mark.parametrize("available", [1, 2])
def test_ground_spawn_shortage_never_stacks_aircraft(available: int) -> None:
    ctx = SpawnContext(cp_type=Fob)
    origin = ctx.airport.position
    for i in range(available):
        position = Point(origin.x + 100 * i, origin.y, ctx.mission.terrain)
        ctx.ground_spawns[ctx.cp].append((ctx.pad(position), position))

    group: Optional[FlyingGroup[Any]] = ctx.spawner(
        A_10C, count=2
    )._generate_at_cp_ground_spawn(ctx.name(), ctx.cp)

    if available < 2:
        assert group is None
        assert ctx.aircraft_groups() == []
        assert len(ctx.ground_spawns[ctx.cp]) == available
    else:
        assert group is not None
        lead, wingman = group.units
        assert lead.position.distance_to_point(wingman.position) >= 100
        assert ctx.ground_spawns[ctx.cp] == []

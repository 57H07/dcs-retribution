import logging
import random
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from dcs import Mission
from dcs.country import Country
from dcs.mapping import Vector2, Point
from dcs.mission import StartType as DcsStartType
from dcs.planes import (
    F_14A,
    F_14A_135_GR,
    F_14B,
    F_5E_3,
    F_86F_Sabre,
    C_101CC,
    Su_33,
    MiG_15bis,
    M_2000C,
)
from dcs.point import PointAction
from dcs.ships import KUZNECOW
from dcs.terrain import NoParkingSlotError, Sinai, ParkingSlot
from dcs.terrain.sinai.airports import Nevatim, Ramon_Airbase
from dcs.unitgroup import (
    FlyingGroup,
    ShipGroup,
    StaticGroup,
    HelicopterGroup,
    PlaneGroup,
)
from dcs.unittype import FlyingType

from game.ato import Flight
from game.ato.flightstate import InFlight
from game.ato.starttype import StartType
from game.ato.traveltime import GroundSpeed
from game.missiongenerator.missiondata import MissionData
from game.naming import namegen
from game.theater import Airfield, ControlPoint, Fob, NavalControlPoint, OffMapSpawn
from game.utils import feet, meters
from pydcs_extensions import A_4E_C, VSN_F4B, VSN_F4C

WARM_START_HELI_ALT = meters(500)
WARM_START_ALTITUDE = meters(3000)

# In-flight spawns are MSL for the first waypoint (this can maybe be changed to AGL, but
# AGL waypoints have different piloting behavior, so we need to check whether that's
# safe to do first), so spawn them high enough that they're unlikely to be near (or
# under) the ground, or any nearby obstacles. The highest airfield in DCS is Kerman in
# PG at 5700ft. This could still be too low if there are tall obstacles near the
# airfield, but the lowest we can push this the better to avoid spawning helicopters
# well above the altitude for WP1.
MINIMUM_MID_MISSION_SPAWN_ALTITUDE_MSL = feet(6000)
MINIMUM_MID_MISSION_SPAWN_ALTITUDE_AGL = feet(500)

STACK_SEPARATION = feet(200)

RTB_ALTITUDE = meters(800)
RTB_DISTANCE = 5000
HELI_ALT = 500

# Half-size, in meters, assumed for a DCS parking slot whose dimensions pydcs does
# not know (terrains with version 1 parking data).
DEFAULT_PARKING_SLOT_HALF_EXTENT = 10.0

SpawnPoint = TypeVar("SpawnPoint")


def aircraft_half_extent(unit_type: Type[FlyingType]) -> float:
    """Radius of the circle that holds the aircraft (wingspan or rotor)."""
    return max(unit_type.width, unit_type.length) / 2


def parking_slot_half_extent(slot: ParkingSlot) -> float:
    """Radius of the circle that holds the largest aircraft the slot accepts."""
    if slot.width is None and slot.length is None:
        return DEFAULT_PARKING_SLOT_HALF_EXTENT
    return max(slot.width or 0, slot.length or 0) / 2


class FlightGroupSpawner:
    def __init__(
        self,
        flight: Flight,
        country: Country,
        mission: Mission,
        helipads: dict[ControlPoint, list[StaticGroup]],
        ground_spawns_roadbase: dict[ControlPoint, list[Tuple[StaticGroup, Point]]],
        ground_spawns_large: dict[ControlPoint, list[Tuple[StaticGroup, Point]]],
        ground_spawns: dict[ControlPoint, list[Tuple[StaticGroup, Point]]],
        mission_data: MissionData,
    ) -> None:
        self.flight = flight
        self.country = country
        self.mission = mission
        self.helipads = helipads
        self.ground_spawns_roadbase = ground_spawns_roadbase
        self.ground_spawns_large = ground_spawns_large
        self.ground_spawns = ground_spawns
        self.mission_data = mission_data

    def create_flight_group(self) -> FlyingGroup[Any]:
        """Creates the group for the flight and adds it to the mission.

        Each flight is spawned according to its FlightState at the time of mission
        generation. Aircraft that are WaitingForStart will be set up based on their
        StartType with a delay. Note that delays are actually created during waypoint
        generation.

        Aircraft that are *not* WaitingForStart will be spawned in their current state.
        We cannot spawn aircraft mid-taxi, so when the simulated state is near the end
        of a long taxi period the aircraft will be spawned in their parking spot. This
        could lead to problems but that's what loiter points are for. The other pre-
        flight states have the same problem but are much shorter and more easily covered
        by the loiter time. Player flights that are spawned near the end of their cold
        start have the biggest problem but players are able to cut corners to make up
        for lost time.

        Aircraft that are already in the air will be spawned at their estimated
        location, speed, and altitude based on their flight plan.
        """
        if (
            self.flight.state.is_waiting_for_start
            or self.flight.state.spawn_type is not StartType.IN_FLIGHT
        ):
            grp = self.generate_flight_at_departure()
            self.flight.group_id = grp.id
            return grp
        grp = self.generate_mid_mission()
        self.flight.group_id = grp.id
        return grp

    def create_idle_aircraft(self) -> Optional[FlyingGroup[Any]]:
        group = None
        cp = self.flight.squadron.location
        if self.flight.is_helo or self.flight.is_lha and isinstance(cp, Fob):
            group = self._generate_at_cp_helipad(
                name=namegen.next_aircraft_name(self.country, self.flight),
                cp=self.flight.squadron.location,
            )
        elif isinstance(cp, Fob):
            group = self._generate_at_cp_ground_spawn(
                name=namegen.next_aircraft_name(self.country, self.flight),
                cp=self.flight.squadron.location,
            )
        elif isinstance(cp, Airfield):
            # TODO: remove hack when fixed in DCS
            slots = None
            if self._check_nevatim_hack(cp):
                ac_type = self.flight.unit_type.dcs_unit_type
                slots = [
                    slot
                    for slot in cp.dcs_airport.free_parking_slots(ac_type)
                    if slot.slot_name in [str(n) for n in range(55, 66)]
                ]
            elif self._check_ramon_airbase_hack(cp):
                ac_type = self.flight.unit_type.dcs_unit_type
                slots = [
                    slot
                    for slot in cp.dcs_airport.free_parking_slots(ac_type)
                    if slot.slot_name
                    not in [
                        str(n) for n in [1, 2, 3, 4, 5, 6, 13, 14, 15, 16, 17, 18, 61]
                    ]
                ]
            group = self._generate_at_airfield(
                name=namegen.next_aircraft_name(self.country, self.flight),
                airfield=cp,
                parking_slots=slots,
            )
        if group:
            group.uncontrolled = True
        return group

    @property
    def start_type(self) -> StartType:
        return self.flight.state.spawn_type

    def generate_flight_at_departure(self) -> FlyingGroup[Any]:
        name = namegen.next_aircraft_name(self.country, self.flight)
        cp = self.flight.departure
        try:
            if self.start_type is StartType.IN_FLIGHT:
                group = self._generate_over_departure(name, cp)
                return group
            elif isinstance(cp, NavalControlPoint):
                group_name = cp.get_carrier_group_name()
                carrier_group = self.mission.find_group(group_name)
                if not isinstance(carrier_group, ShipGroup):
                    raise RuntimeError(
                        f"Carrier group {carrier_group} is a "
                        f"{carrier_group.__class__.__name__}, expected a ShipGroup"
                    )
                return self._generate_at_group(name, carrier_group)
            elif isinstance(cp, Fob):
                is_heli = self.flight.squadron.aircraft.helicopter
                is_vtol = not is_heli and self.flight.squadron.aircraft.lha_capable
                if not is_heli and not is_vtol and not cp.has_ground_spawns:
                    raise RuntimeError(
                        f"Cannot spawn fixed-wing aircraft at {cp} because of insufficient ground spawn slots."
                    )
                is_large = self.flight.unit_type.dcs_unit_type.width > 40

                pilot_count = len(self.flight.roster.members)
                if (
                    not is_heli
                    and self.flight.roster.player_count != pilot_count
                    and not self.flight.coalition.game.settings.ground_start_ai_planes
                ):
                    raise RuntimeError(
                        f"Fixed-wing aircraft at {cp} must be piloted by humans exclusively because"
                        f' the "AI fixed-wing aircraft can use roadbases / bases with only ground'
                        f' spawns" setting is currently disabled.'
                    )
                if cp.has_helipads and (is_heli or is_vtol):
                    pad_group = self._generate_at_cp_helipad(name, cp)
                    if pad_group is not None:
                        return pad_group
                if cp.has_ground_spawns and self.flight.client_count > 0 and is_large:
                    pad_group = self._generate_at_cp_ground_spawn(name, cp, is_large)
                    if pad_group is not None:
                        return pad_group
                if cp.has_ground_spawns and (self.flight.client_count > 0 or is_heli):
                    pad_group = self._generate_at_cp_ground_spawn(name, cp)
                    if pad_group is not None:
                        return pad_group
                    else:
                        pad_group = self._generate_at_cp_ground_spawn(name, cp, True)
                        if pad_group is not None:
                            return pad_group
                return self._generate_over_departure(name, cp)
            elif isinstance(cp, Airfield):
                is_heli = self.flight.squadron.aircraft.helicopter
                if cp.has_helipads and is_heli:
                    pad_group = self._generate_at_cp_helipad(name, cp)
                    if pad_group is not None:
                        return pad_group
                # Large planes (wingspan more than 40 meters, looking at you, C-130)
                # First try spawning on large ground spawns
                # Then try the regular airfield ramp spawns
                is_large = self.flight.unit_type.dcs_unit_type.width > 40
                if (
                    cp.has_ground_spawns
                    and is_large
                    and len(self.ground_spawns_large[cp]) >= self.flight.count
                    and (self.flight.client_count > 0)
                ):
                    pad_group = self._generate_at_cp_ground_spawn(name, cp, is_large)
                    if pad_group is not None:
                        return pad_group
                # Below 40 meter wingspan aircraft
                # First try spawning on regular or roadbase ground spawns
                # Then try the regular airfield ramp spawns
                # Then, if both of the above fail, use the large ground spawns
                if (
                    cp.has_ground_spawns
                    and len(self.ground_spawns[cp])
                    + len(self.ground_spawns_roadbase[cp])
                    + len(self.ground_spawns_large[cp])
                    >= self.flight.count
                    and (self.flight.client_count > 0 or is_heli)
                ):
                    pad_group = self._generate_at_cp_ground_spawn(name, cp)
                    if pad_group is not None:
                        return pad_group

                if (
                    cp.has_ground_spawns
                    and len(self.ground_spawns[cp])
                    + len(self.ground_spawns_roadbase[cp])
                    >= self.flight.count
                    and (self.flight.client_count > 0 or is_heli)
                ):
                    pad_group = self._generate_at_cp_ground_spawn(name, cp)
                    if pad_group is not None:
                        return pad_group
                try:
                    # TODO: get rid of the nevatim hack once fixed in DCS...
                    if self._check_nevatim_hack(cp):
                        slots = [
                            slot
                            for slot in cp.dcs_airport.free_parking_slots(
                                self.flight.squadron.aircraft.dcs_unit_type
                            )
                            if slot.slot_name in [str(n) for n in range(55, 66)]
                        ]
                        return self._generate_at_airfield(name, cp, slots)
                    elif self._check_ramon_airbase_hack(cp):
                        # TODO: get rid of the ramon airbase hack once fixed in DCS...
                        slots = [
                            slot
                            for slot in cp.dcs_airport.free_parking_slots(
                                self.flight.squadron.aircraft.dcs_unit_type
                            )
                            if slot.slot_name
                            not in [
                                str(n)
                                for n in [1, 2, 3, 4, 5, 6, 13, 14, 15, 16, 17, 18, 61]
                            ]
                        ]
                        return self._generate_at_airfield(name, cp, slots)
                    else:
                        return self._generate_at_airfield(name, cp)
                except NoParkingSlotError:
                    if (
                        cp.has_ground_spawns
                        and len(self.ground_spawns_large[cp]) >= self.flight.count
                        and (self.flight.client_count > 0 or is_heli)
                    ):
                        pad_group = self._generate_at_cp_ground_spawn(name, cp, True)
                        if pad_group is not None:
                            return pad_group
                        else:
                            raise NoParkingSlotError
                return self._generate_at_airfield(name, cp)
            else:
                raise NotImplementedError(
                    f"Aircraft spawn behavior not implemented for {cp} ({cp.__class__})"
                )
        except NoParkingSlotError:
            # Generated when there is no place on Runway or on Parking Slots
            logging.warning(
                "No room on runway or parking slots. Starting from the air."
            )
            self.flight.start_type = StartType.IN_FLIGHT
            group = self._generate_over_departure(name, cp)
            return group

    def _check_nevatim_hack(self, cp: ControlPoint) -> bool:
        # TODO: get rid of the nevatim hack once fixed in DCS...
        nevatim_hack = self.flight.coalition.game.settings.nevatim_parking_fix
        nevatim_hack &= isinstance(self.mission.terrain, Sinai)
        nevatim_hack &= isinstance(cp.dcs_airport, Nevatim)
        return nevatim_hack

    def _check_ramon_airbase_hack(self, cp: ControlPoint) -> bool:
        # TODO: get rid of the ramon airbase hack once fixed in DCS...
        ramon_airbase_hack = self.flight.coalition.game.settings.nevatim_parking_fix
        ramon_airbase_hack &= isinstance(self.mission.terrain, Sinai)
        ramon_airbase_hack &= isinstance(cp.dcs_airport, Ramon_Airbase)
        return ramon_airbase_hack

    def generate_mid_mission(self) -> FlyingGroup[Any]:
        assert isinstance(self.flight.state, InFlight)
        name = namegen.next_aircraft_name(self.country, self.flight)
        speed = self.flight.state.estimate_speed()
        pos = self.flight.state.estimate_position()
        pos += Vector2(random.randint(100, 1000), random.randint(100, 1000))
        alt, alt_type = self.flight.state.estimate_altitude()
        cp = self.flight.squadron.location.id

        if cp not in self.mission_data.cp_stack:
            self.mission_data.cp_stack[cp] = MINIMUM_MID_MISSION_SPAWN_ALTITUDE_AGL

        # We don't know where the ground is, so just make sure that any aircraft
        # spawning at an MSL altitude is spawned at some minimum altitude.
        # https://github.com/dcs-liberation/dcs_liberation/issues/1941
        if alt_type == "BARO" and alt < MINIMUM_MID_MISSION_SPAWN_ALTITUDE_MSL:
            alt = MINIMUM_MID_MISSION_SPAWN_ALTITUDE_MSL

        # Set a minimum AGL value for 'alt' if needed,
        # otherwise planes might crash in trees and stuff.
        if alt_type == "RADIO" and alt < self.mission_data.cp_stack[cp]:
            alt = self.mission_data.cp_stack[cp]
            self.mission_data.cp_stack[cp] += STACK_SEPARATION

        group = self.mission.flight_group(
            country=self.country,
            name=name,
            aircraft_type=self.flight.unit_type.dcs_unit_type,
            airport=None,
            position=pos,
            altitude=alt.meters,
            speed=speed.kph,
            maintask=None,
            group_size=self.flight.count,
            callsign_name=self.flight.callsign.name if self.flight.callsign else None,
            callsign_nr=self.flight.callsign.nr if self.flight.callsign else None,
        )

        group.points[0].alt_type = alt_type
        return group

    def _generate_at_airfield(
        self,
        name: str,
        airfield: Airfield,
        parking_slots: Optional[List[ParkingSlot]] = None,
    ) -> FlyingGroup[Any]:
        # TODO: Delayed runway starts should be converted to air starts for multiplayer.
        # Runway starts do not work with late activated aircraft in multiplayer. Instead
        # of spawning on the runway the aircraft will spawn on the taxiway, potentially
        # somewhere that they don't fit anyway. We should either upgrade these to air
        # starts or (less likely) downgrade to warm starts to avoid the issue when the
        # player is generating the mission for multiplayer (which would need a new
        # option).
        self.flight.unit_type.dcs_unit_type.load_payloads()
        return self.mission.flight_group_from_airport(
            country=self.country,
            name=name,
            aircraft_type=self.flight.unit_type.dcs_unit_type,
            airport=airfield.airport,
            maintask=None,
            start_type=self._start_type_at_airfield(airfield),
            group_size=self.flight.count,
            parking_slots=parking_slots,
            callsign_name=self.flight.callsign.name if self.flight.callsign else None,
            callsign_nr=self.flight.callsign.nr if self.flight.callsign else None,
        )

    def _generate_over_departure(
        self, name: str, origin: ControlPoint
    ) -> FlyingGroup[Any]:
        at = origin.position

        alt_type = "RADIO"
        if isinstance(origin, OffMapSpawn):
            alt = self.flight.flight_plan.waypoints[0].alt
            alt_type = self.flight.flight_plan.waypoints[0].alt_type
        elif self.flight.unit_type.helicopter:
            alt = WARM_START_HELI_ALT
        else:
            if origin.id not in self.mission_data.cp_stack:
                min_alt = MINIMUM_MID_MISSION_SPAWN_ALTITUDE_AGL
                self.mission_data.cp_stack[origin.id] = min_alt
            alt = self.mission_data.cp_stack[origin.id]
            self.mission_data.cp_stack[origin.id] += STACK_SEPARATION

        speed = GroundSpeed.for_flight(self.flight, alt)
        pos = at + Vector2(random.randint(100, 1000), random.randint(100, 1000))

        group = self.mission.flight_group(
            country=self.country,
            name=name,
            aircraft_type=self.flight.unit_type.dcs_unit_type,
            airport=None,
            position=pos,
            altitude=alt.meters,
            speed=speed.kph,
            maintask=None,
            group_size=self.flight.count,
            callsign_name=self.flight.callsign.name if self.flight.callsign else None,
            callsign_nr=self.flight.callsign.nr if self.flight.callsign else None,
        )

        group.points[0].alt_type = alt_type
        return group

    def _generate_at_group(
        self, name: str, at: Union[ShipGroup, StaticGroup]
    ) -> FlyingGroup[Any]:
        return self.mission.flight_group_from_unit(
            country=self.country,
            name=name,
            aircraft_type=self.flight.unit_type.dcs_unit_type,
            pad_group=at,
            maintask=None,
            start_type=self._start_type_at_group(at),
            group_size=self.flight.count,
            callsign_name=self.flight.callsign.name if self.flight.callsign else None,
            callsign_nr=self.flight.callsign.nr if self.flight.callsign else None,
        )

    def _generate_at_cp_helipad(
        self, name: str, cp: ControlPoint
    ) -> Optional[FlyingGroup[Any]]:
        # Claim a pad for every aircraft up front: creating the group first and
        # running out of pads halfway used to leave that group in the mission,
        # its aircraft stacked 10 m apart on a single pad.
        claimed = self._claim_spawn_points(
            cp, [self.helipads[cp]], lambda pad: pad.position
        )
        if claimed is None:
            logging.warning(
                f"Not enough free helipads at {cp.name} for {self.flight.count} "
                f"{self.flight.unit_type}"
            )
            if isinstance(cp, Airfield):
                return self._generate_at_airfield(name, cp)
            return None
        helipads = [pad for _, pad in claimed]
        helipad = helipads[0]

        group = self._generate_at_group(name, helipad)

        # Note : A bit dirty, need better support in pydcs
        group.points[0].action = PointAction.FromGroundArea
        group.points[0].type = "TakeOffGround"
        group.units[0].heading = helipad.units[0].heading
        if self.start_type is not StartType.COLD:
            group.points[0].action = PointAction.FromGroundAreaHot
            group.points[0].type = "TakeOffGroundHot"

        wpt = group.waypoint("LANDING")
        if wpt:
            hpad = self.helipads[self.flight.arrival].pop(0)
            wpt.helipad_id = hpad.units[0].id
            wpt.link_unit = hpad.units[0].id
            self.helipads[self.flight.arrival].append(hpad)

        terrain = cp.coalition.game.theater.terrain
        for unit, helipad in zip(group.units[1:], helipads[1:]):
            unit.position = Point(helipad.x, helipad.y, terrain=terrain)
            unit.heading = helipad.units[0].heading
        self._block_parking_slots_under(cp, group)
        return group

    def _generate_at_cp_ground_spawn(
        self, name: str, cp: ControlPoint, is_large: bool = False
    ) -> Optional[FlyingGroup[Any]]:
        # Same preference order as before: roadbase, then regular, then large
        # spawns. A spot is claimed for every aircraft before the group exists,
        # so a shortage can no longer stack wingmen on the lead's spot.
        pools = [self.ground_spawns_large[cp]]
        if not is_large:
            pools = [
                self.ground_spawns_roadbase[cp],
                self.ground_spawns[cp],
                self.ground_spawns_large[cp],
            ]
        claimed = self._claim_spawn_points(cp, pools, lambda spawn: spawn[0].position)
        if claimed is None:
            logging.warning(
                f"Not enough free ground spawn slots at {cp.name} for "
                f"{self.flight.count} {self.flight.unit_type}"
            )
            return None
        lead_pool, ground_spawn = claimed[0]
        is_roadbase = lead_pool is self.ground_spawns_roadbase[cp]
        is_airbase = not is_roadbase

        group = self._generate_at_group(name, ground_spawn[0])

        # Note : A bit dirty, need better support in pydcs
        group.points[0].action = PointAction.FromGroundArea
        group.points[0].type = "TakeOffGround"
        group.units[0].heading = ground_spawn[0].units[0].heading

        self._remove_invisible_farps_if_requested(cp, ground_spawn[0], group)

        # Hot start aircraft which require ground power to start, when ground power
        # trucks have been disabled for performance reasons
        ground_power_available = (
            is_airbase
            and self.flight.coalition.game.settings.ground_start_ground_power_trucks
        ) or (
            is_roadbase
            and self.flight.coalition.game.settings.ground_start_ground_power_trucks_roadbase
        )

        # Also hot start aircraft which require ground crew support (ground air or chock removal)
        # which might not be available at roadbases
        if (
            self.start_type is not StartType.COLD
            or (
                not ground_power_available
                and self.flight.unit_type.dcs_unit_type
                in [
                    A_4E_C,
                    F_86F_Sabre,
                    MiG_15bis,
                    F_14A_135_GR,
                    F_14B,
                    C_101CC,
                ]
            )
            or (
                self.flight.unit_type.dcs_unit_type
                in [
                    F_5E_3,
                    M_2000C,
                    VSN_F4B,
                    VSN_F4C,
                ]
            )
        ):
            group.points[0].action = PointAction.FromGroundAreaHot
            group.points[0].type = "TakeOffGroundHot"

        try:
            cp.coalition.game.scenery_clear_zones
        except AttributeError:
            cp.coalition.game.scenery_clear_zones = []
        cp.coalition.game.scenery_clear_zones.append(ground_spawn[1])

        terrain = cp.coalition.game.theater.terrain
        for unit, (_, ground_spawn) in zip(group.units[1:], claimed[1:]):
            unit.position = Point(ground_spawn[0].x, ground_spawn[0].y, terrain=terrain)
            unit.heading = ground_spawn[0].units[0].heading
            self._remove_invisible_farps_if_requested(cp, ground_spawn[0])
        self._block_parking_slots_under(cp, group)
        return group

    def _claim_spawn_points(
        self,
        cp: ControlPoint,
        pools: list[list[SpawnPoint]],
        position_of: Callable[[SpawnPoint], Point],
    ) -> Optional[list[tuple[list[SpawnPoint], SpawnPoint]]]:
        """Takes one helipad or ground spawn per aircraft of the flight.

        Pools are searched in order, each from its end (the order the spawns
        used to be popped in). Spots overlapping an aircraft already parked on a
        DCS slot are skipped. Returns (pool, spot) pairs, or None without taking
        anything when there are not enough free spots for the whole flight.
        """
        claimed: list[tuple[list[SpawnPoint], SpawnPoint]] = []
        for pool in pools:
            for spawn_point in reversed(pool):
                if len(claimed) == self.flight.count:
                    break
                if self._is_clear_of_parked_aircraft(cp, position_of(spawn_point)):
                    claimed.append((pool, spawn_point))
        if len(claimed) < self.flight.count:
            return None
        for pool, spawn_point in claimed:
            index = next(i for i, p in enumerate(pool) if p is spawn_point)
            del pool[index]
        return claimed

    def _is_clear_of_parked_aircraft(self, cp: ControlPoint, position: Point) -> bool:
        if not isinstance(cp, Airfield):
            return True
        reach = aircraft_half_extent(self.flight.unit_type.dcs_unit_type)
        blocked = self.mission_data.parking_slots_blocked_by_ground_spawns
        for slot in cp.airport.parking_slots:
            if slot.unit_id is None or slot in blocked:
                continue
            clearance = reach + parking_slot_half_extent(slot)
            if slot.position.distance_to_point(position) < clearance:
                return False
        return True

    def _block_parking_slots_under(
        self, cp: ControlPoint, group: FlyingGroup[Any]
    ) -> None:
        """Marks the DCS slots overlapped by aircraft on helipads or ground spawns.

        pydcs only knows about its own slots, so without this an aircraft could
        later be parked on top of the ones spawned on campaign pads.
        """
        if not isinstance(cp, Airfield):
            return
        reach = aircraft_half_extent(self.flight.unit_type.dcs_unit_type)
        blocked = self.mission_data.parking_slots_blocked_by_ground_spawns
        for unit in group.units:
            for slot in cp.airport.parking_slots:
                if slot.unit_id is not None:
                    continue
                clearance = reach + parking_slot_half_extent(slot)
                if slot.position.distance_to_point(unit.position) < clearance:
                    slot.unit_id = unit.id
                    blocked.add(slot)

    def _remove_invisible_farps_if_requested(
        self,
        cp: ControlPoint,
        ground_spawn: StaticGroup,
        group: Optional[FlyingGroup[Any]] = None,
    ) -> None:
        if (
            cp.coalition.game.settings.ground_start_airbase_statics_farps_remove
            and isinstance(cp, Airfield)
        ):
            # Remove invisible FARPs from airfields because they are unnecessary
            neutral_country = self.mission.country(
                cp.coalition.game.neutral_country.name
            )
            neutral_country.remove_static_group(ground_spawn)
            if group:
                group.points[0].link_unit = None
                group.points[0].helipad_id = None

    def dcs_start_type(self) -> DcsStartType:
        if self.start_type is StartType.RUNWAY:
            return DcsStartType.Runway
        elif self.start_type is StartType.COLD:
            return DcsStartType.Cold
        elif self.start_type is StartType.WARM:
            return DcsStartType.Warm
        raise ValueError(f"There is no pydcs StartType matching {self.start_type}")

    def _start_type_at_airfield(
        self,
        airfield: Airfield,
    ) -> DcsStartType:
        return self.dcs_start_type()

    def _start_type_at_group(
        self,
        at: Union[ShipGroup, StaticGroup],
    ) -> DcsStartType:
        group_units = at.units
        # Setting Su-33s starting from the non-supercarrier Kuznetsov to take off from
        # runway to work around a DCS AI issue preventing Su-33s from taking off when
        # set to "Takeoff from ramp" (#1352)
        # Also setting the F-14A AI variant to start from cats since they are reported
        # to have severe pathfinding problems when doing ramp starts (#1927)
        if self.flight.unit_type.dcs_unit_type == F_14A or (
            self.flight.unit_type.dcs_unit_type == Su_33
            and group_units[0] is not None
            and group_units[0].type == KUZNECOW.id
        ):
            return DcsStartType.Runway
        else:
            return self.dcs_start_type()

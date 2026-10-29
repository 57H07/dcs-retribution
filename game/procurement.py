from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Iterator, List, Optional, TYPE_CHECKING, Tuple

from dcs.unittype import VehicleType

from game.config import RUNWAY_REPAIR_COST, REWARDS
from game.data.radar_db import LAUNCHER_TRACKER_PAIRS, TELARS, TRACK_RADARS
from game.data.units import UnitClass
from game.dcs.groundunittype import GroundUnitType
from game.theater import (
    ControlPoint,
    MissionTarget,
    ParkingType,
    Player,
    TheaterUnit,
)
from game.theater.grounddamage import accelerated_repair_cost, is_damage_tracked
from game.theater.repairs import begin_repair
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    EwrGroundObject,
    SamGroundObject,
    TheaterGroundObject,
)

if TYPE_CHECKING:
    from game import Game
    from game.ato import FlightType
    from game.factions.faction import Faction
    from game.squadrons import Squadron


#: Order in which the units of a damaged SAM or EWR site are repaired.
GROUND_UNIT_REPAIR_ORDER: dict[UnitClass, int] = {
    UnitClass.SEARCH_RADAR: 0,
    UnitClass.SEARCH_TRACK_RADAR: 0,
    UnitClass.TRACK_RADAR: 1,
    UnitClass.TELAR: 2,
    UnitClass.LAUNCHER: 2,
}


@dataclass(frozen=True)
class AircraftProcurementRequest:
    near: MissionTarget
    task_capability: FlightType
    number: int
    heli: bool = False

    def __str__(self) -> str:
        task = self.task_capability.value
        target = self.near.name
        return f"{self.number} ship {task} near {target} (heli={self.heli})"


class ProcurementAi:
    def __init__(
        self,
        game: Game,
        owner: Player,
        faction: Faction,
        manage_runways: bool,
        manage_front_line: bool,
        manage_aircraft: bool,
        manage_buildings: bool,
        manage_ground_objects: bool,
    ) -> None:
        self.game = game
        self.is_player = owner
        self.air_wing = game.air_wing_for(owner)
        self.faction = faction
        self.manage_runways = manage_runways
        self.manage_front_line = manage_front_line
        self.manage_aircraft = manage_aircraft
        self.manage_buildings = manage_buildings
        self.manage_ground_objects = manage_ground_objects
        self.threat_zones = self.game.threat_zone_for(self.is_player.opponent)

    def calculate_ground_unit_budget_share(self) -> float:
        armor_investment = 0
        aircraft_investment = 0

        # faction has no ground units
        if (
            len(self.faction.artillery_units) == 0
            and len(self.faction.frontline_units) == 0
        ):
            return 0

        # faction has no planes or no squadrons
        if len(self.faction.all_aircrafts) == 0 or len(self.air_wing.squadrons) == 0:
            return 1

        parking_type = ParkingType(
            fixed_wing=True, fixed_wing_stol=True, rotary_wing=True
        )

        for cp in self.owned_points:
            cp_ground_units = cp.allocated_ground_units(
                self.game.coalition_for(self.is_player).transfers
            )
            armor_investment += cp_ground_units.total_value
            cp_aircraft = cp.allocated_aircraft(parking_type)
            aircraft_investment += cp_aircraft.total_value

        balance = (
            self.game.settings.auto_procurement_balance
            if self.is_player.is_blue
            else self.game.settings.auto_procurement_balance_red
        )
        air = balance / 100.0
        ground = 1 - air
        weighted_investment = aircraft_investment * air + armor_investment * ground
        if weighted_investment == 0:
            # Turn 0 or all units were destroyed.
            return balance / 100.0

        # the more planes we have, the more ground units we want and vice versa
        ground_unit_share = aircraft_investment * air / weighted_investment
        if ground_unit_share > 1.0:
            raise ValueError

        return ground_unit_share

    def spend_budget(self, budget: float) -> float:
        if self.manage_runways:
            budget = self.repair_runways(budget)
        if self.manage_buildings:
            budget = self.repair_buildings(budget)
        if self.manage_front_line or self.manage_ground_objects:
            armor_budget = budget * self.calculate_ground_unit_budget_share()
            budget -= armor_budget
            if self.manage_ground_objects:
                armor_budget = self.repair_ground_objects(armor_budget)
            if self.manage_front_line:
                armor_budget = self.reinforce_front_line(armor_budget)
            budget += armor_budget

        if self.manage_aircraft:
            if self.game.settings.expedited_aircraft_repair:
                budget = self.repair_aircraft(budget)
            budget = self.purchase_aircraft(budget)
        if self.game.settings.ai_surplus_spending:
            budget = self.spend_surplus(budget)
        return budget

    def spend_surplus(self, budget: float) -> float:
        """Spends what the normal procurement left over the reserve.

        The normal procurement only buys aircraft for missions it could not staff
        and caps its repairs to a share of the budget, so the AI used to sit on an
        ever-growing budget. The surplus first pays for the repairs this procurement
        is allowed to make, then fills squadrons up to their maximum size.
        """
        reserve = float(self.game.settings.ai_surplus_reserve)
        surplus = budget - reserve
        if surplus <= 0:
            return budget

        settings = self.game.settings
        if self.manage_buildings:
            surplus -= self.start_repairs(self.building_repair_candidates(), surplus)
        if self.manage_ground_objects:
            surplus -= self.start_repairs(
                self.ground_object_repair_candidates(), surplus
            )
            if settings.persistent_damage_paid_ground_repair:
                surplus = self.repair_inoperative_ground_units(surplus)
        if self.manage_aircraft:
            if settings.expedited_aircraft_repair:
                surplus = self.repair_aircraft(surplus)
            surplus = self.stockpile_aircraft(surplus)
        return reserve + surplus

    def repair_inoperative_ground_units(self, budget: float) -> float:
        """Pays to end the countdown of inoperative ground units (PER-01.3).

        Units with the longest wait come first, then the cheapest.
        """
        # Imported here to avoid a circular import through game.sim.
        from game.sim.gameupdateevents import GameUpdateEvents

        candidates: list[tuple[int, int, TheaterUnit]] = []
        for control_point in self.owned_points:
            for ground_object in control_point.ground_objects:
                if not ground_object.is_friendly(self.is_player):
                    continue
                for unit in ground_object.units:
                    if not unit.inoperative or not is_damage_tracked(unit):
                        continue
                    cost = accelerated_repair_cost(unit)
                    if cost <= 0:
                        continue
                    turns = unit.inoperative_turns_remaining(self.game.turn)
                    candidates.append((turns, cost, unit))
        candidates.sort(key=lambda entry: (-entry[0], entry[1]))

        events = GameUpdateEvents()
        for _, cost, unit in candidates:
            if cost > budget:
                continue
            unit.end_inoperative(events)
            budget -= cost
        return budget

    def stockpile_aircraft(self, budget: float) -> float:
        """Buys aircraft for squadrons below their maximum size.

        Aircraft are bought one at a time, each for the squadron that needs it most,
        so the purchases spread over the air wing: squadrons away from enemy threats
        first, then squadrons able to fly the missions requested this turn, then the
        emptiest squadron, then the one closest to the enemy.
        """
        squadrons = [s for s in self.air_wing.iter_squadrons() if s.aircraft.price > 0]
        if not squadrons:
            return budget
        demand = self.requested_aircraft_by_squadron(squadrons)
        threatened = {
            s: self.threat_zones.threatened(s.location.position) for s in squadrons
        }
        enemy_distance = {
            s: self.distance_to_nearest_enemy_control_point_from(s.location)
            for s in squadrons
        }

        bought: dict[Squadron, int] = {}
        while True:
            candidates = [
                s
                for s in squadrons
                if s.aircraft.price <= budget and self.can_stockpile(s)
            ]
            if not candidates:
                break
            squadron = min(
                candidates,
                key=lambda s: (
                    threatened[s],
                    demand[s] == 0,
                    s.expected_size_next_turn / s.max_size,
                    -demand[s],
                    enemy_distance[s],
                ),
            )
            squadron.pending_deliveries += 1
            budget -= squadron.aircraft.price
            bought[squadron] = bought.get(squadron, 0) + 1

        for squadron, count in bought.items():
            logging.info(
                f"Surplus procurement: ordered {count} aircraft for {squadron}"
            )
        if bought and self.is_player.is_blue:
            total = sum(bought.values())
            self.game.message(
                f"We have ordered {total} aircraft to bring our squadrons up to "
                "strength"
            )
        return budget

    @staticmethod
    def can_stockpile(squadron: Squadron) -> bool:
        """True if the squadron can take one more aircraft next turn."""
        if squadron.destination is not None:
            # Deliveries are made at the current location, which the squadron is
            # leaving.
            return False
        if squadron.max_size <= 0:
            return False
        if squadron.expected_size_next_turn + 1 > squadron.max_size:
            return False
        if (
            squadron.pilot_limits_enabled
            and squadron.expected_size_next_turn + 1
            > squadron.expected_pilots_next_turn
        ):
            return False
        parking_type = ParkingType().from_squadron(squadron)
        return squadron.location.unclaimed_parking(parking_type) >= 1

    def requested_aircraft_by_squadron(
        self, squadrons: list[Squadron]
    ) -> dict[Squadron, int]:
        """Aircraft requested this turn for the missions each squadron can fly."""
        requests = self.game.coalition_for(self.is_player).procurement_requests
        return {
            s: sum(r.number for r in requests if s.can_auto_assign(r.task_capability))
            for s in squadrons
        }

    def distance_to_nearest_enemy_control_point_from(
        self, control_point: ControlPoint
    ) -> float:
        enemy_points = list(
            self.game.theater.control_points_for(self.is_player.opponent)
        )
        if not enemy_points:
            return math.inf
        return min(
            control_point.position.distance_to_point(cp.position) for cp in enemy_points
        )

    def repair_aircraft(self, budget: float) -> float:
        """Pays to finish aircraft maintenance at once (PER-01.2), cheapest first."""
        squadrons = sorted(
            (s for s in self.air_wing.iter_squadrons() if s.aircraft_in_maintenance),
            key=lambda s: s.expedited_repair_cost,
        )
        for squadron in squadrons:
            cost = squadron.expedited_repair_cost
            if cost > budget:
                break
            released = squadron.expedite_maintenance()
            budget -= cost
            if self.is_player.is_blue:
                self.game.message(
                    f"We have expedited the repair of {released} aircraft of "
                    f"{squadron}"
                )
        return budget

    def repair_buildings(self, budget: float) -> float:
        """Spends a share of the budget on repairing destroyed buildings.

        High-value buildings far from the enemy are repaired first.
        """
        repair_budget = budget * (
            self.game.settings.building_repair_budget_percent / 100.0
        )
        if repair_budget <= 0:
            return budget
        return budget - self.start_repairs(
            self.building_repair_candidates(), repair_budget
        )

    def building_repair_candidates(self) -> list[tuple[float, float, TheaterUnit]]:
        """Destroyed buildings not yet under repair, in repair order."""
        repair_candidates: list[tuple[float, float, TheaterUnit]] = []
        for control_point in self.owned_points:
            for ground_object in control_point.ground_objects:
                if not ground_object.is_friendly(self.is_player):
                    continue
                if not isinstance(ground_object, BuildingGroundObject):
                    continue
                cost = ground_object.repair_cost()
                if cost <= 0:
                    continue
                priority = self.building_repair_priority(ground_object)
                for unit in ground_object.statics:
                    if unit.alive or unit.repair_turns_remaining is not None:
                        continue
                    repair_candidates.append((priority, cost, unit))

        repair_candidates.sort(key=lambda entry: (-entry[0], entry[1]))
        return repair_candidates

    def start_repairs(
        self,
        candidates: list[tuple[float, float, TheaterUnit]],
        repair_budget: float,
    ) -> float:
        """Starts repairs in the given order while the budget lasts.

        Once a unit of a site cannot be afforded, the units after it at that site
        are skipped, so that a cheap unit never jumps ahead of a critical one.
        Returns the amount spent.
        """
        # Imported here to avoid a circular import through game.sim.
        from game.sim.gameupdateevents import GameUpdateEvents

        spent = 0.0
        repaired_objects: dict[int, TheaterGroundObject] = {}
        blocked_objects: set[int] = set()
        events = GameUpdateEvents()
        for _, price, unit in candidates:
            site = id(unit.ground_object)
            if site in blocked_objects:
                continue
            if repair_budget - spent < price:
                blocked_objects.add(site)
                continue
            begin_repair(self.game, unit, events)
            spent += price
            repaired_objects[site] = unit.ground_object

        for ground_object in repaired_objects.values():
            if self.is_player.is_blue:
                self.game.message(f"We have begun repairs at {ground_object.obj_name}")
            else:
                self.game.message(
                    f"OPFOR has begun repairs at {ground_object.obj_name}"
                )
        return spent

    def building_repair_priority(self, ground_object: BuildingGroundObject) -> float:
        enemy_distance = self.distance_to_nearest_enemy_control_point(ground_object)
        frontline_distance = self.distance_to_nearest_frontline(ground_object)
        if math.isfinite(enemy_distance):
            remote_score = min(enemy_distance / 20000.0, 2.0)
        else:
            remote_score = 2.0
        if math.isfinite(frontline_distance):
            ammo_frontline_score = 1.0 / (1.0 + (frontline_distance / 10000.0))
        else:
            ammo_frontline_score = 0.1

        income = REWARDS.get(ground_object.category, 0.0)
        income_score = min(income / 2.0, 2.0)
        ammo_bonus = 1.0 if ground_object.is_ammo_depot else 0.0
        factory_bonus = 1.0 if ground_object.is_factory else 0.0

        settings = self.game.settings
        return (
            remote_score * settings.building_repair_weight_remote
            + income_score * settings.building_repair_weight_income
            + ammo_frontline_score * settings.building_repair_weight_ammo_frontline
            + ammo_bonus
            + factory_bonus
        )

    def distance_to_nearest_frontline(
        self, ground_object: TheaterGroundObject
    ) -> float:
        front_lines = ground_object.control_point.front_lines.values()
        if not front_lines:
            return math.inf
        return min(
            ground_object.position.distance_to_point(front_line.position)
            for front_line in front_lines
        )

    def distance_to_nearest_enemy_control_point(
        self, ground_object: TheaterGroundObject
    ) -> float:
        enemy_points = list(
            self.game.theater.control_points_for(self.is_player.opponent)
        )
        if not enemy_points:
            return math.inf
        return min(
            ground_object.position.distance_to_point(cp.position) for cp in enemy_points
        )

    def repair_ground_objects(self, budget: float) -> float:
        """Spends a share of the ground unit budget on repairing SAM and EWR sites.

        Search radars are repaired first, then tracking radars, then launchers.
        """
        repair_budget = budget * self.game.settings.sam_repair_budget_fraction
        if repair_budget <= 0:
            return budget
        return budget - self.start_repairs(
            self.ground_object_repair_candidates(), repair_budget
        )

    def ground_object_repair_candidates(
        self,
    ) -> list[tuple[float, float, TheaterUnit]]:
        """Dead units of SAM and EWR sites not yet under repair, in repair order."""
        # (site priority, repair order inside the site, price, unit)
        repair_candidates: list[tuple[float, int, float, TheaterUnit]] = []
        for control_point in self.owned_points:
            for ground_object in control_point.ground_objects:
                if not ground_object.is_friendly(self.is_player):
                    continue
                if not isinstance(ground_object, (SamGroundObject, EwrGroundObject)):
                    continue
                priority = self.ground_object_repair_priority(ground_object)
                if priority < self.game.settings.sam_repair_priority_threshold:
                    continue
                critical_types = self.critical_unit_types_for_sam(ground_object)
                critical_dead_ids = {
                    unit.id
                    for unit in ground_object.units
                    if unit.type in critical_types
                    and not unit.alive
                    and unit.repairable
                }
                for unit in ground_object.units:
                    if unit.alive or not unit.repairable:
                        continue
                    if critical_dead_ids and unit.id not in critical_dead_ids:
                        continue
                    if unit.repair_turns_remaining is not None:
                        continue
                    if unit.unit_type is None:
                        continue
                    if unit.unit_type.price <= 0:
                        continue
                    order = GROUND_UNIT_REPAIR_ORDER.get(
                        unit.unit_type.unit_class, len(GROUND_UNIT_REPAIR_ORDER)
                    )
                    repair_candidates.append(
                        (priority, order, unit.unit_type.price, unit)
                    )

        # Highest site priority first, then repair order, then cheapest.
        repair_candidates.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))
        return [(p, price, unit) for p, _, price, unit in repair_candidates]

    def ground_object_repair_priority(
        self, ground_object: TheaterGroundObject
    ) -> float:
        threat_range = self.potential_threat_range(ground_object)
        detection_range = self.potential_detection_range(ground_object)
        range_score = max(threat_range, detection_range, 1.0) / 100000.0

        cp_coverage, frontline_distance = self.covered_control_points(ground_object)
        cp_score = min(cp_coverage / 4.0, 2.0)
        if math.isfinite(frontline_distance):
            frontline_score = 1.0 / (1.0 + (frontline_distance / 10000.0))
        else:
            frontline_score = 0.1

        tgo_count, tgo_income = self.covered_ground_objects(ground_object)
        tgo_score = min(tgo_count / 6.0, 2.0)
        income_score = min(tgo_income / 20.0, 2.0)

        settings = self.game.settings
        return (
            range_score * settings.sam_repair_weight_threat
            + frontline_score * settings.sam_repair_weight_frontline
            + cp_score * settings.sam_repair_weight_cp_coverage
            + tgo_score * settings.sam_repair_weight_tgo_coverage
            + income_score * settings.sam_repair_weight_tgo_income
        )

    @staticmethod
    def critical_unit_types_for_sam(
        ground_object: TheaterGroundObject,
    ) -> set[type]:
        types_in_site = {unit.type for unit in ground_object.units if unit.unit_type}
        required_classes: set[UnitClass] = getattr(
            ground_object, "required_unit_classes", set()
        )
        fallback_required_classes = {
            UnitClass.SEARCH_RADAR,
            UnitClass.SEARCH_TRACK_RADAR,
            UnitClass.TRACK_RADAR,
            UnitClass.LAUNCHER,
            UnitClass.TELAR,
        }
        critical = set()
        if required_classes:
            for unit in ground_object.units:
                if unit.unit_type and unit.unit_type.unit_class in required_classes:
                    critical.add(unit.type)
            for launcher, trackers in LAUNCHER_TRACKER_PAIRS.items():
                if launcher not in types_in_site:
                    continue
                for tracker in trackers:
                    if tracker not in types_in_site:
                        continue
                    if issubclass(tracker, VehicleType):
                        tracker_class = next(
                            GroundUnitType.for_dcs_type(tracker)
                        ).unit_class
                        if tracker_class in required_classes:
                            critical.add(tracker)
        else:
            for unit in ground_object.units:
                if (
                    unit.unit_type
                    and unit.unit_type.unit_class in fallback_required_classes
                ):
                    critical.add(unit.type)
            critical.update(t for t in types_in_site if t in TRACK_RADARS)
            critical.update(t for t in types_in_site if t in TELARS)
            for launcher, trackers in LAUNCHER_TRACKER_PAIRS.items():
                if launcher in types_in_site:
                    critical.update(trackers)
        return critical

    def covered_control_points(
        self, ground_object: TheaterGroundObject
    ) -> tuple[int, float]:
        threat_range = self.potential_threat_range(ground_object)
        if threat_range <= 0:
            return 0, math.inf

        covered = 0
        closest_frontline = math.inf
        for control_point in self.owned_points:
            distance = ground_object.position.distance_to_point(control_point.position)
            if distance > threat_range:
                continue
            covered += 1
            frontline_distance = self.distance_to_nearest_frontline_from_cp(
                control_point
            )
            if frontline_distance < closest_frontline:
                closest_frontline = frontline_distance

        return covered, closest_frontline

    def covered_ground_objects(
        self, ground_object: TheaterGroundObject
    ) -> tuple[int, float]:
        threat_range = self.potential_threat_range(ground_object)
        if threat_range <= 0:
            return 0, 0.0

        count = 0
        income = 0.0
        for tgo in self.game.theater.ground_objects:
            if not tgo.is_friendly(self.is_player):
                continue
            distance = ground_object.position.distance_to_point(tgo.position)
            if distance > threat_range:
                continue
            count += 1
            income += REWARDS.get(tgo.category, 0)
        return count, income

    @staticmethod
    def distance_to_nearest_frontline_from_cp(control_point: ControlPoint) -> float:
        front_lines = control_point.front_lines.values()
        if not front_lines:
            return math.inf
        return min(
            control_point.position.distance_to_point(front_line.position)
            for front_line in front_lines
        )

    @staticmethod
    def potential_threat_range(ground_object: TheaterGroundObject) -> float:
        ranges = [
            getattr(unit.type, "threat_range", 0)
            for unit in ground_object.units
            if unit.is_anti_air
        ]
        return float(max(ranges, default=0))

    @staticmethod
    def potential_detection_range(ground_object: TheaterGroundObject) -> float:
        ranges = [
            getattr(unit.type, "detection_range", 0) for unit in ground_object.units
        ]
        return float(max(ranges, default=0))

    def repair_runways(self, budget: float) -> float:
        for control_point in self.owned_points:
            if budget < RUNWAY_REPAIR_COST:
                break
            if control_point.runway_can_be_repaired:
                control_point.begin_runway_repair()
                budget -= RUNWAY_REPAIR_COST
                if self.is_player.is_blue:
                    self.game.message(
                        "We have begun repairing the runway at " f"{control_point}"
                    )
                else:
                    self.game.message(
                        "OPFOR has begun repairing the runway at " f"{control_point}"
                    )
        return budget

    def affordable_ground_unit_of_class(
        self, budget: float, unit_class: UnitClass
    ) -> Optional[GroundUnitType]:
        faction_units = set(self.faction.frontline_units) | set(
            self.faction.artillery_units
        )
        of_class = {u for u in faction_units if u.unit_class is unit_class}

        # faction has no access to needed unit type, take a random unit
        if not of_class:
            of_class = faction_units

        affordable_units = [u for u in of_class if u.price <= budget]
        if not affordable_units:
            return None
        return random.choice(affordable_units)

    def reinforce_front_line(self, budget: float) -> float:
        if not self.faction.frontline_units and not self.faction.artillery_units:
            return budget

        # TODO: Attempt to transfer from reserves.

        while budget > 0:
            cp = self.ground_reinforcement_candidate()
            if cp is None:
                break

            most_needed_type = self.most_needed_unit_class(cp)
            unit = self.affordable_ground_unit_of_class(budget, most_needed_type)
            if unit is None:
                # Can't afford any more units.
                break

            budget -= unit.price
            cp.ground_unit_orders.order({unit: 1})

        return budget

    def most_needed_unit_class(self, cp: ControlPoint) -> UnitClass:
        worst_balanced: Optional[UnitClass] = None
        worst_fulfillment = math.inf
        for unit_class in UnitClass:
            if not self.faction.has_access_to_unit_class(unit_class):
                continue

            current_ratio = self.cost_ratio_of_ground_unit(cp, unit_class)
            desired_ratio = (
                self.faction.doctrine.ground_unit_procurement_ratios.for_unit_class(
                    unit_class
                )
            )
            if not desired_ratio:
                continue
            if current_ratio >= desired_ratio:
                continue
            fulfillment = current_ratio / desired_ratio
            if fulfillment < worst_fulfillment:
                worst_fulfillment = fulfillment
                worst_balanced = unit_class
        if worst_balanced is None:
            return UnitClass.TANK
        return worst_balanced

    @staticmethod
    def fulfill_aircraft_request(
        squadrons: list[Squadron], quantity: int, budget: float
    ) -> Tuple[float, bool]:
        for squadron in squadrons:
            price = squadron.aircraft.price * quantity
            # Final check to make sure the number of aircraft won't exceed the number of available pilots
            # after fulfilling this aircraft request.
            if (
                squadron.pilot_limits_enabled
                and squadron.expected_size_next_turn + quantity
                > squadron.expected_pilots_next_turn
            ):
                continue
            if price > budget:
                continue

            squadron.pending_deliveries += quantity
            budget -= price
            return budget, True
        return budget, False

    def purchase_aircraft(self, budget: float) -> float:
        for request in self.game.coalition_for(self.is_player).procurement_requests:
            squadrons = list(self.best_squadrons_for(request))
            if not squadrons:
                # No airbases in range of this request. Skip it.
                continue
            budget, fulfilled = self.fulfill_aircraft_request(
                squadrons, request.number, budget
            )
        return budget

    @property
    def owned_points(self) -> List[ControlPoint]:
        if self.is_player.is_blue:
            return self.game.theater.player_points()
        else:
            return self.game.theater.enemy_points()

    def best_squadrons_for(
        self, request: AircraftProcurementRequest
    ) -> Iterator[Squadron]:
        threatened = []
        for squadron in self.air_wing.best_squadrons_for(
            request.near,
            request.task_capability,
            request.number,
            request.heli,
            this_turn=False,
        ):
            parking_type = ParkingType().from_squadron(squadron)

            if not squadron.can_provide_pilots(request.number):
                continue
            if squadron.location.unclaimed_parking(parking_type) < request.number:
                continue
            if not squadron.has_aircraft_capacity_for(request.number):
                continue
            if self.threat_zones.threatened(squadron.location.position):
                threatened.append(squadron)
                continue
            yield squadron
        yield from threatened

    def ground_reinforcement_candidate(self) -> Optional[ControlPoint]:
        worst_supply = math.inf
        understaffed: Optional[ControlPoint] = None

        # Prefer to buy front line units at active front lines that are not
        # already overloaded.
        for cp in self.owned_points:
            if not cp.has_active_frontline:
                continue

            if not cp.has_ground_unit_source(self.game):
                # No source of ground units, so can't buy anything.
                continue

            reserves_factor = (
                self.game.settings.frontline_reserves_factor
                if self.is_player.is_blue
                else self.game.settings.frontline_reserves_factor_red
            )
            fr_factor = reserves_factor / 100.0
            purchase_target = cp.frontline_unit_count_limit * fr_factor
            allocated = cp.allocated_ground_units(
                self.game.coalition_for(self.is_player).transfers
            )
            if allocated.total >= purchase_target:
                # Control point is already sufficiently defended.
                continue
            if allocated.total < worst_supply:
                worst_supply = allocated.total
                understaffed = cp

        if understaffed is not None:
            return understaffed

        # Otherwise buy reserves, but don't exceed the amount defined in the settings.
        # These units do not exist in the world until the CP becomes
        # connected to an active front line, at which point all these units
        # will suddenly appear at the gates of the newly captured CP.
        #
        # To avoid sudden overwhelming numbers of units we avoid buying
        # many.
        #
        # Also, do not bother buying units at bases that will never connect
        # to a front line.
        for cp in self.owned_points:
            if cp.is_global:
                continue
            if not cp.can_recruit_ground_units(self.game):
                continue

            allocated = cp.allocated_ground_units(
                self.game.coalition_for(self.is_player).transfers
            )
            target = (
                self.game.settings.reserves_procurement_target
                if self.is_player.is_blue
                else self.game.settings.reserves_procurement_target_red
            )
            if allocated.total >= target:
                continue

            if allocated.total < worst_supply:
                worst_supply = allocated.total
                understaffed = cp

        return understaffed

    def cost_ratio_of_ground_unit(
        self, control_point: ControlPoint, unit_class: UnitClass
    ) -> float:
        allocations = control_point.allocated_ground_units(
            self.game.coalition_for(self.is_player).transfers
        )
        class_cost = 0
        total_cost = 0
        for unit_type, count in allocations.all.items():
            cost = unit_type.price * count
            total_cost += cost
            if unit_type.unit_class is unit_class:
                class_cost += cost
        if not total_cost:
            return 0
        return class_cost / total_cost

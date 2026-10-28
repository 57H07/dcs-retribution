from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Iterator

from shapely.geometry import LineString, Point as ShapelyPoint

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.commander.missionproposals import EscortType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.squadrons.csarservice import FRONT_LINE_DANGER, near_a_front_line
from game.squadrons.downedpilot import DownedPilot
from game.theater.theatergroundobject import IadsGroundObject, NavalGroundObject
from game.utils import meters

#: Waypoints in a flight plan that the flight does not fly through.
_NOT_FLOWN = {FlightWaypointType.BULLSEYE, FlightWaypointType.DIVERT}


@dataclass
class PlanCsar(PackagePlanningTask[DownedPilot]):
    #: Whether to propose a CAS escort, decided against the theater state before
    #: the flights are proposed (propose_flights has no state to look at).
    cas_escort: bool = field(init=False, default=False)

    def preconditions_met(self, state: TheaterState) -> bool:
        if self.target not in state.csar_targets:
            return False
        # Only so much of the ATO is worth spending on rescues in one turn. Pilots
        # are offered closest-to-base first, so the ones dropped here are the least
        # reachable; they wait for a later turn if they survive that long.
        if state.csar_flights_planned >= state.context.settings.max_csar_flights:
            return False
        # Don't feed rescue helicopters into a live SAM ring; the planner will
        # schedule DEAD/SEAD first and revisit the pilot on a later pass. This
        # registers the threats for that; its own verdict is weighted by the
        # autoplanner aggressiveness (and void at 100), which is for strike
        # packages that can fight their way in, not for a slow helicopter.
        if not self.target_area_preconditions_met(state):
            return False
        if any(self.iter_iads_threats(state)):
            return False
        self.cas_escort = (
            state.context.settings.csar_cas_escort
            and self.near_enemy_ground_forces(state)
        )
        if not super().preconditions_met(state):
            return False
        # The pickup is clear, but the route there and back may not be. Only
        # known once the flight plan exists.
        if self.route_threatened(state):
            self.cancel_package()
            return False
        return True

    def csar_routes(self) -> Iterator[LineString]:
        """The rescue helicopters' routes, out and back, as flown."""
        if self.package is None:
            return
        for flight in self.package.flights:
            if flight.flight_type is not FlightType.CSAR:
                continue
            route = [
                (waypoint.position.x, waypoint.position.y)
                for waypoint in flight.flight_plan.waypoints
                if waypoint.waypoint_type not in _NOT_FLOWN
            ]
            if len(route) > 1:
                yield LineString(route)

    def route_threatened(self, state: TheaterState) -> bool:
        """Whether a rescue helicopter would fly through an air defence zone.

        The air defences it would cross are recorded as threats, like those at
        the pickup, so that the planner can go after them first.
        """
        threatened = False
        for route in self.csar_routes():
            if not state.threat_zones.threatened_by_air_defense(route):
                continue
            threatened = True
            air_defenses: Iterator[IadsGroundObject | NavalGroundObject] = (
                itertools.chain(state.enemy_air_defenses, state.enemy_ships)
            )
            for iads in air_defenses:
                threat_range = iads.max_threat_range()
                position = ShapelyPoint(iads.position.x, iads.position.y)
                if (
                    threat_range.meters > 0
                    and route.distance(position) < threat_range.meters
                    and iads not in state.threatening_air_defenses
                ):
                    state.threatening_air_defenses.append(iads)
        return threatened

    def cancel_package(self) -> None:
        """Returns a package that will not be flown to the inventory."""
        if self.package is None:
            return
        for flight in list(self.package.flights):
            self.package.remove_flight(flight)
        self.package = None

    def near_enemy_ground_forces(self, state: TheaterState) -> bool:
        """Whether the pickup is close to a front line or to enemy armour."""
        position = self.target.position
        if near_a_front_line(state.active_front_lines, position, FRONT_LINE_DANGER):
            return True
        for battle_positions in state.enemy_battle_positions.values():
            for armour in battle_positions.in_priority_order:
                if (
                    armour.position.distance_to_point(position)
                    < FRONT_LINE_DANGER.meters
                ):
                    return True
        return False

    def apply_effects(self, state: TheaterState) -> None:
        # One flight collects the whole cluster, so take its other members off the
        # board too rather than planning a package each. The mission generator
        # rebuilds the same cluster from the target's position, so it knows who
        # else to expect at the pickup.
        radius = meters(state.context.settings.csar_cluster_radius)
        for pilot in self.target.cluster(radius):
            if pilot in state.csar_targets:
                state.csar_targets.remove(pilot)
        state.csar_flights_planned += 1
        super().apply_effects(state)

    def propose_flights(self) -> None:
        # Deliberately not get_flight_size(): the 2/3/4-ship weights are about
        # putting enough ordnance on a target, which has nothing to do with how
        # many helicopters it takes to collect one pilot. A pair by default, so
        # the lead has cover on the ground, or a singleton if configured.
        settings = self.target.coalition.game.settings
        self.propose_flight(FlightType.CSAR, 1 if settings.csar_single_flight else 2)
        self.propose_common_escorts()
        if self.cas_escort:
            self.propose_flight(FlightType.CAS, 2, EscortType.Ground)

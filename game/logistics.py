"""Planned air logistics: resupply of forward bases (TRN-03).

When the ``plan_logistics_missions`` setting is on, the HQ flies ground units held
in reserve at rear bases to front-line bases and FOBs at the start of each turn.
Each resupply is an ordinary airlifted :class:`~game.transfers.TransferOrder`, so it
behaves like any other airlift: the units are delivered at the destination at turn
end, they die with the aircraft carrying them, and the flight can be flown by the
player.

Bases without a road link are served first. Cargo planes airdrop the cargo at bases
they cannot land at (FOBs, FARPs) and, since helicopters are limited to
``HELO_AIRLIFT_MAX_RANGE`` per leg, are the only option beyond it. A setting caps the
share of the transport fleet used, to keep transports available for Air Assault.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Optional, TYPE_CHECKING

from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.theater.controlpoint import ControlPointType
from game.theater.transitnetwork import TransitConnection, TransitNetwork
from game.transfers import (
    AirliftPlanner,
    TransferOrder,
    airlift_capacity_per_aircraft,
    airlift_compatible,
    delivers_by_airdrop,
)

if TYPE_CHECKING:
    from game import Game
    from game.dcs.groundunittype import GroundUnitType
    from game.squadrons import Squadron
    from game.theater import ControlPoint, Player


def logistics_enabled(game: Game, player: Player) -> bool:
    """True if the HQ of player plans logistics missions this turn."""
    from game.settings import AutoAtoBehavior

    settings = game.settings
    if not settings.plan_logistics_missions:
        return False
    # The player's HQ follows the auto-planner switch, like any other package.
    return not (
        player.is_blue and settings.auto_ato_behavior is AutoAtoBehavior.Disabled
    )


def is_cut_off(control_point: ControlPoint, network: TransitNetwork) -> bool:
    """True for a ground base with no road, sea or air link to a friendly base.

    Such a base gets no reinforcements through transfers; only an airdrop by a
    logistics flight can reach it.
    """
    if control_point.captured.is_neutral or control_point.is_fleet:
        return False
    if not control_point.can_deploy_ground_units:
        return False
    # nodes.get: the network is a defaultdict, indexing it would add the base.
    return not network.nodes.get(control_point)


def base_is_cut_off(control_point: ControlPoint) -> bool:
    """is_cut_off for the map, shown only when logistics missions are enabled."""
    if control_point.captured.is_neutral:
        return False
    game = control_point.coalition.game
    if not game.settings.plan_logistics_missions:
        return False
    return is_cut_off(control_point, game.transit_network_for(control_point.captured))


@dataclass(frozen=True)
class ResupplyTarget:
    base: ControlPoint
    #: Ground units the base can still use: front-line capacity minus the units
    #: present and the units already on their way.
    deficit: int
    has_road: bool
    front_line: bool

    @property
    def priority(self) -> tuple[bool, bool, int]:
        # Sorted ascending: no road first, then front line, then the largest need.
        return self.has_road, not self.front_line, -self.deficit


class LogisticsPlanner:
    """Plans the resupply flights of one coalition for this turn."""

    def __init__(self, game: Game, player: Player) -> None:
        self.game = game
        self.player = player
        self.coalition = game.coalition_for(player)
        self.network = game.transit_network_for(player)
        self.air_wing = game.air_wing_for(player)
        self.aircraft_left = self.fleet_cap()

    def transport_squadrons(self) -> Iterator[Squadron]:
        for squadron in self.air_wing.iter_squadrons():
            if not squadron.can_auto_assign(FlightType.TRANSPORT):
                continue
            if (
                squadron.location.cptype
                in (ControlPointType.FOB, ControlPointType.FARP)
                and not squadron.aircraft.dcs_unit_type.helicopter
            ):
                # AI planes cannot use FOBs or FARPs (Squadron.can_auto_assign_mission)
                continue
            yield squadron

    def fleet_cap(self) -> int:
        """Aircraft logistics flights may use this turn."""
        fleet = sum(s.untasked_crewed_aircraft for s in self.transport_squadrons())
        share = self.game.settings.logistics_transport_fleet_share
        return math.floor(fleet * share / 100)

    def _friendly_ground_bases(self) -> Iterator[ControlPoint]:
        for cp in self.game.theater.control_points_for(self.player):
            if cp.can_deploy_ground_units and not cp.is_fleet:
                yield cp

    @staticmethod
    def _wants_resupply(cp: ControlPoint) -> bool:
        return cp.has_active_frontline or cp.is_fob

    def _has_road(self, cp: ControlPoint) -> bool:
        return any(
            link is TransitConnection.Road
            for link in self.network.nodes.get(cp, {}).values()
        )

    def _incoming(self, cp: ControlPoint) -> int:
        return sum(t.size for t in self.coalition.transfers if t.destination == cp)

    def resupply_targets(self) -> list[ResupplyTarget]:
        """Bases in need of ground units, the most urgent first."""
        targets = []
        for cp in self._friendly_ground_bases():
            if not self._wants_resupply(cp):
                continue
            deficit = (
                cp.frontline_unit_count_limit - cp.base.total_armor - self._incoming(cp)
            )
            if deficit <= 0:
                continue
            targets.append(
                ResupplyTarget(cp, deficit, self._has_road(cp), cp.has_active_frontline)
            )
        return sorted(targets, key=lambda t: t.priority)

    def reserves(self, cp: ControlPoint) -> int:
        """Ground units cp can give away: all of them at a rear base."""
        if cp.has_active_frontline:
            return 0
        if cp.is_fob:
            return max(0, cp.base.total_armor - cp.frontline_unit_count_limit)
        return cp.base.total_armor

    def _sources_for(self, target: ControlPoint) -> list[ControlPoint]:
        sources = [
            cp
            for cp in self._friendly_ground_bases()
            if cp != target and self.reserves(cp) > 0
        ]
        return sorted(
            sources, key=lambda cp: cp.position.distance_to_point(target.position)
        )

    def _squadron_for(
        self, source: ControlPoint, target: ControlPoint
    ) -> Optional[Squadron]:
        """The transport squadron best placed to fly source to target, if any.

        Landing is preferred to airdropping, then the squadron closest to the
        cargo. Helicopters cannot fly legs longer than HELO_AIRLIFT_MAX_RANGE, so
        beyond it only cargo planes qualify.
        """
        probe = TransferOrder(source, target, {})
        candidates = [
            squadron
            for squadron in self.transport_squadrons()
            if squadron.untasked_crewed_aircraft > 0
            and airlift_compatible(
                squadron.aircraft,
                squadron.location,
                probe,
                target,
                allow_airdrop=True,
            )
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda s: (
                delivers_by_airdrop(s.aircraft, target),
                s.location.position.distance_to_point(source.position),
            ),
        )

    def _cargo(self, source: ControlPoint, count: int) -> dict[GroundUnitType, int]:
        units: dict[GroundUnitType, int] = {}
        for unit_type, available in sorted(
            source.base.armor.items(), key=lambda i: -i[1]
        ):
            if count <= 0:
                break
            take = min(available, count)
            if take > 0:
                units[unit_type] = take
                count -= take
        return units

    def plan_resupply(self, target: ResupplyTarget, now: datetime) -> Optional[Package]:
        """Plans one resupply flight to target, if a source and a squadron allow."""
        for source in self._sources_for(target.base):
            squadron = self._squadron_for(source, target.base)
            if squadron is None:
                continue
            aircraft = min(
                squadron.untasked_crewed_aircraft,
                squadron.aircraft.dcs_unit_type.group_size_max,
                self.aircraft_left,
            )
            capacity = aircraft * airlift_capacity_per_aircraft(squadron.aircraft)
            count = min(target.deficit, self.reserves(source), capacity)
            if count <= 0:
                continue
            transfer = TransferOrder(
                source, target.base, self._cargo(source, count), request_airflift=True
            )
            source.base.commit_losses(transfer.units)
            self.coalition.transfers.pending_transfers.append(transfer)
            package = AirliftPlanner(
                self.game, transfer, target.base
            ).create_package_with(squadron, now)
            self.aircraft_left -= math.ceil(
                transfer.size / airlift_capacity_per_aircraft(squadron.aircraft)
            )
            logging.info(
                f"Logistics: {transfer.size} units from {source} to {target.base} by "
                f"{squadron}"
            )
            return package
        return None

    def plan(self, now: datetime) -> list[Package]:
        """Plans this turn's resupply flights, one per base in need at most."""
        packages = []
        for target in self.resupply_targets():
            if self.aircraft_left <= 0:
                break
            package = self.plan_resupply(target, now)
            if package is not None:
                packages.append(package)
        return packages


def plan_logistics(game: Game, player: Player, now: datetime) -> list[Package]:
    """Entry point from turn initialization."""
    if not logistics_enabled(game, player):
        return []
    return LogisticsPlanner(game, player).plan(now)

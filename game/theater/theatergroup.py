from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING, Type

from dcs import Point
from dcs.triggers import TriggerZone
from dcs.unittype import ShipType, StaticType, UnitType as DcsUnitType, VehicleType

from game.data.radar_db import LAUNCHER_TRACKER_PAIRS, TELARS, TRACK_RADARS
from game.data.units import ANTI_AIR_UNIT_CLASSES, UnitClass
from game.dcs.groundunittype import GroundUnitType
from game.dcs.shipunittype import ShipUnitType
from game.dcs.unittype import UnitType
from game.point_with_heading import PointWithHeading
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.utils import Heading, Distance, meters

if TYPE_CHECKING:
    from game.layout.layout import LayoutUnit
    from game.sim import GameUpdateEvents
    from game.theater.theatergroundobject import TheaterGroundObject

FIXED_POS_ARG = "--fix-pos"
FIXED_HDG_ARG = "--fix-hdg"


@dataclass
class TheaterUnit:
    """Representation of a single Unit in the Game"""

    # Every Unit has a unique ID generated from the game
    id: int
    # The name of the Unit. Not required to be unique
    name: str
    # DCS UniType of the unit
    type: Type[DcsUnitType]
    # Position and orientation of the Unit
    position: PointWithHeading
    # The parent ground object
    ground_object: TheaterGroundObject
    # Should the unit's position remain fixed?
    fixed_pos: bool = False
    # Should the unit's heading remain fixed?
    fixed_hdg: bool = False
    # State of the unit, dead or alive
    alive: bool = True
    # Turns remaining until the unit is repaired and revived.
    repair_turns_remaining: Optional[int] = None
    # Turn on which a unit made inoperative by persistent damage is operational
    # again. None when the unit is not inoperative.
    operational_on_turn: Optional[int] = None

    @staticmethod
    def from_template(
        id: int,
        dcs_type: Type[DcsUnitType],
        t: LayoutUnit,
        go: TheaterGroundObject,
        fixed_pos: bool,
        fixed_hdg: bool,
    ) -> TheaterUnit:
        return TheaterUnit(
            id,
            t.name,
            dcs_type,
            PointWithHeading.from_point(t.position, Heading.from_degrees(t.heading)),
            go,
            fixed_pos or FIXED_POS_ARG in t.name,
            fixed_hdg or FIXED_HDG_ARG in t.name,
        )

    @property
    def unit_type(self) -> Optional[UnitType[Any]]:
        if issubclass(self.type, VehicleType):
            return next(GroundUnitType.for_dcs_type(self.type))
        elif issubclass(self.type, ShipType):
            return next(ShipUnitType.for_dcs_type(self.type))
        # None for not available StaticTypes
        return None

    def _combat_state_changed(self, events: GameUpdateEvents) -> None:
        self.ground_object.invalidate_threat_poly()
        events.update_tgo(self.ground_object)
        if self.ground_object.is_iads:
            iads = self.ground_object.control_point.coalition.game.theater.iads_network
            iads.update_tgo(self.ground_object, events)

    def kill(self, events: GameUpdateEvents) -> None:
        self.alive = False
        self.operational_on_turn = None
        self._combat_state_changed(events)
        if self.ground_object.is_naval_control_point:
            for unit in self.ground_object.units:
                if (
                    unit.unit_type
                    and unit.unit_type.unit_class is UnitClass.AIRCRAFT_CARRIER
                    and not unit.alive
                ):
                    cp = self.ground_object.control_point
                    for squadron in cp.squadrons:
                        cp.coalition.air_wing.squadrons[squadron.aircraft].remove(
                            squadron
                        )

    def revive(self, events: GameUpdateEvents) -> None:
        self.alive = True
        self.operational_on_turn = None
        self.ground_object.threat_poly()
        events.update_tgo(self.ground_object)
        if self.ground_object.is_iads:
            iads = self.ground_object.control_point.coalition.game.theater.iads_network
            iads.update_tgo(self.ground_object, events)

    @property
    def inoperative(self) -> bool:
        """True while a damaged unit waits for repair (persistent damage)."""
        return self.alive and self.operational_on_turn is not None

    @property
    def operational(self) -> bool:
        return self.alive and not self.inoperative

    def inoperative_turns_remaining(self, current_turn: int) -> int:
        if not self.inoperative or self.operational_on_turn is None:
            return 0
        return max(self.operational_on_turn - current_turn, 0)

    def make_inoperative(
        self, turns: int, current_turn: int, events: GameUpdateEvents
    ) -> None:
        """Takes the unit out of action for the ``turns`` turns after
        ``current_turn``. A unit already inoperative keeps the longer countdown."""
        if not self.alive or turns <= 0:
            return
        operational_on = current_turn + turns + 1
        if self.operational_on_turn is not None:
            operational_on = max(operational_on, self.operational_on_turn)
        self.operational_on_turn = operational_on
        self._combat_state_changed(events)

    def end_inoperative(self, events: GameUpdateEvents) -> None:
        if self.operational_on_turn is None:
            return
        self.operational_on_turn = None
        self._combat_state_changed(events)

    @property
    def unit_name(self) -> str:
        return f"{str(self.id).zfill(4)} | {self.name}"

    @property
    def display_name(self) -> str:
        unit_label = self.unit_type or self.type.name or self.name
        return f"{str(self.id).zfill(4)} | {unit_label}{self._status_label}"

    @property
    def short_name(self) -> str:
        return f"<b>{self.type.id[0:18]}</b> {self._status_label}"

    @property
    def _status_label(self) -> str:
        if not self.alive:
            return " [DEAD]"
        if self.inoperative:
            return " [INOPERATIVE]"
        return ""

    @property
    def is_static(self) -> bool:
        return issubclass(self.type, StaticType) or isinstance(self, SceneryUnit)

    @property
    def is_vehicle(self) -> bool:
        return issubclass(self.type, VehicleType)

    @property
    def is_ship(self) -> bool:
        return issubclass(self.type, ShipType)

    @property
    def is_anti_air(self) -> bool:
        return (
            self.unit_type is not None
            and self.unit_type.unit_class in ANTI_AIR_UNIT_CLASSES
        )

    @property
    def icon(self) -> str:
        return self.type.id

    @property
    def repairable(self) -> bool:
        # Only let units with UnitType be repairable as we just have prices for them
        return self.unit_type is not None

    @property
    def detection_range(self) -> Distance:
        unit_range = getattr(self.type, "detection_range", None)
        return meters(unit_range if unit_range is not None and self.operational else 0)

    @property
    def threat_range(self) -> Distance:
        unit_range = getattr(self.type, "threat_range", None)
        return meters(unit_range if unit_range is not None and self.operational else 0)

    def rotate_heading_clockwise(self, rotation: Heading) -> None:
        if self.fixed_hdg:
            return
        self.position.heading += rotation

    def rotate_position_clockwise(self, position: Point, rotation: Heading) -> None:
        if self.fixed_pos:
            return
        self.position.rotate(position, rotation)


class SceneryUnit(TheaterUnit):
    """Special TheaterUnit for handling scenery ground objects"""

    # Scenery Objects are identified by a special trigger zone
    zone: TriggerZone

    @property
    def display_name(self) -> str:
        dead_label = " [DEAD]" if not self.alive else ""
        return f"{str(self.id).zfill(4)} | {self.name}{dead_label}"

    @property
    def short_name(self) -> str:
        dead_label = " [DEAD]" if not self.alive else ""
        return f"<b>{self.name[0:18]}</b> {dead_label}"

    @property
    def icon(self) -> str:
        return "missing"

    @property
    def repairable(self) -> bool:
        return False


@dataclass
class TheaterGroup:
    """Logical group for multiple TheaterUnits at a specific position"""

    # Every Theater Group has a unique ID generated from the game
    id: int  # Unique ID
    # The name of the Group. Not required to be unique
    name: str
    # Position and orientation of the Group
    position: PointWithHeading
    # All TheaterUnits within the group
    units: list[TheaterUnit]
    # The parent ground object
    ground_object: TheaterGroundObject

    @staticmethod
    def from_template(
        id: int,
        name: str,
        units: list[TheaterUnit],
        go: TheaterGroundObject,
    ) -> TheaterGroup:
        return TheaterGroup(
            id,
            name,
            PointWithHeading.from_point(go.position, go.heading),
            units,
            go,
        )

    @property
    def group_name(self) -> str:
        return f"{str(self.id).zfill(4)} | {self.name}"

    @property
    def unit_count(self) -> int:
        return len(self.units)

    @property
    def alive_units(self) -> int:
        return sum(unit.alive for unit in self.units)

    def max_detection_range(self) -> Distance:
        """Calculate the maximum detection range of the TheaterGroup"""
        ranges = (u.detection_range for u in self.units if u.is_anti_air)
        return max(ranges, default=meters(0))

    def max_threat_range(self, radar_only: bool = False) -> Distance:
        """Calculate the maximum threat range of the TheaterGroup.
        This also checks for Launcher and Tracker Pairs and if they are functioning or not. Allows to also use only radar emitting units for the calculation with the parameter.
        """
        max_non_radar = meters(0)
        max_telar_range = meters(0)
        max_tel_range = meters(0)
        live_trs = set()
        launchers: dict[Type[VehicleType], Distance] = {}
        for unit in self.units:
            if not unit.operational or not unit.is_anti_air:
                continue
            if unit.type in TRACK_RADARS:
                live_trs.add(unit.type)
            elif unit.type in TELARS:
                max_telar_range = max(max_telar_range, unit.threat_range)
            elif (
                issubclass(unit.type, VehicleType)
                and unit.type in LAUNCHER_TRACKER_PAIRS
            ):
                launchers[unit.type] = unit.threat_range
            else:
                max_non_radar = max(max_non_radar, unit.threat_range)
        for launcher, threat_range in launchers.items():
            for tr in LAUNCHER_TRACKER_PAIRS[launcher]:
                if tr in live_trs:
                    max_tel_range = max(max_tel_range, threat_range)
        if radar_only:
            return max(max_tel_range, max_telar_range)
        return max(max_tel_range, max_telar_range, max_non_radar)


class IadsGroundGroup(TheaterGroup):
    # IADS GroundObject Groups have a specific Role for the system
    iads_role: IadsRole = IadsRole.NO_BEHAVIOR

    @staticmethod
    def from_group(group: TheaterGroup) -> IadsGroundGroup:
        return IadsGroundGroup(
            group.id,
            group.name,
            group.position,
            group.units,
            group.ground_object,
        )

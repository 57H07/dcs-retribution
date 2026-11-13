"""The data cartridge (DTC) of a player flight (#191).

DCS reads a cartridge as JSON, `{"data": {...}, "name": ..., "type": ...}`; see
`docs/dev/design/dtc.md` for the format and the modules that accept it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from typing import Any, Callable, Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from dcs import Point

    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.squadrons.dtcsettings import DtcSettings
    from .cmds import CmdsSchema
    from game.missiongenerator.missiondata import MissionData
    from game.theater.player import Player


@dataclass(frozen=True)
class DtcThreat:
    """An air defense site, as a reference point of a cartridge."""

    name: str
    position: Point
    #: The side that owns it: a flight sees the sites of the other side.
    owner: Player
    #: How far it reaches, in metres; 0 when unknown.
    threat_range_m: float = 0.0


@dataclass(frozen=True)
class DtcContext:
    """What a cartridge needs from the mission besides the flight."""

    #: Terrain name, as `dcs.terrain.Terrain.name`.
    terrain: str
    #: Mission start, local time of the theater.
    start_time: datetime
    timezone: tzinfo
    #: Each active front line, from end to end.
    front_lines: tuple[tuple[Point, Point], ...] = field(default=())
    #: The air defense sites of both sides that still have working air defense.
    air_defenses: tuple[DtcThreat, ...] = field(default=())


@dataclass(frozen=True)
class DtcCartridge:
    #: Name shown in the DTC page of the jet; also the file name, `<name>.dtc`.
    name: str
    #: DCS unit type id, e.g. `FA-18C_hornet`.
    unit_type: str
    data: dict[str, Any]

    @property
    def file_name(self) -> str:
        return f"{self.name}.dtc"

    def to_json(self) -> str:
        return json.dumps(
            {"data": self.data, "name": self.name, "type": self.unit_type}, indent=4
        )


CartridgeBuilder = Callable[
    ["FlightData", "MissionData", DtcContext, str], DtcCartridge
]


def _builders() -> dict[str, CartridgeBuilder]:
    from . import apache, hornet, tomcat, viper

    return {
        apache.UNIT_TYPE: apache.build,
        hornet.UNIT_TYPE: hornet.build,
        tomcat.UNIT_TYPE: tomcat.build,
        viper.UNIT_TYPE: viper.build,
    }


def supports(flight: FlightData) -> bool:
    """Whether the module of `flight` takes a native cartridge."""
    return takes_cartridge(flight.aircraft_type.dcs_unit_type.id)


def takes_cartridge(unit_type: str) -> bool:
    """Whether the module of DCS type `unit_type` takes a native cartridge."""
    return unit_type in _builders()


def cmds_schema(unit_type: str) -> CmdsSchema | None:
    """The CMDS programs the player may set in the cartridge of the module (#221)."""
    from . import hornet, tomcat, viper

    return {
        hornet.UNIT_TYPE: hornet.CMDS,
        tomcat.UNIT_TYPE: tomcat.CMDS,
        viper.UNIT_TYPE: viper.CMDS,
    }.get(unit_type)


def shows_threats(unit_type: str) -> bool:
    """Whether the cartridge of the module adds front lines and air defenses."""
    from . import apache, tomcat, viper

    return unit_type in (apache.UNIT_TYPE, tomcat.UNIT_TYPE, viper.UNIT_TYPE)


def dtc_settings(flight: FlightData) -> DtcSettings:
    """What the player set for the cartridges of the flight's squadron (#221)."""
    return flight.squadron.dtc


def cartridge_name(flight: FlightData) -> str:
    """`Retribution <callsign>`, kept to the characters of a file name."""
    callsign = re.sub(r"[^A-Za-z0-9 _-]", "", flight.callsign).strip()
    return f"Retribution {callsign}".strip()


def _nearest(
    objective: Point, items: Iterable[Any], position: Callable[[Any], Point], limit: int
) -> list[Any]:
    return sorted(items, key=lambda i: objective.distance_to_point(position(i)))[:limit]


def nearest_front_lines(
    flight: FlightData, context: DtcContext, limit: int
) -> list[tuple[Point, Point]]:
    """The front lines nearest the package target, nearest first."""

    def middle(line: tuple[Point, Point]) -> Point:
        start, end = line
        return start.midpoint(end)

    return _nearest(flight.package.target.position, context.front_lines, middle, limit)


def nearest_threats(
    flight: FlightData, context: DtcContext, limit: int
) -> list[DtcThreat]:
    """The enemy air defense sites nearest the package target, nearest first."""
    hostile = [
        site
        for site in context.air_defenses
        if not site.owner.is_neutral and site.owner != flight.friendly
    ]
    return _nearest(
        flight.package.target.position, hostile, lambda s: s.position, limit
    )


def build_cartridge(
    flight: FlightData, mission_data: MissionData, context: DtcContext
) -> DtcCartridge | None:
    """The cartridge of `flight`; None when its module takes none."""
    builder = _builders().get(flight.aircraft_type.dcs_unit_type.id)
    if builder is None:
        return None
    return builder(flight, mission_data, context, cartridge_name(flight))

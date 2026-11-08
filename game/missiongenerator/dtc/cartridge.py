"""The data cartridge (DTC) of a player flight (#191).

DCS reads a cartridge as JSON, `{"data": {...}, "name": ..., "type": ...}`; see
`docs/dev/design/dtc.md` for the format and the modules that accept it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from dcs import Point

    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData
    from game.theater.player import Player


@dataclass(frozen=True)
class DtcThreat:
    """An air defense site, as a reference point of a cartridge."""

    name: str
    position: Point
    #: The side that owns it: a flight sees the sites of the other side.
    owner: Player


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
    from . import hornet, tomcat

    return {hornet.UNIT_TYPE: hornet.build, tomcat.UNIT_TYPE: tomcat.build}


def supports(flight: FlightData) -> bool:
    """Whether the module of `flight` takes a native cartridge."""
    return flight.aircraft_type.dcs_unit_type.id in _builders()


def cartridge_name(flight: FlightData) -> str:
    """`Retribution <callsign>`, kept to the characters of a file name."""
    callsign = re.sub(r"[^A-Za-z0-9 _-]", "", flight.callsign).strip()
    return f"Retribution {callsign}".strip()


def build_cartridge(
    flight: FlightData, mission_data: MissionData, context: DtcContext
) -> DtcCartridge | None:
    """The cartridge of `flight`; None when its module takes none."""
    builder = _builders().get(flight.aircraft_type.dcs_unit_type.id)
    if builder is None:
        return None
    return builder(flight, mission_data, context, cartridge_name(flight))

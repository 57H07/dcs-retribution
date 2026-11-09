"""F-16C cartridge: the front lines and the enemy air defenses (#191).

The miz already carries the route and the radio presets of the jet, and the F-16C
cartridge cannot name a channel: `NAV_PTS`, `DEST` and `COMM` mirror the mission. The
cartridge adds what the miz cannot: the front lines as `GEO_LINES` and the enemy air
defense sites as `THREAT_PTS`, ringed on the HSD. `CMDS`, `ROE` and the other pages
keep the module's defaults.

The fields and limits are those of the module's DTC editor,
`CoreMods/aircraft/F-16C/DTC/MPD` (`GEO_LINES.lua`, `THREAT_PTS.lua`).
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .cartridge import (
    DtcCartridge,
    DtcContext,
    nearest_front_lines,
    nearest_threats,
)

if TYPE_CHECKING:
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

UNIT_TYPE = "F-16C_50"

#: The HSD draws 4 lines, L1 to L4, through geo points 31 to 55.
MAX_LINES = 4
#: Point n is `GEO_LINES<30 + n>`, as the editor names it.
_FIRST_GEO_POINT = 30
#: Threat points 56 to 70: point n is `THREAT_PTS<55 + n>`.
MAX_THREATS = 15
_FIRST_THREAT_POINT = 55
#: The custom threat of the editor (`THREAT_PTS_defs.lua`, entry 1).
_CUSTOM_THREAT = 1
_CUSTOM_RADIUS_M = 37040.0
_CUSTOM_ALTITUDE_M = 9144.0


def _geo_lines(flight: FlightData, context: DtcContext) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for line, (start, end) in enumerate(
        nearest_front_lines(flight, context, MAX_LINES), 1
    ):
        for position in (start, end):
            number = len(points) + 1
            points.append(
                {
                    "number": number,
                    "id": f"GEO_LINES{_FIRST_GEO_POINT + number}",
                    "x": position.x,
                    "y": position.y,
                    "alt": 0.0,
                    **{f"L{n}": n == line for n in range(1, MAX_LINES + 1)},
                    "note": "",
                }
            )
    return points


def _threat_points(flight: FlightData, context: DtcContext) -> list[dict[str, Any]]:
    return [
        {
            "number": number,
            "id": f"THREAT_PTS{_FIRST_THREAT_POINT + number}",
            "x": site.position.x,
            "y": site.position.y,
            "threatName": site.name,
            "radius": site.threat_range_m or _CUSTOM_RADIUS_M,
            "alt": _CUSTOM_ALTITUDE_M,
            "elev": 0.0,
            # The HSD label: at most 3 letters or digits.
            "text": f"T{number}",
            "ring": True,
            "def_num": _CUSTOM_THREAT,
        }
        for number, site in enumerate(nearest_threats(flight, context, MAX_THREATS), 1)
    ]


def build(
    flight: FlightData, mission_data: MissionData, context: DtcContext, name: str
) -> DtcCartridge:
    data: dict[str, Any] = {
        "type": UNIT_TYPE,
        "name": name,
        "terrain": context.terrain,
        "MPD": {
            "mirror_NAV_PTS": True,
            "mirror_DEST": True,
            "mirror_GEO_LINES": False,
            "mirror_THREAT_PTS": False,
            "GEO_LINES": _geo_lines(flight, context),
            "THREAT_PTS": _threat_points(flight, context),
        },
        "COMM": {"mirror_COMM1": True, "mirror_COMM2": True},
    }
    return DtcCartridge(name=name, unit_type=UNIT_TYPE, data=data)

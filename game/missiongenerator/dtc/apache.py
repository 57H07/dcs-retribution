"""AH-64D cartridge: the front lines and the enemy air defenses (#191).

The miz already carries the route of the helicopter. The cartridge adds, in mission
file 1, what the miz cannot: the front lines as FLOT lines and the enemy air defense
sites as target points, which the TSD rings as threats. Waypoints, hazards and control
measures are left out, so the helicopter keeps those of the mission; the other
partitions (radios, weapons, laser codes) keep the module's defaults.

The fields and limits are those of the module's DTC editor,
`CoreMods/aircraft/AH-64D/DTC/NAV` (`Points.lua`, `Lines.lua`).
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .cartridge import (
    DtcCartridge,
    DtcContext,
    dtc_settings,
    nearest_front_lines,
    nearest_threats,
)

if TYPE_CHECKING:
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

UNIT_TYPE = "AH-64D_BLK_II"

#: The editor holds 15 lines; the front lines nearest the target are enough.
MAX_LINES = 4
#: `FLOT (Forward Line of Own Troops)`, entry 4 of `LineTypesCaptions`.
_FLOT = 4
#: Target points T01 to T50; the nearest sites are enough.
MAX_THREATS = 20
#: `GU (Generic Air Defense Unit)` of the TGT point types.
_GENERIC_AIR_DEFENSE = 2
#: The free text of a point or line.
_NOTE_LENGTH = 40


def _note(text: str) -> str:
    ascii_only = text.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_only.split())[:_NOTE_LENGTH]


def _lines(flight: FlightData, context: DtcContext) -> list[dict[str, Any]]:
    return [
        {
            "type_num": _FLOT,
            "text": "",
            "note": "Front line",
            "vertices": [{"x": start.x, "y": start.y}, {"x": end.x, "y": end.y}],
        }
        for start, end in nearest_front_lines(flight, context, MAX_LINES)
    ]


def _threats(flight: FlightData, context: DtcContext) -> dict[str, Any]:
    sites = nearest_threats(flight, context, MAX_THREATS)
    return {
        "isEnabled": True,
        "POINTS": [
            {
                "num": number,
                "id": _GENERIC_AIR_DEFENSE,
                # The editor's default label: T01, T02...
                "text": f"T{number:02d}",
                "note": _note(site.name),
                "x": site.position.x,
                "y": site.position.y,
                # Elevation in metres, from the height map of the DCS map.
                "alt": round(context.elevation_m(site.position)),
            }
            for number, site in enumerate(sites, 1)
        ],
    }


def build(
    flight: FlightData, mission_data: MissionData, context: DtcContext, name: str
) -> DtcCartridge:
    mission: dict[str, Any] = {}
    if dtc_settings(flight).threats:
        mission["Lines"] = _lines(flight, context)
        mission["Points"] = {"TGT": _threats(flight, context)}
    data: dict[str, Any] = {
        "type": UNIT_TYPE,
        "name": name,
        "terrain": context.terrain,
        "NAV": {"MissionFile": 1, "Mission_1": mission},
    }
    return DtcCartridge(name=name, unit_type=UNIT_TYPE, data=data)

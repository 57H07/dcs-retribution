"""F-14BU cartridge: the front lines and the enemy air defenses (#191).

Flight plan 1 of the jet is the route of the mission editor, which the miz already
carries; the cartridge leaves its waypoints empty and adds what the miz cannot: the
front lines as `lines` and the enemy air defense sites as `additional_points`. The
other partitions (`CMDS`, `JDAM`, `TIS`) keep the module's defaults.

The limits are those of the module's DTC editor, `CoreMods/aircraft/F14/DTC`.
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
from .cmds import ALE47

if TYPE_CHECKING:
    from dcs import Point

    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

UNIT_TYPE = "F-14BU"
#: The countermeasure programs the player may set (#221).
CMDS = ALE47

#: Flight plans of the jet; plan 1 is the mission route.
PLANS = 12
#: Lines of a flight plan.
MAX_LINES = 4
#: Reference points of a flight plan.
MAX_REFERENCE_POINTS = 20


def _place(position: Point) -> dict[str, Any]:
    """The coordinates the DTC editor stores for a point; elevation in feet."""
    lat_lon = position.latlng()
    return {
        "x": position.x,
        "y": position.y,
        "lat": lat_lon.lat,
        "lon": lat_lon.lng,
        "elev": 0,
    }


def _lines(flight: FlightData, context: DtcContext) -> list[dict[str, Any]]:
    return [
        {"points": [_place(start), _place(end)], "closed": False}
        for start, end in nearest_front_lines(flight, context, MAX_LINES)
    ]


def _threats(flight: FlightData, context: DtcContext) -> list[dict[str, Any]]:
    sites = nearest_threats(flight, context, MAX_REFERENCE_POINTS)
    return [
        {"name": f"THRT {number}", **_place(site.position)}
        for number, site in enumerate(sites, 1)
    ]


def _plan() -> dict[str, Any]:
    return {
        "name": "",
        "waypoints": [],
        "lines": [],
        "additional_points": [],
        "route_as_line": False,
    }


def build(
    flight: FlightData, mission_data: MissionData, context: DtcContext, name: str
) -> DtcCartridge:
    settings = dtc_settings(flight)
    plans = [_plan() for _ in range(PLANS)]
    if settings.threats:
        plans[0]["lines"] = _lines(flight, context)
        plans[0]["additional_points"] = _threats(flight, context)
    data: dict[str, Any] = {
        "type": UNIT_TYPE,
        "name": name,
        "cartridge_name": name,
        "terrain": context.terrain,
        "NAV": plans,
    }
    if settings.cmds:
        data["CMDS"] = {
            "delay_between_programs": 0,
            **CMDS.program_settings(settings.cmds),
        }
    return DtcCartridge(name=name, unit_type=UNIT_TYPE, data=data)

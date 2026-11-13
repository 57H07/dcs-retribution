"""F-14BU cartridge: front lines, enemy air defenses, CMDS and JDAM targets.

Flight plan 1 of the jet is the route of the mission editor, which the miz already
carries; the cartridge leaves its waypoints empty and adds what the miz cannot: the
front lines as `lines` and the enemy air defense sites as `additional_points` (#191).
What the player sets for the squadron (#221) adds the CMDS programs, and, for each
station 3 to 6 that carries a JDAM, the aim points of the package target with the
launch acceptability region (LAR) the jet reads from the cartridge. `TIS` keeps the
module's defaults.

The fields, limits and the LAR are those of the module's DTC editor,
`CoreMods/aircraft/F14/DTC/F-14BU_DTC.lua`; a cartridge saved by that editor
(`F14_Tuto_JDAM.miz`) gives the same LAR and region to the centimetre.
"""

from __future__ import annotations

import math
from typing import Any, Optional, TYPE_CHECKING

from game.ato.flightwaypointtype import FlightWaypointType
from game.theater.theatergroundobject import TheaterGroundObject
from .cartridge import (
    DtcCartridge,
    DtcContext,
    dtc_settings,
    nearest_front_lines,
    nearest_threats,
)
from .cmds import TOMCAT
from .hornet import leg_speed_kmh

if TYPE_CHECKING:
    from dcs import Point

    from game.ato.flightwaypoint import FlightWaypoint
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

UNIT_TYPE = "F-14BU"
#: The countermeasure programs the player may set (#221).
CMDS = TOMCAT

#: Flight plans of the jet; plan 1 is the mission route.
PLANS = 12
#: Lines of a flight plan.
MAX_LINES = 4
#: Reference points of a flight plan.
MAX_REFERENCE_POINTS = 20

#: JDAM stations 3 to 6, pydcs pylons 4 to 7, each with 8 targets.
JDAM_STATIONS = 4
JDAM_TARGETS_PER_STATION = 8
_FIRST_JDAM_PYLON = 4
_JDAM_CLSIDS = ("GBU_31", "GBU-31", "GBU_32", "GBU-32", "GBU_38", "GBU-38")
#: The editor's defaults: 20,000 ft, 450 kt, impact at 65 degrees.
_DROP_ALT_FT = 20000
_DROP_SPEED_KT = 450
_IMPACT_ANGLE = 65
_METERS_TO_FEET = 3.28084
_NMI_TO_METERS = 1852.0

#: `JDAM_LAR_TABLE` of the editor: (min range nm, max range nm, half angle deg)
#: by drop altitude (kft) and Mach.
_LAR_ALTS_KFT = (5, 10, 20, 30, 40, 50)
_LAR_MACHS = (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2)
_LAR_TABLE = (
    ((0.87, 1.50, 20.00), (0.93, 1.95, 24.04), (1.07, 2.52, 23.64), (1.21, 3.32, 22.24), (1.35, 4.41, 24.72), (1.52, 5.77, 30.62), (1.75, 7.52, 32.31), (1.98, 8.95, 34.52), (2.23, 10.09, 37.22)),
    ((0.91, 2.29, 32.77), (1.07, 3.04, 35.12), (1.23, 3.74, 37.15), (1.42, 4.95, 36.65), (1.62, 6.36, 35.70), (1.81, 8.01, 34.41), (2.01, 9.48, 37.02), (2.22, 10.83, 39.82), (2.47, 12.02, 41.79)),
    ((1.71, 3.36, 43.14), (2.09, 3.91, 42.72), (1.85, 5.28, 44.44), (1.62, 6.75, 45.00), (1.47, 8.29, 44.95), (2.03, 10.02, 44.38), (2.21, 11.69, 44.39), (2.03, 13.33, 44.96), (2.25, 14.80, 45.00)),
    ((1.42, 4.99, 45.00), (1.89, 5.40, 45.00), (1.99, 6.06, 45.00), (2.08, 7.16, 45.00), (2.16, 8.89, 45.00), (2.37, 10.69, 45.00), (2.64, 12.53, 45.00), (2.95, 14.51, 45.00), (3.24, 16.34, 45.00)),
    ((1.37, 6.84, 45.00), (1.85, 7.35, 45.00), (2.21, 8.12, 45.00), (2.48, 8.88, 45.00), (2.48, 9.52, 45.00), (2.65, 10.18, 45.00), (2.97, 10.84, 45.00), (3.29, 13.53, 45.00), (3.61, 16.49, 45.00)),
    ((1.64, 10.26, 45.00), (2.12, 10.26, 45.00), (2.45, 10.26, 45.00), (2.77, 10.82, 45.00), (3.09, 13.37, 45.00), (3.32, 14.58, 45.00), (3.48, 14.58, 45.00), (3.64, 14.71, 45.00), (3.87, 15.27, 45.00)),
)  # fmt: skip


def _place(position: Point, context: DtcContext) -> dict[str, Any]:
    """The coordinates the DTC editor stores for a point; elevation in feet."""
    lat_lon = position.latlng()
    return {
        "x": position.x,
        "y": position.y,
        "lat": lat_lon.lat,
        "lon": lat_lon.lng,
        "elev": round(context.elevation_m(position) * _METERS_TO_FEET),
    }


def _lines(flight: FlightData, context: DtcContext) -> list[dict[str, Any]]:
    return [
        {"points": [_place(start, context), _place(end, context)], "closed": False}
        for start, end in nearest_front_lines(flight, context, MAX_LINES)
    ]


def _threats(flight: FlightData, context: DtcContext) -> list[dict[str, Any]]:
    sites = nearest_threats(flight, context, MAX_REFERENCE_POINTS)
    return [
        {"name": f"THRT {number}", **_place(site.position, context)}
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


# JDAM: the launch acceptability region, as `lookupJDAMLAR` and `calcLARPoints`.


def _bracket(values: tuple[float, ...], value: float) -> tuple[int, int, float]:
    if value <= values[0]:
        return 0, 0, 0.0
    if value >= values[-1]:
        last = len(values) - 1
        return last, last, 0.0
    for i in range(len(values) - 1):
        if values[i] <= value <= values[i + 1]:
            return i, i + 1, (value - values[i]) / (values[i + 1] - values[i])
    raise AssertionError("unreachable")


def _speed_of_sound_kt(alt_ft: float) -> float:
    """ISA: lapse rate below 36,089 ft, isothermal above."""
    temperature = 288.15 - 0.001981 * alt_ft if alt_ft < 36089 else 216.65
    return 38.967 * math.sqrt(temperature)


def lar(speed_kt: float, alt_ft: float) -> tuple[float, float, float]:
    """Min range (nm), max range (nm) and half angle (deg) of the region."""
    mach = speed_kt / _speed_of_sound_kt(alt_ft)
    a1, a2, at = _bracket(_LAR_ALTS_KFT, alt_ft / 1000)
    m1, m2, mt = _bracket(_LAR_MACHS, mach)

    def interpolate(field: int) -> float:
        def at_alt(a: int) -> float:
            row = _LAR_TABLE[a]
            return row[m1][field] * (1 - mt) + row[m2][field] * mt

        return at_alt(a1) * (1 - at) + at_alt(a2) * at

    return interpolate(0), interpolate(1), interpolate(2)


def _region(
    x: float, y: float, heading: float, speed_kt: float, alt_ft: float
) -> tuple[list[dict[str, float]], float, float]:
    """The region behind the target (inner arc, outer arc) and its centre."""
    rmin_nm, rmax_nm, half = lar(speed_kt, alt_ft)
    near, far = rmin_nm * _NMI_TO_METERS, rmax_nm * _NMI_TO_METERS
    centre = math.radians((heading + 180) % 360)
    left, right = centre - math.radians(half), centre + math.radians(half)

    def at(distance: float, angle: float) -> dict[str, float]:
        return {
            "x": x + distance * math.cos(angle),
            "y": y + distance * math.sin(angle),
        }

    points = [at(near, left + (right - left) / 3 * i) for i in range(4)]
    points.append(at(far, right))
    points += [at(far, left + (right - left) / 6 * i) for i in range(5, -1, -1)]
    middle = (near + far) / 2
    return points, x + middle * math.cos(centre), y + middle * math.sin(centre)


def _inactive_target() -> dict[str, Any]:
    """An empty target as the editor saves it."""
    rmin, rmax, half = lar(_DROP_SPEED_KT, _DROP_ALT_FT)
    return {
        "active": False,
        "name": "",
        "elev": 0,
        "attack_heading": 0,
        "drop_alt": _DROP_ALT_FT,
        "drop_spd": _DROP_SPEED_KT,
        "has_impact_angle": False,
        "impact_angle": _IMPACT_ANGLE,
        "has_impact_heading": False,
        "impact_heading": 0,
        "lar_rmin_nmi": rmin,
        "lar_rmax_nmi": rmax,
        "lar_half_angle_deg": half,
    }


def _target(
    name: str,
    position: Point,
    elevation_m: float,
    heading: float,
    speed_kt: int,
    alt_ft: int,
) -> dict[str, Any]:
    polygon, launch_x, launch_y = _region(
        position.x, position.y, heading, speed_kt, alt_ft
    )
    rmin, rmax, half = lar(speed_kt, alt_ft)
    lat_lon = position.latlng()
    return {
        **_inactive_target(),
        "active": True,
        "name": name,
        "x": position.x,
        "y": position.y,
        "lat": lat_lon.lat,
        "lon": lat_lon.lng,
        # In metres, unlike the navigation points.
        "elev": round(elevation_m, 1),
        "attack_heading": round(heading, 1),
        "drop_alt": alt_ft,
        "drop_spd": speed_kt,
        "lar_rmin_nmi": rmin,
        "lar_rmax_nmi": rmax,
        "lar_half_angle_deg": half,
        "lar_polygon": polygon,
        "launch_x": launch_x,
        "launch_y": launch_y,
    }


def _jdam_stations(flight: FlightData) -> list[int]:
    """The JDAM stations (0 for STA 3) that carry a JDAM on the player's jet."""
    if not flight.client_units:
        return []
    pylons = getattr(flight.client_units[0], "pylons", {}) or {}
    stations = []
    for station in range(JDAM_STATIONS):
        clsid = str(pylons.get(_FIRST_JDAM_PYLON + station, {}).get("CLSID", ""))
        if any(name in clsid for name in _JDAM_CLSIDS):
            stations.append(station)
    return stations


def _aim_points(flight: FlightData) -> list[Point]:
    """The aim points of the package target: its standing units, else itself."""
    target = flight.package.target
    if isinstance(target, TheaterGroundObject):
        units: list[Point] = [unit.position for unit in target.strike_targets]
        if units:
            return units[:JDAM_TARGETS_PER_STATION]
    return [target.position]


def _release(flight: FlightData) -> Optional[tuple[float, int, int]]:
    """Attack heading (deg, grid), speed (kt) and altitude (ft) into the target.

    From the leg into the first target waypoint of the flight plan; None without one.
    """
    previous: Optional[FlightWaypoint] = None
    for waypoint in flight.waypoints:
        if "TARGET" in waypoint.waypoint_type.name and previous is not None:
            dx = waypoint.position.x - previous.position.x
            dy = waypoint.position.y - previous.position.y
            heading = math.degrees(math.atan2(dy, dx)) % 360
            speed = round(leg_speed_kmh(previous, waypoint) / 1.852)
            alt = round(previous.alt.feet) or _DROP_ALT_FT
            return heading, speed, alt
        if waypoint.waypoint_type not in (
            FlightWaypointType.DIVERT,
            FlightWaypointType.BULLSEYE,
        ):
            previous = waypoint
    return None


def _jdam(flight: FlightData, context: DtcContext) -> Optional[dict[str, Any]]:
    """Each station with a JDAM gets every aim point, its own one first."""
    stations = _jdam_stations(flight)
    release = _release(flight)
    if not stations or release is None:
        return None
    heading, speed, alt = release
    aims = [
        _target(
            f"TGT{number}", position, context.elevation_m(position), heading, speed, alt
        )
        for number, position in enumerate(_aim_points(flight), 1)
    ]
    table = []
    for station in range(JDAM_STATIONS):
        targets: list[dict[str, Any]] = []
        if station in stations:
            first = stations.index(station) % len(aims)
            targets = aims[first:] + aims[:first]
        targets = targets + [
            _inactive_target() for _ in range(JDAM_TARGETS_PER_STATION - len(targets))
        ]
        table.append({"targets": targets})
    return {"stations": table}


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
        # The bingo and the automatic programs keep the module's defaults.
        data["CMDS"] = {"CMDSProgramSettings": CMDS.program_settings(settings.cmds)}
    if settings.jdam_targets:
        jdam = _jdam(flight, context)
        if jdam is not None:
            data["JDAM"] = jdam
    return DtcCartridge(name=name, unit_type=UNIT_TYPE, data=data)

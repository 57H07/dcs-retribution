"""F/A-18C cartridge: `COMM` presets with names and `WYPT` steerpoints (#191).

The frequencies are the unit's own `Radio` presets, the ones the mission sets: the
cartridge only adds the channel names, which the miz cannot carry. The steerpoints
are the flight's waypoints, numbered as on the kneeboard.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from game.ato.flightwaypointtype import FlightWaypointType
from .cartridge import DtcCartridge, DtcContext, dtc_settings
from .cmds import ALE47

if TYPE_CHECKING:
    from game.ato.flightwaypoint import FlightWaypoint
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import CarrierInfo, MissionData
    from game.radio.radios import RadioFrequency
    from game.radio.tacan import TacanChannel

UNIT_TYPE = "FA-18C_hornet"
#: The countermeasure programs the player may set (#221).
CMDS = ALE47

#: The waypoint database of the jet holds 59 points.
MAX_WAYPOINTS = 59
#: Limits of a waypoint elevation in the DTC editor: -2,000 to 25,000 ft.
_MIN_ALT_M = -2000 * 0.3048
_MAX_ALT_M = 25000 * 0.3048
#: Leg speed when the times do not give one, and the sane range, in km/h.
_DEFAULT_SPEED_KMH = 463.0
_MIN_SPEED_KMH = 150.0
_MAX_SPEED_KMH = 2200.0
#: Reference points, not flown in the route.
_OFF_ROUTE = (FlightWaypointType.DIVERT, FlightWaypointType.BULLSEYE)

#: ARC-210 presets 1-20; G, M, C and S are fixed positions of the selector.
CHANNELS = 20
#: The module's stock presets (MHz), for a unit without a `Radio` table.
_STOCK_PRESETS = [
    305.0, 264.0, 265.0, 256.0, 254.0, 250.0, 270.0, 257.0, 255.0, 262.0,
    259.0, 268.0, 269.0, 260.0, 263.0, 261.0, 267.0, 251.0, 253.0, 266.0,
]  # fmt: skip


def short_name(label: str) -> str:
    """The DTC channel name: at most 5 upper-case letters or digits."""
    return re.sub(r"[^A-Z0-9]", "", label.upper())[:5]


def _frequency_names(flight: FlightData, mission_data: MissionData) -> dict[float, str]:
    """A name for each frequency the channel allocator may have preset, by MHz."""
    names: dict[float, str] = {}

    def name(frequency: Optional[RadioFrequency], label: str) -> None:
        if frequency is not None:
            names.setdefault(round(frequency.mhz, 3), short_name(label))

    def callsign(text: str) -> str:
        return text.split()[0] if text.split() else text

    name(flight.intra_flight_channel, callsign(flight.callsign))
    for support in [*mission_data.awacs, *mission_data.tankers]:
        name(support.freq, callsign(support.callsign))
    for jtac in mission_data.jtacs:
        name(jtac.freq, "JTAC")
    name(flight.package.frequency, "PKG")
    name(flight.departure.atc, "DEP")
    if flight.arrival != flight.departure:
        name(flight.arrival.atc, "ARR")
    if flight.divert is not None:
        name(flight.divert.atc, "DVT")
    return names


#: The FM bands of the ARC-210 (MHz), as the DTC editor tells them apart
#: (`get_Modulation` of COMM/COMM_common.lua); every other band is AM.
_FM_BANDS = ((30.0, 88.0), (156.0, 174.0))


def _modulation(frequency: float) -> int:
    """0 AM, 1 FM."""
    return int(any(low <= frequency < high for low, high in _FM_BANDS))


def _channel(frequency: float, name: str) -> dict[str, Any]:
    return {"frequency": frequency, "modulation": _modulation(frequency), "name": name}


def _comm(flight: FlightData, mission_data: MissionData) -> dict[str, Any]:
    names = _frequency_names(flight, mission_data)
    radio = flight.client_units[0].radio if flight.client_units else None
    comm: dict[str, Any] = {}
    for radio_id in (1, 2):
        presets = dict(enumerate(_STOCK_PRESETS, start=1))
        if radio and radio_id in radio:
            presets.update(radio[radio_id]["channels"])
        table: dict[str, Any] = {"Guard": False}
        for number in range(1, CHANNELS + 1):
            frequency = float(presets[number])
            table[f"Channel_{number}"] = _channel(
                frequency, names.get(round(frequency, 3), f"CH {number}")
            )
        table["Channel_G"] = _channel(243.0, "GUARD")
        table["Channel_M"] = _channel(122.8, "MAN")
        table["Channel_C"] = _channel(30.0, "CUE")
        table["Channel_S"] = _channel(156.05, "MAR")
        comm[f"COMM{radio_id}"] = table
        comm[f"mirror_COMM{radio_id}"] = False
    return comm


def _cockpit_name(waypoint: FlightWaypoint) -> str:
    """The name of the waypoint, folded to the ASCII the displays can show."""
    label = waypoint.display_name or waypoint.name
    folded = label.replace("—", "-").replace("–", "-")
    ascii_only = folded.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_only.split())[:24]


def _seconds_of_day(context: DtcContext, when: Optional[datetime]) -> int:
    """Zulu seconds since midnight of the mission day: the clock of the cartridge."""
    if when is None:
        return 0
    start = context.start_time.replace(tzinfo=context.timezone).astimezone(timezone.utc)
    midnight = start.replace(hour=0, minute=0, second=0, microsecond=0)
    zulu = when.replace(tzinfo=context.timezone).astimezone(timezone.utc)
    return max(0, int((zulu - midnight).total_seconds()))


def _altitude(waypoint: FlightWaypoint) -> tuple[float, int]:
    """Metres and DTC altitude type (1 MSL, 2 AGL), as the miz route gives them."""
    if waypoint.flyover:
        return 0.0, 2
    return waypoint.alt.meters, 2 if waypoint.alt_type == "RADIO" else 1


def leg_speed_kmh(
    previous: Optional[FlightWaypoint], waypoint: FlightWaypoint
) -> float:
    """Ground speed of the leg into `waypoint`, from the times of the flight plan."""
    if previous is None or waypoint.tot is None:
        return _DEFAULT_SPEED_KMH
    depart = previous.departure_time or previous.tot
    if depart is None or waypoint.tot <= depart:
        return _DEFAULT_SPEED_KMH
    seconds = (waypoint.tot - depart).total_seconds()
    speed = previous.position.distance_to_point(waypoint.position) / seconds * 3.6
    return max(_MIN_SPEED_KMH, min(_MAX_SPEED_KMH, speed))


def _carrier(flight: FlightData, mission_data: MissionData) -> Optional[CarrierInfo]:
    """The carrier the flight recovers on, if it lands on one."""
    arrival = flight.arrival
    for carrier in mission_data.carriers:
        # The runway data of a carrier carries its TACAN.
        if arrival.tacan is not None and arrival.tacan == carrier.tacan:
            return carrier
        name = arrival.airfield_name
        if carrier.unit_name in name or name in carrier.unit_name:
            return carrier
    return None


def _nav_settings(
    flight: FlightData, mission_data: MissionData, home: int
) -> dict[str, Any]:
    """Pre-tune the TACAN and ICLS of the recovery: the carrier, else the fields."""
    carrier = _carrier(flight, mission_data)
    tacan: Optional[TacanChannel]
    if carrier is not None:
        tacan = carrier.tacan
        icls = carrier.icls_channel
        acls = carrier.link4_freq.mhz if carrier.link4_freq is not None else None
    else:
        tacan = flight.departure.tacan or flight.arrival.tacan
        icls = flight.arrival.icls
        acls = None
    return {
        "TACAN": {
            "Mode": 1,  # T/R
            "Channel": tacan.number if tacan is not None else 1,
            "ChannelMode": 2 if tacan is not None and tacan.band.value == "Y" else 1,
            "OnOff": tacan is not None,
        },
        "ICLS": {"Channel": icls if icls is not None else 1, "OnOff": icls is not None},
        "ACLS": {
            "Frequency": acls if acls is not None else 225.0,
            "OnOff": acls is not None,
        },
        "AA_Waypoint": {"AA_WP_Number": 59, "AA_WP_Enabled": False},
        "Home_Waypoint": {"FPAS_HOME_WP": home},
        "Altitude_Warning": {"Warn_Alt_Rdr": 500, "Warn_Alt_Baro": 2000},
    }


def _no_offset_aimpoint(number: int) -> dict[str, Any]:
    """The empty offset aimpoint the DTC editor gives each new steerpoint."""
    return {
        "idOA": f"OA{number}",
        "idOA_Line": f"OA{number}Line",
        "isOA": False,
        "OA_Range": 0.0,
        "OA_Bearing": 0.0,
        "OA_X": 0.0,
        "OA_Y": 0.0,
        "OA_Alt": 0.0,
        "OA_DeltaX": 0.0,
        "OA_DeltaY": 0.0,
        "OA_Bearing_Units": 1,  # degrees magnetic
        "OA_Range_Units": 1,  # feet
        "OA_Elevation_Units": 1,  # feet
    }


def _wypt(
    flight: FlightData, mission_data: MissionData, context: DtcContext
) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    route: dict[str, Any] = {}
    home = 1
    target_set = False
    previous: Optional[FlightWaypoint] = None
    # Waypoint 0 of the kneeboard is the take off: steerpoint n is waypoint n.
    for number, waypoint in enumerate(flight.waypoints[1 : MAX_WAYPOINTS + 1], 1):
        on_route = waypoint.waypoint_type not in _OFF_ROUTE
        altitude, altitude_type = _altitude(waypoint)
        point: dict[str, Any] = {
            "wypt_num": number,
            "id": f"STPT{number}",
            "text_note": _cockpit_name(waypoint),
            "note": "",
            "x": waypoint.position.x,
            "y": waypoint.position.y,
            "alt": min(max(altitude, _MIN_ALT_M), _MAX_ALT_M),
            "altitudeType": altitude_type,
            "velocityType": 3,
            "R1": on_route,
            "R2": False,
            "R3": False,
            **_no_offset_aimpoint(number),
        }
        if on_route:
            point["R1_order"] = len(route) + 1
            # One target per route: the first.
            is_target = "TARGET" in waypoint.waypoint_type.name and not target_set
            target_set = target_set or is_target
            route[f"STPT{number}"] = {
                "route_num": 1,
                "wypt_num": number,
                "alt": altitude,
                "altitudeType": altitude_type,
                "speed": leg_speed_kmh(previous, waypoint),
                "ETA": _seconds_of_day(context, waypoint.tot),
                "FIX_Time": waypoint.tot is not None,
                "TGT": is_target,
            }
            previous = waypoint
        if waypoint.waypoint_type is FlightWaypointType.LANDING_POINT:
            home = number
        points.append(point)
    return {
        "NAV_PTS": points,
        "NAV_ROUTE": [route, [], []],
        "NAV_SETTINGS": _nav_settings(flight, mission_data, home),
        "terrain": context.terrain,
        "mirror_NAV_PTS": False,
    }


def build(
    flight: FlightData, mission_data: MissionData, context: DtcContext, name: str
) -> DtcCartridge:
    data: dict[str, Any] = {
        "type": UNIT_TYPE,
        "name": name,
        "terrain": context.terrain,
        "COMM": _comm(flight, mission_data),
        "WYPT": _wypt(flight, mission_data, context),
    }
    changes = dtc_settings(flight).cmds
    if changes:
        # Left out, the jet keeps the module's programs and threat table.
        programs = CMDS.program_settings(changes)
        data["ALR67"] = {
            "CMDS": {"CMDSProgramSettings": {"delay_between_programs": 0, **programs}}
        }
    return DtcCartridge(name=name, unit_type=UNIT_TYPE, data=data)

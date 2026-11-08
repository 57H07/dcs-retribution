"""#191: the data cartridge of a player flight, built from its FlightData."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4
from zipfile import ZipFile

import dcs
import pytest
from dcs import Mission, Point
from dcs.planes import F_14BU, F_15ESE, FA_18C_hornet
from dcs.terrain import Caucasus
from dcs.unit import Skill

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator import dtc
from game.missiongenerator.dtc import DtcContext, DtcThreat, build_cartridge
from game.missiongenerator.missiondata import MissionData
from game.radio.radios import MHz
from game.radio.tacan import TacanBand, TacanChannel
from game.runways import RunwayData
from game.theater.player import Player
from game.utils import Heading, feet

TERRAIN = Caucasus()
START = datetime(2005, 6, 14, 8, 0, 0)
CONTEXT = DtcContext(terrain="Caucasus", start_time=START, timezone=timezone.utc)


def runway(name: str, **kwargs: Any) -> RunwayData:
    return RunwayData(name, Heading.from_degrees(90), "09", **kwargs)


def waypoint(
    name: str,
    kind: FlightWaypointType,
    x: float,
    y: float,
    alt_ft: int = 20000,
    tot: datetime | None = None,
    **kwargs: Any,
) -> FlightWaypoint:
    wpt = FlightWaypoint(name, kind, Point(x, y, TERRAIN), feet(alt_ft), **kwargs)
    wpt.tot = tot
    return wpt


def hornet_radio() -> dict[int, dict[str, dict[int, float]]]:
    stock = {n: 300.0 + n for n in range(1, 21)}
    return {1: {"channels": dict(stock)}, 2: {"channels": dict(stock)}}


def hornet_flight(**overrides: Any) -> Any:
    """A player Hornet flight: what the mission generator hands the export."""
    client = SimpleNamespace(radio=hornet_radio())
    client.radio[2]["channels"][1] = 251.0  # intra-flight
    client.radio[1]["channels"][2] = 270.0  # package
    client.radio[1]["channels"][3] = 251.5  # departure tower
    flight: Any = SimpleNamespace(
        aircraft_type=SimpleNamespace(
            dcs_unit_type=SimpleNamespace(id="FA-18C_hornet")
        ),
        callsign="Enfield 1",
        client_units=[client],
        intra_flight_channel=MHz(251),
        package=SimpleNamespace(frequency=MHz(270)),
        departure=runway("Batumi", atc=MHz(251, 500)),
        arrival=runway("Batumi", atc=MHz(251, 500)),
        divert=None,
        waypoints=[
            waypoint("TAKEOFF", FlightWaypointType.TAKEOFF, 0, 0, alt_ft=0),
            waypoint("JOIN", FlightWaypointType.JOIN, 10000, 0, tot=START),
            waypoint(
                "STRIKE",
                FlightWaypointType.TARGET_POINT,
                40000,
                0,
                tot=START + timedelta(minutes=5),
                custom_name="Bridge — north",
            ),
            waypoint("DIVERT", FlightWaypointType.DIVERT, 0, 5000, alt_ft=0),
            waypoint("LANDING", FlightWaypointType.LANDING_POINT, 0, 0, alt_ft=0),
        ],
    )
    for key, value in overrides.items():
        setattr(flight, key, value)
    return flight


def test_a_hornet_cartridge_carries_the_presets_of_the_mission_with_names() -> None:
    cartridge = build_cartridge(hornet_flight(), MissionData(), CONTEXT)

    assert cartridge is not None
    comm = cartridge.data["COMM"]
    assert comm["COMM2"]["Channel_1"] == {
        "frequency": 251.0,
        "modulation": 0,
        "name": "ENFIE",
    }
    assert comm["COMM1"]["Channel_2"]["name"] == "PKG"
    assert comm["COMM1"]["Channel_3"]["name"] == "DEP"
    assert comm["COMM1"]["Channel_20"] == {
        "frequency": 320.0,
        "modulation": 0,
        "name": "CH 20",
    }


def test_the_fixed_positions_of_the_selector_are_those_of_the_module() -> None:
    cartridge = build_cartridge(hornet_flight(), MissionData(), CONTEXT)

    assert cartridge is not None
    comm1 = cartridge.data["COMM"]["COMM1"]
    # The values of the module's own DTC editor (COMM/COMM_common.lua).
    assert comm1["Channel_G"] == {"frequency": 243.0, "modulation": 0, "name": "GUARD"}
    assert comm1["Channel_M"] == {"frequency": 122.8, "modulation": 0, "name": "MAN"}
    assert comm1["Channel_C"] == {"frequency": 30.0, "modulation": 1, "name": "CUE"}
    assert comm1["Channel_S"] == {"frequency": 156.05, "modulation": 1, "name": "MAR"}


def test_presets_are_fm_in_the_fm_bands_of_the_radio_only() -> None:
    flight = hornet_flight()
    channels = flight.client_units[0].radio[1]["channels"]
    channels[4], channels[5], channels[6] = 40.5, 121.5, 160.0

    cartridge = build_cartridge(flight, MissionData(), CONTEXT)

    assert cartridge is not None
    comm1 = cartridge.data["COMM"]["COMM1"]
    assert [comm1[f"Channel_{n}"]["modulation"] for n in (4, 5, 6)] == [1, 0, 1]


def test_each_steerpoint_has_the_empty_offset_aimpoint_of_the_editor() -> None:
    cartridge = build_cartridge(hornet_flight(), MissionData(), CONTEXT)

    assert cartridge is not None
    point = cartridge.data["WYPT"]["NAV_PTS"][1]
    assert point["idOA"] == "OA2"
    assert point["idOA_Line"] == "OA2Line"
    assert point["isOA"] is False
    assert point["OA_Bearing_Units"] == 1


def test_steerpoint_n_is_waypoint_n_of_the_kneeboard() -> None:
    cartridge = build_cartridge(hornet_flight(), MissionData(), CONTEXT)

    assert cartridge is not None
    wypt = cartridge.data["WYPT"]
    points = wypt["NAV_PTS"]
    assert [(p["id"], p["text_note"]) for p in points] == [
        ("STPT1", "JOIN"),
        ("STPT2", "Bridge - north"),
        ("STPT3", "DIVERT"),
        ("STPT4", "LANDING"),
    ]
    assert (points[1]["x"], points[1]["y"]) == (40000, 0)
    assert points[0]["alt"] == feet(20000).meters
    # The divert is a reference point: not flown in route 1.
    assert [p["R1"] for p in points] == [True, True, False, True]
    route = wypt["NAV_ROUTE"][0]
    assert list(route) == ["STPT1", "STPT2", "STPT4"]
    assert route["STPT2"]["TGT"] is True
    assert route["STPT1"]["ETA"] == 8 * 3600
    assert route["STPT2"]["ETA"] == 8 * 3600 + 300
    # 30 km in 5 minutes.
    assert route["STPT2"]["speed"] == 360.0
    assert wypt["NAV_SETTINGS"]["Home_Waypoint"] == {"FPAS_HOME_WP": 4}


def test_the_tacan_of_the_departure_field_is_pre_tuned() -> None:
    flight = hornet_flight(
        departure=runway("Batumi", tacan=TacanChannel(16, TacanBand.X))
    )

    cartridge = build_cartridge(flight, MissionData(), CONTEXT)

    assert cartridge is not None
    settings = cartridge.data["WYPT"]["NAV_SETTINGS"]
    assert settings["TACAN"] == {
        "Mode": 1,
        "Channel": 16,
        "ChannelMode": 1,
        "OnOff": True,
    }
    assert settings["ICLS"] == {"Channel": 1, "OnOff": False}


def test_a_module_without_cartridge_gets_none() -> None:
    flight = hornet_flight(
        aircraft_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-15ESE"))
    )
    assert build_cartridge(flight, MissionData(), CONTEXT) is None


def test_the_cartridge_file_is_the_json_dcs_reads() -> None:
    cartridge = build_cartridge(hornet_flight(), MissionData(), CONTEXT)

    assert cartridge is not None
    assert cartridge.name == "Retribution Enfield 1"
    assert cartridge.file_name == "Retribution Enfield 1.dtc"
    payload = json.loads(cartridge.to_json())
    assert payload["name"] == "Retribution Enfield 1"
    assert payload["type"] == "FA-18C_hornet"
    assert payload["data"]["terrain"] == "Caucasus"
    assert payload["data"]["type"] == "FA-18C_hornet"


# F-14BU: the route comes from the miz; the cartridge adds the front and the threats.


def tomcat_flight() -> Any:
    flight = hornet_flight(
        aircraft_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-14BU")),
        friendly=Player.BLUE,
    )
    flight.package.target = SimpleNamespace(position=Point(40000, 0, TERRAIN))
    return flight


def threat(name: str, x: float, owner: Player = Player.RED) -> DtcThreat:
    return DtcThreat(name=name, position=Point(x, 0, TERRAIN), owner=owner)


def test_a_tomcat_cartridge_draws_the_front_and_the_enemy_air_defenses() -> None:
    front = (Point(30000, -10000, TERRAIN), Point(30000, 10000, TERRAIN))
    context = DtcContext(
        terrain="Caucasus",
        start_time=START,
        timezone=timezone.utc,
        front_lines=(front,),
        air_defenses=(
            threat("Far site", 90000),
            threat("Our Patriot", 41000, owner=Player.BLUE),
            threat("Near site", 45000),
        ),
    )

    cartridge = build_cartridge(tomcat_flight(), MissionData(), context)

    assert cartridge is not None
    payload = json.loads(cartridge.to_json())
    assert payload["type"] == "F-14BU"
    data = payload["data"]
    assert data["type"] == "F-14BU"
    assert data["cartridge_name"] == "Retribution Enfield 1"
    assert len(data["NAV"]) == 12
    plan = data["NAV"][0]
    # Plan 1 is the route of the mission editor: the miz already carries it.
    assert plan["waypoints"] == []
    assert plan["route_as_line"] is False
    [line] = plan["lines"]
    assert line["closed"] is False
    assert [(p["x"], p["y"]) for p in line["points"]] == [
        (30000, -10000),
        (30000, 10000),
    ]
    lat_lon = front[0].latlng()
    assert (line["points"][0]["lat"], line["points"][0]["lon"]) == (
        lat_lon.lat,
        lat_lon.lng,
    )
    # Hostile sites only, nearest to the target of the package first.
    points = plan["additional_points"]
    assert [(p["name"], p["x"]) for p in points] == [
        ("THRT 1", 45000),
        ("THRT 2", 90000),
    ]
    assert all(p["waypoints"] == [] for p in data["NAV"][1:])


def test_a_tomcat_cartridge_keeps_to_the_limits_of_the_jet() -> None:
    fronts = tuple(
        (Point(1000.0 * n, 0, TERRAIN), Point(1000.0 * n, 500, TERRAIN))
        for n in range(6)
    )
    sites = tuple(threat(f"Site {n}", 40000 + 100 * n) for n in range(30))
    context = DtcContext(
        terrain="Caucasus",
        start_time=START,
        timezone=timezone.utc,
        front_lines=fronts,
        air_defenses=sites,
    )

    cartridge = build_cartridge(tomcat_flight(), MissionData(), context)

    assert cartridge is not None
    plan = cartridge.data["NAV"][0]
    assert len(plan["lines"]) == 4
    assert len(plan["additional_points"]) == 20


# Mission generation: the cartridges go into the .miz and next to it.


def generated_flight(mission: Mission, unit_type: Any, name: str) -> Any:
    """A FlightData-like flight with real pydcs units: one player, one AI."""
    country = mission.country(dcs.countries.USA.name)
    group = mission.flight_group_inflight(
        country, name, unit_type, Point(0, 0, mission.terrain), 6000, group_size=2
    )
    group.units[0].skill = Skill.Client
    flight = hornet_flight(
        aircraft_type=SimpleNamespace(dcs_unit_type=unit_type),
        units=group.units,
        client_units=[group.units[0]],
        callsign=name,
        flight_id=uuid4(),
    )
    return flight


def mission_units(miz: Path) -> dict[str, dict[str, Any]]:
    with ZipFile(miz) as archive:
        text = archive.read("mission").decode("utf-8")
    units: dict[str, dict[str, Any]] = {}
    for coalition in dcs.lua.loads(text)["mission"]["coalition"].values():
        for country in coalition["country"].values():
            for group in country.get("plane", {}).get("group", {}).values():
                for unit in group["units"].values():
                    units[unit["name"]] = unit
    return units


def test_a_player_hornet_gets_its_cartridge_in_the_miz_and_next_to_it(
    tmp_path: Path,
) -> None:
    mission = Mission(Caucasus())
    flight = generated_flight(mission, FA_18C_hornet, "Enfield 1")
    mission_data = MissionData(flights=[flight])
    miz = tmp_path / "retribution_nextturn.miz"

    cartridges = dtc.prepare(mission_data, CONTEXT)
    mission.save(str(miz))
    dtc.write(cartridges, miz, mission)

    with ZipFile(miz) as archive:
        embedded = json.loads(archive.read("DTC/Retribution Enfield 1.dtc"))
    assert embedded["type"] == "FA-18C_hornet"
    player, wingman = flight.units
    units = mission_units(miz)
    assert units[player.name]["DTC"] == {
        "Cartridges": {1: {"name": "Retribution Enfield 1", "default": True}},
        "AutoLoad": True,
    }
    assert "DTC" not in units[wingman.name]
    copy = dtc.cartridge_file(miz, flight.flight_id)
    assert copy == tmp_path / "retribution_nextturn_DTC" / "Retribution Enfield 1.dtc"
    assert json.loads(copy.read_text(encoding="utf-8")) == embedded


def test_a_flight_of_another_module_generates_its_mission_as_before(
    tmp_path: Path,
) -> None:
    mission = Mission(Caucasus())
    flight = generated_flight(mission, F_15ESE, "Dude 1")
    miz = tmp_path / "retribution_nextturn.miz"

    cartridges = dtc.prepare(MissionData(flights=[flight]), CONTEXT)
    mission.save(str(miz))
    dtc.write(cartridges, miz, mission)

    with ZipFile(miz) as archive:
        assert not [n for n in archive.namelist() if n.startswith("DTC/")]
    assert all("DTC" not in u for u in mission_units(miz).values())
    assert dtc.cartridge_file(miz, flight.flight_id) is None


def test_the_cartridges_of_the_last_mission_replace_the_previous_ones(
    tmp_path: Path,
) -> None:
    miz = tmp_path / "retribution_nextturn.miz"
    first = Mission(Caucasus())
    old = generated_flight(first, FA_18C_hornet, "Enfield 1")
    cartridges = dtc.prepare(MissionData(flights=[old]), CONTEXT)
    first.save(str(miz))
    dtc.write(cartridges, miz, first)

    second = Mission(Caucasus())
    new = generated_flight(second, FA_18C_hornet, "Uzi 1")
    cartridges = dtc.prepare(MissionData(flights=[new]), CONTEXT)
    second.save(str(miz))
    dtc.write(cartridges, miz, second)

    assert dtc.cartridge_file(miz, old.flight_id) is None
    assert dtc.cartridge_file(miz, new.flight_id) is not None
    assert [p.name for p in (tmp_path / "retribution_nextturn_DTC").glob("*.dtc")] == [
        "Retribution Uzi 1.dtc"
    ]


def test_a_cartridge_that_cannot_be_embedded_leaves_the_mission_as_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mission = Mission(Caucasus())
    flight = generated_flight(mission, FA_18C_hornet, "Enfield 1")
    miz = tmp_path / "retribution_nextturn.miz"
    cartridges = dtc.prepare(MissionData(flights=[flight]), CONTEXT)
    mission.save(str(miz))

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise OSError("disk full")

    monkeypatch.setattr(dtc.export, "ZipFile", broken)
    dtc.write(cartridges, miz, mission)

    assert all("DTC" not in u for u in mission_units(miz).values())
    assert dtc.cartridge_file(miz, flight.flight_id) is None


def test_a_carrier_recovery_pre_tunes_the_tacan_icls_and_acls_of_the_boat() -> None:
    boat_tacan = TacanChannel(74, TacanBand.X)
    carrier: Any = SimpleNamespace(
        unit_name="CVN-71 Theodore Roosevelt",
        tacan=boat_tacan,
        icls_channel=11,
        link4_freq=MHz(336),
    )
    flight = hornet_flight(
        departure=runway("Batumi", tacan=TacanChannel(16, TacanBand.X)),
        arrival=runway("Carrier Strike Group 8", tacan=boat_tacan, icls=11),
    )
    mission_data = MissionData()
    mission_data.carriers.append(carrier)

    cartridge = build_cartridge(flight, mission_data, CONTEXT)

    assert cartridge is not None
    settings = cartridge.data["WYPT"]["NAV_SETTINGS"]
    assert settings["TACAN"]["Channel"] == 74
    assert settings["ICLS"] == {"Channel": 11, "OnOff": True}
    assert settings["ACLS"] == {"Frequency": 336.0, "OnOff": True}

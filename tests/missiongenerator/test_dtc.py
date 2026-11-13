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
from dcs.planes import F_14BU, F_15ESE, F_16C_50, FA_18C_hornet
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
from game.squadrons.dtcsettings import DtcSettings
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
        squadron=SimpleNamespace(dtc=DtcSettings()),
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


def threat(
    name: str, x: float, owner: Player = Player.RED, threat_range_m: float = 0.0
) -> DtcThreat:
    return DtcThreat(
        name=name,
        position=Point(x, 0, TERRAIN),
        owner=owner,
        threat_range_m=threat_range_m,
    )


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


# F-16C: route and presets come from the miz; the cartridge adds the front and threats.


def viper_flight() -> Any:
    flight = tomcat_flight()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    return flight


def test_a_viper_cartridge_draws_the_front_and_the_enemy_air_defenses() -> None:
    fronts = (
        (Point(30000, -10000, TERRAIN), Point(30000, 10000, TERRAIN)),
        (Point(90000, -10000, TERRAIN), Point(90000, 10000, TERRAIN)),
    )
    context = DtcContext(
        terrain="Caucasus",
        start_time=START,
        timezone=timezone.utc,
        front_lines=fronts,
        air_defenses=(
            threat("Far site", 90000, threat_range_m=25000.0),
            threat("Our Patriot", 41000, owner=Player.BLUE),
            threat("Near site", 45000, threat_range_m=50000.0),
        ),
    )

    cartridge = build_cartridge(viper_flight(), MissionData(), context)

    assert cartridge is not None
    payload = json.loads(cartridge.to_json())
    assert payload["type"] == "F-16C_50"
    data = payload["data"]
    assert (data["type"], data["terrain"]) == ("F-16C_50", "Caucasus")
    mpd = data["MPD"]
    # The miz already carries the route and the presets: the jet mirrors them.
    assert mpd["mirror_NAV_PTS"] is True
    assert mpd["mirror_DEST"] is True
    assert data["COMM"] == {"mirror_COMM1": True, "mirror_COMM2": True}
    assert mpd["mirror_GEO_LINES"] is False
    assert mpd["mirror_THREAT_PTS"] is False
    # Each front line, nearest the target first, on a line of its own.
    lines = mpd["GEO_LINES"]
    assert [(p["id"], p["x"], p["y"]) for p in lines] == [
        ("GEO_LINES31", 30000, -10000),
        ("GEO_LINES32", 30000, 10000),
        ("GEO_LINES33", 90000, -10000),
        ("GEO_LINES34", 90000, 10000),
    ]
    assert [[p[f"L{n}"] for n in (1, 2, 3, 4)] for p in lines] == [
        [True, False, False, False],
        [True, False, False, False],
        [False, True, False, False],
        [False, True, False, False],
    ]
    assert [p["number"] for p in lines] == [1, 2, 3, 4]
    # Hostile sites only, nearest the target first, ringed at their reach.
    threats = mpd["THREAT_PTS"]
    assert [
        (p["id"], p["number"], p["x"], p["text"], p["threatName"], p["radius"])
        for p in threats
    ] == [
        ("THREAT_PTS56", 1, 45000, "T1", "Near site", 50000.0),
        ("THREAT_PTS57", 2, 90000, "T2", "Far site", 25000.0),
    ]
    assert all(p["ring"] and p["def_num"] == 1 for p in threats)


def test_a_viper_cartridge_keeps_to_the_limits_of_the_jet() -> None:
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

    cartridge = build_cartridge(viper_flight(), MissionData(), context)

    assert cartridge is not None
    mpd = cartridge.data["MPD"]
    # 4 lines of the HSD; 15 threat points, 56 to 70.
    assert len(mpd["GEO_LINES"]) == 8
    assert len(mpd["THREAT_PTS"]) == 15
    # A site of unknown reach gets the ring of the editor's custom threat.
    assert {p["radius"] for p in mpd["THREAT_PTS"]} == {37040.0}


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


def test_a_player_viper_gets_its_cartridge_next_to_a_hornet(tmp_path: Path) -> None:
    mission = Mission(Caucasus())
    hornet = generated_flight(mission, FA_18C_hornet, "Enfield 1")
    viper = generated_flight(mission, F_16C_50, "Uzi 1")
    viper.friendly = Player.BLUE
    viper.package.target = SimpleNamespace(position=Point(40000, 0, TERRAIN))
    miz = tmp_path / "retribution_nextturn.miz"

    cartridges = dtc.prepare(MissionData(flights=[hornet, viper]), CONTEXT)
    mission.save(str(miz))
    dtc.write(cartridges, miz, mission)

    with ZipFile(miz) as archive:
        embedded = json.loads(archive.read("DTC/Retribution Uzi 1.dtc"))
        assert "DTC/Retribution Enfield 1.dtc" in archive.namelist()
    assert embedded["type"] == "F-16C_50"
    assert mission_units(miz)[viper.units[0].name]["DTC"]["Cartridges"] == {
        1: {"name": "Retribution Uzi 1", "default": True}
    }
    copy = dtc.cartridge_file(miz, viper.flight_id)
    assert copy is not None
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


# What the player sets for the cartridges of a squadron (#221).


def test_a_cartridge_keeps_the_cmds_of_the_module_until_the_player_changes_them() -> (
    None
):
    for flight in (hornet_flight(), tomcat_flight(), viper_flight()):
        cartridge = build_cartridge(flight, MissionData(), CONTEXT)
        assert cartridge is not None
        data = cartridge.data
        assert "ALR67" not in data and "CMDS" not in data
        assert "CMDS" not in data.get("MPD", {})


def test_a_hornet_cartridge_carries_the_cmds_programs_of_its_squadron() -> None:
    flight = hornet_flight()
    flight.squadron.dtc.cmds = {"MAN_1": {"chaff_quantity": 4, "flare_quantity": 3}}

    cartridge = build_cartridge(flight, MissionData(), CONTEXT)

    assert cartridge is not None
    programs = cartridge.data["ALR67"]["CMDS"]["CMDSProgramSettings"]
    assert programs["delay_between_programs"] == 0
    assert programs["MAN_1"]["Chaff"] == {"Quantity": 4, "Repeat": 10, "Interval": 1.0}
    assert programs["MAN_1"]["Flare"] == {"Quantity": 3}
    # The other programs are written whole, with the module's values.
    assert programs["BYP"]["Chaff"] == {"Quantity": 2, "Repeat": 1, "Interval": 1.0}
    assert len(programs) == 11


def test_a_tomcat_cartridge_carries_the_cmds_programs_of_its_squadron() -> None:
    flight = tomcat_flight()
    flight.squadron.dtc.cmds = {
        "PROG_1": {"chaff_salvo_interval": 0.25, "priority": 3},
        # The ALE-47 programs of an older version: ignored.
        "AUTO_1": {"chaff_interval": 0.5},
    }

    cartridge = build_cartridge(flight, MissionData(), CONTEXT)

    assert cartridge is not None
    # The format of `F-14BU_DTC.lua`, as a cartridge saved by DCS has it.
    programs = cartridge.data["CMDS"]["CMDSProgramSettings"]
    assert set(programs) == {f"PROG_{n}" for n in range(1, 9)}
    assert programs["PROG_1"]["Priority"] == 3
    assert programs["PROG_1"]["Chaff"] == {
        "BurstQuantity": 2,
        "BurstInterval": 0.2,
        "SalvoQuantity": 8,
        "SalvoInterval": 0.25,
    }
    assert programs["PROG_5"]["Chaff"]["BurstQuantity"] == 4


def test_a_viper_cartridge_carries_the_cmds_programs_of_its_squadron() -> None:
    flight = viper_flight()
    flight.squadron.dtc.cmds = {"MAN1": {"flare_salvo_quantity": 4}}

    cartridge = build_cartridge(flight, MissionData(), CONTEXT)

    assert cartridge is not None
    programs = cartridge.data["MPD"]["CMDS"]["CMDSProgramSettings"]
    assert programs["MAN1"]["Flare"]["SalvoQuantity"] == 4
    assert programs["MAN1"]["Chaff"]["SalvoQuantity"] == 10
    assert set(programs) == {p for p, _ in dtc.cmds.VIPER.programs}


def test_without_threats_a_cartridge_leaves_the_displays_to_the_module() -> None:
    front = (Point(30000, -10000, TERRAIN), Point(30000, 10000, TERRAIN))
    context = DtcContext(
        terrain="Caucasus",
        start_time=START,
        timezone=timezone.utc,
        front_lines=(front,),
        air_defenses=(threat("Near site", 45000),),
    )
    tomcat, viper = tomcat_flight(), viper_flight()
    tomcat.squadron.dtc.threats = False
    viper.squadron.dtc.threats = False

    tomcat_cartridge = build_cartridge(tomcat, MissionData(), context)
    viper_cartridge = build_cartridge(viper, MissionData(), context)

    assert tomcat_cartridge is not None and viper_cartridge is not None
    plan = tomcat_cartridge.data["NAV"][0]
    assert plan["lines"] == [] and plan["additional_points"] == []
    mpd = viper_cartridge.data["MPD"]
    assert "GEO_LINES" not in mpd and "THREAT_PTS" not in mpd
    assert mpd["mirror_NAV_PTS"] is True


def test_without_auto_load_the_pilot_loads_the_cartridge(tmp_path: Path) -> None:
    mission = Mission(Caucasus())
    flight = generated_flight(mission, FA_18C_hornet, "Enfield 1")
    flight.squadron.dtc.auto_load = False
    miz = tmp_path / "retribution_nextturn.miz"

    cartridges = dtc.prepare(MissionData(flights=[flight]), CONTEXT)
    mission.save(str(miz))
    dtc.write(cartridges, miz, mission)

    player = flight.units[0]
    assert mission_units(miz)[player.name]["DTC"]["AutoLoad"] is False


def apache_flight() -> Any:
    flight = tomcat_flight()
    flight.aircraft_type = SimpleNamespace(
        dcs_unit_type=SimpleNamespace(id="AH-64D_BLK_II")
    )
    return flight


def test_an_apache_cartridge_draws_the_front_and_the_enemy_air_defenses() -> None:
    front = (Point(30000, -10000, TERRAIN), Point(30000, 10000, TERRAIN))
    context = DtcContext(
        terrain="Caucasus",
        start_time=START,
        timezone=timezone.utc,
        front_lines=(front,),
        air_defenses=(
            threat("Far site", 90000),
            threat("Our Patriot", 41000, owner=Player.BLUE),
            threat("SA-6 — Near site", 45000),
        ),
    )

    cartridge = build_cartridge(apache_flight(), MissionData(), context)

    assert cartridge is not None
    assert cartridge.unit_type == "AH-64D_BLK_II"
    nav = cartridge.data["NAV"]
    assert nav["MissionFile"] == 1
    mission = nav["Mission_1"]
    # Waypoints and control measures stay those of the mission.
    assert set(mission) == {"Lines", "Points"}
    assert set(mission["Points"]) == {"TGT"}
    [line] = mission["Lines"]
    assert line["type_num"] == 4  # FLOT
    assert line["vertices"] == [
        {"x": 30000, "y": -10000},
        {"x": 30000, "y": 10000},
    ]
    targets = mission["Points"]["TGT"]
    assert targets["isEnabled"] is True
    assert [(p["num"], p["text"], p["note"]) for p in targets["POINTS"]] == [
        (1, "T01", "SA-6 Near site"),
        (2, "T02", "Far site"),
    ]
    assert {p["id"] for p in targets["POINTS"]} == {2}


def test_without_threats_an_apache_cartridge_keeps_the_mission_points() -> None:
    flight = apache_flight()
    flight.squadron.dtc.threats = False

    cartridge = build_cartridge(flight, MissionData(), CONTEXT)

    assert cartridge is not None
    assert cartridge.data["NAV"]["Mission_1"] == {}


# F-14BU JDAM targets (#221), checked against a cartridge saved by the DTC editor of
# DCS (F14_Tuto_JDAM.miz): STA 4 target 1, launch point left at the region centre.
SAVED_TARGET: dict[str, Any] = {
    "x": -328733.16352422,
    "y": 631364.85975003,
    "attack_heading": 327.9,
    "drop_alt": 20000,
    "drop_spd": 450,
    "lar_rmin_nmi": 1.5712031862492,
    "lar_rmax_nmi": 7.2509806211745,
    "lar_half_angle_deg": 44.983734395416,
    "launch_x": -335653.59238992,
    "launch_y": 635706.03659372,
    "lar_polygon_0": (-329383.5971623, 634201.10191374),
    "lar_polygon_10": (-331734.8642249, 644453.89695797),
}


def test_the_jdam_region_is_the_one_of_the_dtc_editor() -> None:
    from game.missiongenerator.dtc import tomcat

    saved = SAVED_TARGET
    assert tomcat.lar(450, 20000) == pytest.approx(
        (saved["lar_rmin_nmi"], saved["lar_rmax_nmi"], saved["lar_half_angle_deg"])
    )
    # 35,000 ft and 400 kt, STA 3 of the same cartridge.
    assert tomcat.lar(400, 35000) == pytest.approx(
        (2.2690993429096, 7.9636799383663, 45.0)
    )
    target = tomcat._target(
        "TGT1", Point(saved["x"], saved["y"], TERRAIN), 10.0, 327.9, 450, 20000
    )
    assert target["launch_x"] == pytest.approx(saved["launch_x"], abs=0.01)
    assert target["launch_y"] == pytest.approx(saved["launch_y"], abs=0.01)
    polygon = target["lar_polygon"]
    assert len(polygon) == 11
    assert (polygon[0]["x"], polygon[0]["y"]) == pytest.approx(
        saved["lar_polygon_0"], abs=0.01
    )
    assert (polygon[10]["x"], polygon[10]["y"]) == pytest.approx(
        saved["lar_polygon_10"], abs=0.01
    )
    assert target["elev"] == 10.0 and target["active"] is True


def jdam_tomcat(*pylons: int) -> Any:
    flight = tomcat_flight()
    flight.client_units[0].pylons = {
        pylon: {"CLSID": "{BRU-32 GBU-38}"} for pylon in pylons
    }
    return flight


def test_each_jdam_station_gets_the_aim_points_its_own_first() -> None:
    flight = jdam_tomcat(4, 6)  # STA 3 and STA 5
    context = DtcContext(
        terrain="Caucasus",
        start_time=START,
        timezone=timezone.utc,
        ground_height=lambda p: 42.0,
    )

    cartridge = build_cartridge(flight, MissionData(), context)

    assert cartridge is not None
    stations = cartridge.data["JDAM"]["stations"]
    assert len(stations) == 4
    assert all(len(s["targets"]) == 8 for s in stations)
    sta3 = stations[0]["targets"][0]
    assert sta3["active"] is True and sta3["name"] == "TGT1"
    assert (sta3["x"], sta3["y"]) == (40000, 0)  # the package target
    assert sta3["elev"] == 42.0
    # The leg into the target: north, 30 km in 5 minutes, at 20,000 ft.
    assert sta3["attack_heading"] == 0
    assert sta3["drop_spd"] == 194
    assert sta3["drop_alt"] == 20000
    assert stations[2]["targets"][0]["active"] is True
    assert stations[1]["targets"][0]["active"] is False
    assert stations[3]["targets"][0]["active"] is False


def test_no_jdam_targets_without_a_jdam_or_when_turned_off() -> None:
    without = build_cartridge(jdam_tomcat(), MissionData(), CONTEXT)
    assert without is not None and "JDAM" not in without.data
    flight = jdam_tomcat(4)
    flight.squadron.dtc.jdam_targets = False
    turned_off = build_cartridge(flight, MissionData(), CONTEXT)
    assert turned_off is not None and "JDAM" not in turned_off.data

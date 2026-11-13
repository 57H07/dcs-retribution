"""WEB-04.5: the Radios & TACAN tab of a flight, on a real generated game."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from zipfile import ZipFile

from dcs import Mission

import pytest

from game import Game, persistency
from game.ato import Flight, FlightType, Package
from game.commands import CommandError
from game.commands.baseradios import BaseRadios, radio_warnings, set_base_radios
from game.commands.flightradios import (
    datalink_fields,
    flight_radio_warnings,
    flight_tacan_warnings,
    frequency_ranges,
    has_flight_tacan,
    package_radio_warnings,
    set_datalink_value,
    set_flight_frequency,
    set_flight_tacan,
    set_package_frequency,
)
from game.commands.mission import MISSION_FILE_NAME
from game.commands.packageflights import add_flight
from game.commands.packages import create_package
from game.commands.transfers import can_plan_transport_mission
from game.missiongenerator import dtc
from game.missiongenerator.dtc import DtcCartridge
from game.native import NativeContext
from game.radio.datalink import DataLinkKey
from game.radio.radios import RadioFrequency
from game.radio.tacan import TacanBand, TacanChannel
from game.server import GameContext
from game.server.eventstream import EventStream
from game.server.packages.models import PackageDetailJs
from game.sim import GameUpdateEvents
from game.squadrons import Squadron
from game.squadrons.dtcsettings import DtcSettings
from game.theater import ControlPoint, Fob, TheaterGroundObject
from game.theater.theatergroundobject import SamGroundObject
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)
from tests.server.test_native_routes import FakeBridge
from tests.server.test_packages_routes import _request

F16 = "F-16CM Fighting Falcon (Block 50)"
KC135 = "KC-135 Stratotanker"


@pytest.fixture(scope="module")
def reference_game(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Game]:
    missing: Path = tmp_path_factory.mktemp("no_user_payloads")
    with repository_payloads_only(missing):
        yield generate_reference_game()


@pytest.fixture
def game(reference_game: Game, monkeypatch: pytest.MonkeyPatch) -> Iterator[Game]:
    sim = SimpleNamespace(
        current_time_in_sim_if_game_loaded=reference_game.conditions.start_time
    )
    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(game=reference_game, sim_controller=sim),
        raising=False,
    )
    yield reference_game
    reference_game.blue.ato.clear()
    for cp in reference_game.theater.controlpoints:
        if isinstance(cp, Fob):
            cp.frequency = None


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[GameUpdateEvents]:
    events: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", events.append)
    return events


def _now(game: Game) -> datetime:
    return game.conditions.start_time


def _sam(game: Game) -> TheaterGroundObject:
    return next(
        tgo
        for tgo in game.theater.ground_objects
        if isinstance(tgo, SamGroundObject) and not tgo.is_friendly(game.blue.player)
    )


def _squadron(game: Game, aircraft: str) -> Squadron:
    return next(
        s
        for s in game.blue.air_wing.iter_squadrons()
        if s.aircraft.display_name == aircraft
    )


def _flight(game: Game) -> Flight:
    package = create_package(game, _sam(game), _now(game))
    return add_flight(
        game, package, FlightType.SEAD, _squadron(game, F16), 2, _now(game)
    )


def _tanker(game: Game) -> Flight:
    squadron = _squadron(game, KC135)
    package = create_package(game, game.theater.player_points()[0], _now(game))
    return add_flight(game, package, FlightType.REFUELING, squadron, 1, _now(game))


def _path(flight: Flight, suffix: str = "") -> str:
    return f"/packages/{flight.package.id}/flights/{flight.id}/radios{suffix}"


# --- frequency -----------------------------------------------------------------


def test_a_flight_frequency_stays_within_its_radio(game: Game) -> None:
    flight = _flight(game)
    events = GameUpdateEvents()
    ranges = frequency_ranges(flight)
    good = ranges[0].minimum.mhz
    set_flight_frequency(flight, good, None, events)
    assert flight.frequency is not None and flight.frequency.mhz == good
    assert flight.frequency.modulation is ranges[0].modulation
    assert flight in events.updated_flights

    with pytest.raises(CommandError, match="cannot tune"):
        set_flight_frequency(flight, 5.0, None, GameUpdateEvents())
    assert flight.frequency.mhz == good

    set_flight_frequency(flight, None, None, GameUpdateEvents())
    assert flight.frequency is None


def test_a_modulation_the_radio_has_not_there_is_refused(game: Game) -> None:
    flight = _flight(game)
    first = frequency_ranges(flight)[0]
    other = "FM" if first.modulation.name == "AM" else "AM"
    mhz = first.minimum.mhz
    covering = {
        r.modulation.name
        for r in frequency_ranges(flight)
        if r.minimum.mhz <= mhz < r.maximum.mhz
    }
    if other not in covering:
        with pytest.raises(CommandError, match=f"no {other}"):
            set_flight_frequency(flight, mhz, other, GameUpdateEvents())
    with pytest.raises(CommandError, match="Unknown modulation"):
        set_flight_frequency(flight, mhz, "SSB", GameUpdateEvents())


def test_package_frequency_limits(game: Game) -> None:
    flight = _flight(game)
    package = flight.package
    events = GameUpdateEvents()
    set_package_frequency(package, 251.25, events)
    assert package.frequency == RadioFrequency(251_250_000)
    assert flight in events.updated_flights
    with pytest.raises(CommandError, match="frequency must be"):
        set_package_frequency(package, 500, GameUpdateEvents())
    set_package_frequency(package, None, GameUpdateEvents())
    assert package.frequency is None


# --- warnings ------------------------------------------------------------------


def _fob(game: Game) -> ControlPoint:
    return next(
        cp
        for cp in game.theater.control_points_for(game.blue.player)
        if isinstance(cp, Fob)
    )


def test_double_booking_is_shared_with_the_base_panel(game: Game) -> None:
    flight = _flight(game)
    mhz = frequency_ranges(flight)[0].minimum.mhz
    set_flight_frequency(flight, mhz, "AM", GameUpdateEvents())
    assert flight_radio_warnings(game, flight) == []

    fob = _fob(game)
    set_base_radios(fob, BaseRadios(frequency_mhz=mhz), GameUpdateEvents())
    assert "double booked" in flight_radio_warnings(game, flight)[0]
    assert "double booked" in radio_warnings(game, fob)[0]

    set_base_radios(fob, BaseRadios(), GameUpdateEvents())
    assert flight_radio_warnings(game, flight) == []
    assert radio_warnings(game, fob) == []


def test_a_flight_on_its_package_frequency_is_not_double_booked(game: Game) -> None:
    flight = _flight(game)
    package = flight.package
    mhz = frequency_ranges(flight)[0].minimum.mhz
    set_package_frequency(package, mhz, GameUpdateEvents())
    set_flight_frequency(flight, mhz, "AM", GameUpdateEvents())
    assert flight_radio_warnings(game, flight) == []
    assert package_radio_warnings(game, package) == []

    other = _flight(game)
    set_flight_frequency(other, mhz, "AM", GameUpdateEvents())
    assert "double booked" in flight_radio_warnings(game, other)[0]
    assert "double booked" in package_radio_warnings(game, package)[0]


def test_guard_frequency_warns(game: Game) -> None:
    flight = _flight(game)
    package = flight.package
    set_package_frequency(package, 243.0, GameUpdateEvents())
    assert "guard" in package_radio_warnings(game, package)[0]


# --- TACAN ---------------------------------------------------------------------


def test_tacan_is_for_tankers_only(game: Game) -> None:
    flight = _flight(game)
    assert not has_flight_tacan(flight)
    with pytest.raises(CommandError, match="tanker"):
        set_flight_tacan(flight, 74, "X", None, GameUpdateEvents())


def test_tanker_tacan_limits_and_warning(game: Game) -> None:
    tanker = _tanker(game)
    assert has_flight_tacan(tanker)
    set_flight_tacan(tanker, 74, "Y", "tkr", GameUpdateEvents())
    assert tanker.tacan == TacanChannel(74, TacanBand.Y)
    assert tanker.tcn_name == "TKR"
    assert flight_tacan_warnings(game, tanker) == []

    # A flight holding the same channel: the reference game has a single tanker.
    other = _flight(game)
    other.tacan = TacanChannel(74, TacanBand.Y)
    assert "already in use" in flight_tacan_warnings(game, tanker)[0]
    other.tacan = None

    with pytest.raises(CommandError, match="TACAN channel"):
        set_flight_tacan(tanker, 127, "Y", None, GameUpdateEvents())
    with pytest.raises(CommandError, match="band"):
        set_flight_tacan(tanker, 74, "Z", None, GameUpdateEvents())
    with pytest.raises(CommandError, match="callsign"):
        set_flight_tacan(tanker, 74, "Y", "TOOLONG", GameUpdateEvents())

    set_flight_tacan(tanker, None, None, "TKR", GameUpdateEvents())
    assert (tanker.tacan, tanker.tcn_name) == (None, None)


# --- datalink ------------------------------------------------------------------


def test_link16_rules_of_the_property_editor(game: Game) -> None:
    flight = _flight(game)
    fields = {f.identifier: f for f in datalink_fields(flight)}
    assert DataLinkKey.LINK16.value in fields
    member = next(iter(flight.iter_members()))
    stn = DataLinkKey.LINK16.value

    set_datalink_value(flight, 0, stn, "17", GameUpdateEvents())
    assert member.properties[stn] == "00017"
    with pytest.raises(CommandError, match="octal"):
        set_datalink_value(flight, 0, stn, "00089", GameUpdateEvents())
    with pytest.raises(CommandError, match="at most"):
        set_datalink_value(flight, 0, stn, "000017", GameUpdateEvents())
    assert member.properties[stn] == "00017"

    set_datalink_value(flight, 0, "VoiceCallsignLabel", "vp", GameUpdateEvents())
    assert member.properties["VoiceCallsignLabel"] == "VP"
    with pytest.raises(CommandError, match="not a valid"):
        set_datalink_value(flight, 0, "VoiceCallsignLabel", "V1", GameUpdateEvents())
    with pytest.raises(CommandError, match="not a valid"):
        set_datalink_value(flight, 0, "VoiceCallsignNumber", "AB", GameUpdateEvents())

    set_datalink_value(flight, 0, stn, "", GameUpdateEvents())
    assert stn not in member.properties


def test_datalink_refuses_unknown_member_and_field(game: Game) -> None:
    flight = _flight(game)
    with pytest.raises(CommandError, match="no longer exists"):
        set_datalink_value(flight, 9, "STN_L16", "1", GameUpdateEvents())
    with pytest.raises(CommandError, match="no such datalink"):
        set_datalink_value(flight, 0, "HelmetDevice", "1", GameUpdateEvents())


# --- routes --------------------------------------------------------------------


def test_read_route(game: Game) -> None:
    flight = _flight(game)
    status, body = _request("GET", _path(flight))
    assert status == 200
    assert body["frequency_mhz"] is None
    assert body["ranges"]
    assert body["has_tacan"] is False
    assert body["departure"] == flight.departure.name
    assert body["datalink"]["name"] == "Link 16"
    assert len(body["datalink"]["members"]) == 2


def test_command_routes_answer_the_tab(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    flight = _flight(game)
    mhz = frequency_ranges(flight)[0].minimum.mhz
    status, body = _request("PUT", _path(flight, "/frequency"), {"mhz": mhz})
    assert status == 200
    assert body["frequency_mhz"] == mhz
    assert any(flight in events.updated_flights for events in published)

    status, body = _request("PUT", _path(flight, "/frequency"), {"mhz": 5})
    assert status == 409
    assert "cannot tune" in body["detail"]

    status, body = _request("PUT", _path(flight, "/package-frequency"), {"mhz": 251})
    assert status == 200
    assert body["package_frequency_mhz"] == 251

    status, body = _request(
        "PUT",
        _path(flight, "/datalink/1"),
        {"identifier": "STN_L16", "value": "7"},
    )
    assert status == 200
    assert body["datalink"]["members"][1]["values"]["STN_L16"] == "00007"

    status, body = _request("PUT", _path(flight, "/tacan"), {"channel": 74})
    assert status == 409


def test_a_gone_flight_is_a_404(game: Game) -> None:
    flight = _flight(game)
    package: Package = flight.package
    other = _flight(game)
    status, _ = _request("GET", f"/packages/{package.id}/flights/{other.id}/radios")
    assert status == 404


# --- what the issue moved to the web ---------------------------------------------


def test_new_package_on_own_base_offers_transport(game: Game) -> None:
    base = next(
        cp
        for cp in game.theater.control_points_for(game.blue.player)
        if can_plan_transport_mission(cp)
    )
    package = create_package(game, base, _now(game))
    detail = PackageDetailJs.for_package(game, package)
    assert detail.transport_origin_id == base.id

    enemy = create_package(game, _sam(game), _now(game))
    assert PackageDetailJs.for_package(game, enemy).transport_origin_id is None


def test_transport_entry_leaves_with_the_first_flight(game: Game) -> None:
    base = next(
        cp
        for cp in game.theater.control_points_for(game.blue.player)
        if can_plan_transport_mission(cp)
    )
    package = create_package(game, base, _now(game))
    add_flight(game, package, FlightType.BARCAP, _squadron(game, F16), 1, _now(game))
    assert PackageDetailJs.for_package(game, package).transport_origin_id is None


# --- data cartridge (#191) ------------------------------------------------------


@pytest.fixture
def missions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The Missions folder of DCS, where Take off writes the mission."""
    monkeypatch.setattr(persistency, "mission_path_for", lambda name: tmp_path / name)
    return tmp_path


@pytest.fixture
def bridge(monkeypatch: pytest.MonkeyPatch) -> FakeBridge:
    fake = FakeBridge()
    monkeypatch.setattr(NativeContext, "_bridge", fake)
    return fake


def _generated_cartridge(missions: Path, flight: Flight) -> DtcCartridge:
    """What Take off leaves for a player Hornet flight."""
    miz = missions / MISSION_FILE_NAME
    with ZipFile(miz, "w"):
        pass
    cartridge = DtcCartridge("Retribution Enfield 1", "FA-18C_hornet", {"COMM": {}})
    dtc.write([dtc.FlightCartridge(flight.id, cartridge, ())], miz, Mission())
    return cartridge


def test_a_flight_without_cartridge_has_none_to_save(
    game: Game, missions: Path, bridge: FakeBridge
) -> None:
    flight = _flight(game)

    status, body = _request("GET", _path(flight))
    assert body["cartridge_file"] is None

    status, body = _request("POST", _path(flight, "/cartridge/save"))
    assert status == 409
    assert body["detail"] == (
        "No data cartridge for this flight: it comes with the mission (Take off), "
        "for a player flight of an aircraft that takes one."
    )
    assert bridge.asked == []


def test_the_cartridge_of_the_last_mission_is_saved_where_the_player_wants(
    game: Game, missions: Path, bridge: FakeBridge, tmp_path: Path
) -> None:
    flight = _flight(game)
    cartridge = _generated_cartridge(missions, flight)
    target = tmp_path / "chosen" / "mine.dtc"
    target.parent.mkdir()
    bridge.answer = str(target)

    status, body = _request("GET", _path(flight))
    assert body["cartridge_file"] == "Retribution Enfield 1.dtc"

    status, body = _request("POST", _path(flight, "/cartridge/save"))
    assert (status, body) == (200, {"outcome": "saved", "path": str(target)})
    assert target.read_text(encoding="utf-8") == cartridge.to_json()
    [(kind, start)] = bridge.asked
    assert kind == "save-file"
    assert start == str(persistency.base_path() / "DTC" / "Retribution Enfield 1.dtc")


def test_saving_the_cartridge_can_be_cancelled(
    game: Game, missions: Path, bridge: FakeBridge
) -> None:
    flight = _flight(game)
    _generated_cartridge(missions, flight)

    status, body = _request("POST", _path(flight, "/cartridge/save"))
    assert (status, body) == (200, {"outcome": "cancelled", "path": None})


# --- cartridge settings (#221) ---------------------------------------------------


@pytest.fixture
def fresh_cartridges(game: Game, monkeypatch: pytest.MonkeyPatch) -> None:
    """The module-scoped game keeps what a test sets on its squadrons: undo it."""
    for squadron in game.blue.air_wing.iter_squadrons():
        monkeypatch.setattr(squadron, "dtc", DtcSettings())


def test_an_aircraft_without_cartridge_has_no_settings(
    game: Game, fresh_cartridges: None
) -> None:
    tanker = _tanker(game)
    status, body = _request("GET", _path(tanker))
    assert body["cartridge_settings"] is None

    status, body = _request(
        "PUT", _path(tanker, "/cartridge/settings"), {"auto_load": False}
    )
    assert status == 409
    assert body["detail"] == "This aircraft takes no data cartridge."


def test_the_tab_shows_the_cmds_of_the_module_until_changed(
    game: Game, fresh_cartridges: None
) -> None:
    flight = _flight(game)
    status, body = _request("GET", _path(flight))
    settings = body["cartridge_settings"]
    assert settings["auto_load"] is True
    assert settings["threats"] is True
    assert settings["cmds_modified"] is False
    assert [p["id"] for p in settings["cmds_programs"]][:2] == ["MAN1", "MAN2"]
    assert settings["cmds_programs"][0]["values"]["chaff_salvo_quantity"] == 10
    assert {f["id"] for f in settings["cmds_fields"]} >= {"flare_burst_interval"}


def test_cartridge_settings_are_kept_on_the_squadron(
    game: Game, fresh_cartridges: None
) -> None:
    flight = _flight(game)
    programs = {"MAN1": {"chaff_salvo_quantity": 4, "chaff_burst_quantity": 1}}
    status, body = _request(
        "PUT",
        _path(flight, "/cartridge/settings"),
        {"auto_load": False, "threats": False, "cmds": programs},
    )
    assert status == 200
    settings = body["cartridge_settings"]
    assert (settings["auto_load"], settings["threats"]) == (False, False)
    assert settings["cmds_modified"] is True
    assert flight.squadron.dtc == DtcSettings(
        auto_load=False, threats=False, cmds={"MAN1": {"chaff_salvo_quantity": 4}}
    )

    # Another flight of the squadron, next turn too: the squadron keeps them.
    other = _flight(game)
    assert other.squadron is flight.squadron
    status, body = _request("GET", _path(other))
    assert body["cartridge_settings"]["auto_load"] is False

    status, body = _request("DELETE", _path(flight, "/cartridge/settings"))
    assert status == 200
    assert flight.squadron.dtc == DtcSettings()


def test_a_cmds_value_out_of_limits_is_refused(
    game: Game, fresh_cartridges: None
) -> None:
    flight = _flight(game)
    status, body = _request(
        "PUT",
        _path(flight, "/cartridge/settings"),
        {"auto_load": False, "cmds": {"MAN1": {"chaff_salvo_quantity": 120}}},
    )
    assert status == 409
    assert body["detail"] == "MAN 1: Chaff SQ must be from 0 to 99."
    # Nothing changed, not even what was valid.
    assert flight.squadron.dtc == DtcSettings()


def test_settings_apply_to_every_squadron_of_the_aircraft(
    game: Game, fresh_cartridges: None
) -> None:
    flight = _flight(game)
    flight.squadron.dtc.auto_load = False
    unit_type = flight.squadron.aircraft.dcs_unit_type.id
    others = [
        s
        for s in game.blue.air_wing.iter_squadrons()
        if s is not flight.squadron and s.aircraft.dcs_unit_type.id == unit_type
    ]

    status, body = _request(
        "POST", _path(flight, "/cartridge/settings/apply-to-aircraft")
    )

    assert status == 200
    assert body["cartridge_settings"]["same_aircraft_squadrons"] == len(others)
    for squadron in others:
        assert squadron.dtc == flight.squadron.dtc
        assert squadron.dtc is not flight.squadron.dtc

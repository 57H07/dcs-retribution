"""WEB-04.3: the commands of the Payload tab, on a real generated game.

W16 checks that the editor leaves plans alone (`tests/flightplans`). Here: the rules and
the routes.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from dcs.planes import F_14B
from dcs.unittype import FlyingType

from game import Game
from game.ato import Flight, FlightType, Package
from game.commands import CommandError, flightpayload
from game.commands.flightpayload import (
    CLEAN_CLSID,
    DATALINK_PROPERTY_IDS,
    PropertyValue,
    effective_loadout,
    named_loadouts,
    property_controls,
    pylon_options,
    reset_weapon_settings,
    save_member_payload,
    set_flight_fuel,
    set_member_custom,
    set_member_livery,
    set_member_loadout,
    set_member_property,
    set_member_pylon,
    set_same_livery,
    set_same_loadout,
    set_tgp_laser_code,
    set_weapon_laser_code,
    set_weapon_setting,
)
from game.commands.packageflights import add_flight, default_loadout
from game.commands.packages import create_package
from game.data.weapons import Pylon, Weapon
from game.radio.datalink import DataLinkKey
from game.server import GameContext
from game.server.eventstream import EventStream
from game.server.flightpayload.models import FlightPayloadJs
from game.sim import GameUpdateEvents
from game.squadrons import Squadron
from game.theater.theatergroundobject import SamGroundObject
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)
from tests.server.test_packages_routes import _request

F16 = "F-16CM Fighting Falcon (Block 50)"
F15E = "F-15E Strike Eagle"


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
    monkeypatch.setattr(reference_game.settings, "restrict_weapons_by_date", False)
    monkeypatch.setattr(reference_game.settings, "restrict_props_by_date", False)
    yield reference_game
    for package in list(reference_game.blue.ato.packages):
        for flight in list(package.flights):
            flight.return_pilots_and_aircraft()
    reference_game.blue.ato.clear()


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[GameUpdateEvents]:
    events: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", events.append)
    return events


def _squadron(game: Game, aircraft: str) -> Squadron:
    return next(
        s
        for s in game.blue.air_wing.iter_squadrons()
        if s.aircraft.display_name == aircraft
    )


def _package(game: Game) -> Package:
    sam = next(
        tgo
        for tgo in game.theater.ground_objects
        if isinstance(tgo, SamGroundObject) and not tgo.is_friendly(game.blue.player)
    )
    return create_package(game, sam, game.conditions.start_time)


def _sead(game: Game, size: int = 2) -> Flight:
    return add_flight(
        game,
        _package(game),
        FlightType.SEAD,
        _squadron(game, F16),
        size,
        game.conditions.start_time,
    )


def _url(flight: Flight, path: str = "") -> str:
    return f"/packages/{flight.package.id}/flights/{flight.id}/payload{path}"


def _set_player(flight: Flight, index: int = 0) -> None:
    pilot = flight.roster.members[index].pilot
    assert pilot is not None
    pilot.player = True


def _unused_weapon(game: Game, flight: Flight) -> tuple[int, Weapon]:
    """A pylon and a weapon it accepts that the loadout does not carry there."""
    loadout = flight.roster.members[0].loadout
    for number, weapons in pylon_options(game, flight).items():
        for weapon in weapons:
            if loadout.pylons.get(number) != weapon:
                return number, weapon
    raise AssertionError("No free weapon on this aircraft")


# --- what the tab shows --------------------------------------------------------------


def test_read_model_lists_pylons_and_what_each_accepts(game: Game) -> None:
    flight = _sead(game)

    payload = FlightPayloadJs.for_flight(game, flight)

    assert payload.aircraft == str(flight.unit_type)
    assert payload.fuel_max == int(flight.unit_type.dcs_unit_type.fuel_max)
    assert payload.same_loadout is True
    numbers = [pylon.number for pylon in payload.pylons]
    assert numbers == sorted(flight.unit_type.dcs_unit_type.pylons)
    for options in payload.pylons:
        allowed = Pylon.for_aircraft(flight.unit_type, options.number).allowed
        offered = {w.clsid for w in options.weapons}
        assert offered - {CLEAN_CLSID} <= {w.clsid for w in allowed}
        keys = [(w.name, w.clsid) for w in options.weapons]
        assert keys == sorted(keys)
    member = payload.members[0]
    assert member.custom is False
    assert member.loadout == flight.roster.members[0].loadout.name
    assert member.loadout in payload.loadouts
    assert [p.number for p in member.pylons] == numbers
    stored = flight.roster.members[0].loadout.pylons
    for pylon in member.pylons:
        weapon = stored.get(pylon.number)
        assert (pylon.weapon.clsid if pylon.weapon else None) == (
            weapon.clsid if weapon else None
        )


def test_clean_is_offered_only_where_a_loadout_uses_it(game: Game) -> None:
    flight = _sead(game)
    member = flight.roster.members[0]
    clean = Weapon.with_clsid(CLEAN_CLSID)
    number = next(iter(pylon_options(game, flight)))
    known = [
        loadout.pylons.get(number)
        for loadout in named_loadouts(flight.unit_type).values()
    ]
    assert clean is not None
    assert (clean in pylon_options(game, flight)[number]) == (clean in known)

    set_member_custom(game, flight, member, True)
    member.loadout.pylons[number] = clean

    # The member's own loadout counts too: what a pylon carries stays selectable.
    assert clean in pylon_options(game, flight)[number]
    set_member_pylon(game, flight, member, number, CLEAN_CLSID)
    assert member.loadout.pylons[number] == clean


# --- named and custom loadouts -------------------------------------------------------


def test_named_loadout_goes_to_all_members_when_shared(game: Game) -> None:
    flight = _sead(game)
    first, second = flight.roster.members
    other = next(n for n in named_loadouts(flight.unit_type) if n != first.loadout.name)

    set_member_loadout(flight, first, other)

    assert first.loadout.name == other
    assert second.loadout is first.loadout
    with pytest.raises(CommandError, match="share one loadout"):
        set_member_loadout(flight, second, other)
    with pytest.raises(CommandError, match="no loadout named"):
        set_member_loadout(flight, first, "Nope")


def test_custom_starts_from_the_same_weapons_and_can_go_back(game: Game) -> None:
    flight = _sead(game)
    first, second = flight.roster.members
    pylons = dict(first.loadout.pylons)
    default = default_loadout(flight.unit_type, flight.flight_type).name

    set_member_custom(game, flight, first, True)

    assert first.loadout.is_custom and first.use_custom_loadout
    assert first.loadout.name == "Custom"
    assert first.loadout.pylons == pylons
    assert second.loadout is first.loadout and second.use_custom_loadout
    with pytest.raises(CommandError, match="Turn off"):
        set_member_loadout(flight, first, default)

    set_member_custom(game, flight, first, False)

    back = first.loadout
    assert (back.is_custom, first.use_custom_loadout) == (False, False)
    assert back.name == default
    assert first.loadout.pylons == pylons
    assert second.loadout is first.loadout


def test_custom_twice_keeps_the_edits(game: Game) -> None:
    flight = _sead(game)
    member = flight.roster.members[0]
    number, weapon = _unused_weapon(game, flight)
    set_member_custom(game, flight, member, True)
    set_member_pylon(game, flight, member, number, weapon.clsid)

    set_member_custom(game, flight, member, True)

    assert member.loadout.pylons[number] == weapon


def test_pylon_edits_need_a_custom_loadout_and_an_accepted_weapon(game: Game) -> None:
    flight = _sead(game)
    member = flight.roster.members[0]
    number, weapon = _unused_weapon(game, flight)
    with pytest.raises(CommandError, match="Turn on"):
        set_member_pylon(game, flight, member, number, weapon.clsid)

    set_member_custom(game, flight, member, True)
    named = named_loadouts(flight.unit_type)[
        default_loadout(flight.unit_type, flight.flight_type).name
    ]
    with pytest.raises(CommandError, match="no pylon"):
        set_member_pylon(game, flight, member, 999, weapon.clsid)
    refused = next(
        w
        for w in Weapon._by_clsid.values()
        if w not in pylon_options(game, flight)[number]
    )
    with pytest.raises(CommandError, match="cannot carry"):
        set_member_pylon(game, flight, member, number, refused.clsid)

    set_member_pylon(game, flight, member, number, weapon.clsid)
    assert member.loadout.pylons[number] == weapon
    # The named loadout of the aircraft does not move.
    assert named_loadouts(flight.unit_type)[named.name].pylons == named.pylons

    set_member_pylon(game, flight, member, number, None)
    assert member.loadout.pylons[number] is None


def test_edit_reaches_members_added_by_a_resize(game: Game) -> None:
    flight = _sead(game)
    flight.roster.resize(3)
    first, _, third = flight.roster.members
    assert third.loadout is not first.loadout
    number, weapon = _unused_weapon(game, flight)

    set_member_custom(game, flight, first, True)
    set_member_pylon(game, flight, first, number, weapon.clsid)

    assert third.loadout is first.loadout
    assert third.use_custom_loadout


def test_members_can_have_their_own_loadouts(game: Game) -> None:
    flight = _sead(game)
    first, second = flight.roster.members
    number, weapon = _unused_weapon(game, flight)

    set_same_loadout(flight, False)

    assert second.loadout is not first.loadout
    set_member_custom(game, flight, second, True)
    set_member_pylon(game, flight, second, number, weapon.clsid)
    assert second.loadout.pylons[number] == weapon
    assert first.loadout.pylons.get(number) != weapon
    assert not first.loadout.is_custom

    set_same_loadout(flight, True)

    assert second.loadout is first.loadout
    assert not second.use_custom_loadout


# --- the date restriction ------------------------------------------------------------


@pytest.fixture
def before_any_missile(game: Game, monkeypatch: pytest.MonkeyPatch) -> Game:
    monkeypatch.setattr(game.settings, "restrict_weapons_by_date", True)
    monkeypatch.setattr(game, "date", datetime.date(1950, 1, 1))
    return game


def test_date_restriction_filters_what_is_offered(
    game: Game, before_any_missile: Game
) -> None:
    flight = _sead(game)
    faction = flight.squadron.coalition.faction
    restricted = pylon_options(game, flight)

    for number, weapons in restricted.items():
        allowed = Pylon.for_aircraft(flight.unit_type, number).allowed
        assert len(weapons) <= len(allowed) + 1
        for weapon in weapons:
            assert weapon.available_on(game.date, faction)

    member = flight.roster.members[0]
    set_member_custom(game, flight, member, True)
    number, weapon = next(
        (n, w)
        for n in restricted
        for w in Pylon.for_aircraft(flight.unit_type, n).allowed
        if not w.available_on(game.date, faction)
    )
    with pytest.raises(CommandError, match="cannot carry"):
        set_member_pylon(game, flight, member, number, weapon.clsid)


def test_reading_shows_what_flies_and_leaves_the_stored_loadout_alone(
    game: Game, before_any_missile: Game
) -> None:
    flight = _sead(game)
    member = flight.roster.members[0]
    stored = dict(member.loadout.pylons)
    shown = effective_loadout(game, flight, member)
    assert shown.pylons != stored

    payload = FlightPayloadJs.for_flight(game, flight)

    assert member.loadout.pylons == stored
    assert member.loadout.date is None
    replaced = [p for p in payload.members[0].pylons if p.replaced_weapon is not None]
    assert replaced
    for pylon in replaced:
        weapon = shown.pylons.get(pylon.number)
        assert (pylon.weapon.clsid if pylon.weapon else None) == (
            weapon.clsid if weapon else None
        )


def test_custom_starts_from_what_the_restriction_leaves(
    game: Game, before_any_missile: Game
) -> None:
    flight = _sead(game)
    member = flight.roster.members[0]
    shown = effective_loadout(game, flight, member)

    set_member_custom(game, flight, member, True)

    assert member.loadout.pylons == shown.pylons
    # Undated, as a custom loadout always was: generation keeps degrading and applying
    # the target overrides on it.
    assert member.loadout.date is None


def test_nothing_is_filtered_when_the_restriction_is_off(game: Game) -> None:
    flight = _sead(game)
    original = game.date
    game.date = datetime.date(1950, 1, 1)
    try:
        options = pylon_options(game, flight)
        for number, weapons in options.items():
            allowed = Pylon.for_aircraft(flight.unit_type, number).allowed
            assert set(weapons) >= allowed
        assert (
            effective_loadout(game, flight, flight.roster.members[0]).pylons
            == flight.roster.members[0].loadout.pylons
        )
    finally:
        game.date = original


# --- weapon settings -----------------------------------------------------------------


def _weapon_with_settings(game: Game, flight: Flight) -> tuple[int, Weapon]:
    for number, weapons in pylon_options(game, flight).items():
        for weapon in weapons:
            if weapon.has_settings() and flightpayload.visible_weapon_settings(
                weapon, None
            ):
                return number, weapon
    raise AssertionError("No configurable weapon on this aircraft")


def test_weapon_settings_are_set_one_by_one_and_reset(game: Game) -> None:
    flight = add_flight(
        game,
        _package(game),
        FlightType.SEAD,
        _squadron(game, F16),
        2,
        game.conditions.start_time,
    )
    member = flight.roster.members[0]
    set_member_custom(game, flight, member, True)
    number, weapon = _weapon_with_settings(game, flight)
    set_member_pylon(game, flight, member, number, weapon.clsid)
    setting = next(
        s
        for s in flightpayload.visible_weapon_settings(weapon, None)
        if s.control == "comboList" and len(s.values) > 1 and not s.read_only
    )
    value = next(v["id"] for v in setting.values if v["id"] != setting.current_value)

    set_weapon_setting(flight, member, number, setting.id, value)

    assert member.loadout.pylon_settings[number][setting.id] == value
    shown = FlightPayloadJs.for_flight(game, flight).members[0]
    pylon = next(p for p in shown.pylons if p.number == number)
    assert next(s for s in pylon.settings if s.id == setting.id).value == value

    with pytest.raises(CommandError, match="invalid value"):
        set_weapon_setting(flight, member, number, setting.id, "not a choice")
    with pytest.raises(CommandError, match="cannot be changed"):
        set_weapon_setting(flight, member, number, "nope", 1)

    reset_weapon_settings(flight, member, number)
    assert member.loadout.pylon_settings[number][setting.id] == setting.def_value

    # A settings dict belongs to its weapon.
    set_member_pylon(game, flight, member, number, None)
    assert number not in member.loadout.pylon_settings
    with pytest.raises(CommandError, match="no settings"):
        reset_weapon_settings(flight, member, number)


# --- fuel, livery, laser codes, options ----------------------------------------------


def test_fuel_stays_within_the_tanks(game: Game) -> None:
    flight = _sead(game)
    top = int(flight.unit_type.dcs_unit_type.fuel_max)

    set_flight_fuel(flight, 1000)
    assert flight.fuel == 1000
    for wrong in (-1, top + 1):
        with pytest.raises(CommandError, match="Internal fuel"):
            set_flight_fuel(flight, wrong)
    assert flight.fuel == 1000


def test_laser_codes_are_for_players(game: Game) -> None:
    flight = _sead(game)
    member = flight.roster.members[0]
    with pytest.raises(CommandError, match="AI"):
        set_tgp_laser_code(game, member, True)
    with pytest.raises(CommandError, match="AI"):
        set_weapon_laser_code(game, member, None)
    assert FlightPayloadJs.for_flight(game, flight).members[0].weapon_laser_codes == []

    _set_player(flight)
    try:
        set_tgp_laser_code(game, member, True)
        code = member.tgp_laser_code
        assert code is not None
        shown = FlightPayloadJs.for_flight(game, flight).members[0]
        assert shown.tgp_laser_code == code.code
        assert code.code in [c.code for c in shown.weapon_laser_codes]

        set_weapon_laser_code(game, member, code.code)
        assert member.weapon_laser_code == code
        with pytest.raises(CommandError, match="not available"):
            set_weapon_laser_code(game, member, 1111)

        set_tgp_laser_code(game, member, False)
        assert member.tgp_laser_code is None
        assert member.weapon_laser_code is None
    finally:
        pilot = member.pilot
        assert pilot is not None
        pilot.player = False


def test_livery_follows_the_shared_setting(game: Game) -> None:
    flight = _sead(game)
    first, second = flight.roster.members
    choices = [
        c
        for c in FlightPayloadJs.for_flight(game, flight).members[0].liveries
        if c.livery_id is not None
    ]
    assert len(choices) > 1
    one, two = choices[0], choices[1]

    set_member_livery(flight, first, one.livery_id, False)
    assert second.livery == one.livery_id
    assert not second.use_livery_set
    with pytest.raises(CommandError, match="share one livery"):
        set_member_livery(flight, second, two.livery_id, False)
    with pytest.raises(CommandError, match="cannot use"):
        set_member_livery(flight, first, "no such livery", False)

    set_same_livery(flight, False)
    set_member_livery(flight, second, two.livery_id, False)
    assert (first.livery, second.livery) == (one.livery_id, two.livery_id)
    shown = FlightPayloadJs.for_flight(game, flight).members
    assert [c.livery_id for c in shown[1].liveries if c.selected] == [two.livery_id]

    set_same_livery(flight, True)
    assert second.livery == one.livery_id


def _f14_flight() -> Any:
    """What the option rules read of a player flight of F-14s."""
    return SimpleNamespace(
        unit_type=SimpleNamespace(
            iter_props=lambda: F_14B.properties.values(),
            should_show_prop=lambda _: True,
        ),
        client_count=1,
    )


def test_options_are_checked_by_control(game: Game) -> None:
    flight = _f14_flight()
    member = _sead(game).roster.members[0]
    controls = {c.prop.identifier: c.prop for c in property_controls(flight)}
    assert controls["INSAlignmentStored"].control == "checkbox"
    assert controls["M61BURST"].control == "comboList"
    assert controls["TacanChannel"].control == "spinbox"

    invalid: list[tuple[str, PropertyValue]] = [
        ("INSAlignmentStored", "x"),
        ("M61BURST", "no such value"),
        ("TacanChannel", -(10**9)),
        ("TacanChannel", True),
    ]
    for identifier, value in invalid:
        with pytest.raises(CommandError, match="invalid value"):
            set_member_property(game, flight, member, identifier, value)
    assert member.properties == {}

    set_member_property(game, flight, member, "INSAlignmentStored", True)
    assert member.properties["INSAlignmentStored"] is True
    burst = controls["M61BURST"].values
    assert burst is not None
    last = list(burst)[-1]
    set_member_property(game, flight, member, "M61BURST", last)
    assert member.properties["M61BURST"] == last
    minimum = controls["TacanChannel"].minimum
    set_member_property(game, flight, member, "TacanChannel", minimum)
    assert member.properties["TacanChannel"] == minimum
    with pytest.raises(CommandError, match="does not have"):
        set_member_property(game, flight, member, "nope", 1)


def test_a_player_flight_shows_its_other_options(game: Game) -> None:
    flight = _sead(game)
    assert all(not c.prop.player_only for c in property_controls(flight))
    _set_player(flight)
    pilot = flight.roster.members[0].pilot
    assert pilot is not None
    try:
        assert property_controls(flight)
    finally:
        pilot.player = False


def test_datalink_options_are_left_to_the_radios_tab(game: Game) -> None:
    flight = _sead(game)
    member = flight.roster.members[0]
    properties = flight.unit_type.dcs_unit_type.properties
    assert DataLinkKey.LINK16.value in properties

    shown = {c.prop.identifier for c in property_controls(flight)}

    assert not shown & DATALINK_PROPERTY_IDS
    with pytest.raises(CommandError, match="does not have"):
        set_member_property(game, flight, member, DataLinkKey.LINK16.value, "00017")
    payload = FlightPayloadJs.for_flight(game, flight)
    assert not {p.id for p in payload.properties} & DATALINK_PROPERTY_IDS
    assert not set(payload.members[0].properties) & DATALINK_PROPERTY_IDS


def test_f14_options_come_through() -> None:
    controls = property_controls(_f14_flight())

    assert {c.prop.identifier for c in controls} >= {
        "M61BURST",
        "ALE39Loadout",
        "INSAlignmentStored",
        "TacanChannel",
        "KY28Key",
    }


# --- payload files -------------------------------------------------------------------


def test_saved_payload_joins_the_named_loadouts(
    game: Game, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_dir(backup: bool = False) -> Path:
        path = tmp_path / "backups" if backup else tmp_path
        path.mkdir(exist_ok=True)
        return path

    monkeypatch.setattr(flightpayload, "payloads_dir", fake_dir)
    flight = _sead(game)
    member = flight.roster.members[0]
    aircraft = flight.unit_type.dcs_unit_type
    with pytest.raises(CommandError, match="Turn on"):
        save_member_payload(flight, member, "Mine")

    set_member_custom(game, flight, member, True)
    number, _ = _unused_weapon(game, flight)
    set_member_pylon(game, flight, member, number, None)
    with pytest.raises(CommandError, match="name"):
        save_member_payload(flight, member, "  ")

    saved = False
    cache_before = dict(FlyingType._payload_cache)
    try:
        path = save_member_payload(flight, member, "Mine")
        saved = True
        assert path == tmp_path / f"{aircraft.id}.lua"
        assert "Mine" in path.read_text(encoding="utf-8")
        loadouts = named_loadouts(flight.unit_type)
        assert "Mine" in loadouts
        expected = {n: w for n, w in member.loadout.pylons.items() if w is not None}
        clean = Weapon.with_clsid(CLEAN_CLSID)
        assert clean is not None
        expected[number] = clean
        assert loadouts["Mine"].pylons == expected
        # A second save goes through the existing file, after a backup.
        path = save_member_payload(flight, member, "Mine 2")
        assert (tmp_path / "backups" / f"{aircraft.id}.lua").exists()
        text = path.read_text(encoding="utf-8")
        assert "Mine" in text and "Mine 2" in text
        assert flightpayload.backup_payload_file(flight) is not None
    finally:
        if saved:
            assert aircraft.payloads is not None
            aircraft.payloads.pop("Mine", None)
            aircraft.payloads.pop("Mine 2", None)
        FlyingType._payload_cache = cache_before


# --- routes --------------------------------------------------------------------------


def test_routes_answer_the_read_model_and_publish_the_flight(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    flight = _sead(game)
    member = flight.roster.members[0]

    status, body = _request("GET", _url(flight))
    assert status == 200
    assert body["members"][0]["custom"] is False
    assert body["date"] == game.date.isoformat()

    status, body = _request("PUT", _url(flight, "/members/0/custom"), {"custom": True})
    assert status == 200
    assert body["members"][0]["custom"] is True
    assert body["members"][0]["loadout"] == "Custom"
    assert published[-1].updated_flights == {flight}

    number, weapon = _unused_weapon(game, flight)
    status, body = _request(
        "PUT", _url(flight, f"/members/0/pylons/{number}"), {"clsid": weapon.clsid}
    )
    assert status == 200
    assert member.loadout.pylons[number] == weapon
    pylon = next(p for p in body["members"][0]["pylons"] if p["number"] == number)
    assert pylon["weapon"]["clsid"] == weapon.clsid

    status, body = _request("PUT", _url(flight, "/fuel"), {"fuel": 1234})
    assert (status, body["fuel"]) == (200, 1234)
    status, body = _request("PUT", _url(flight, "/same-loadout"), {"same": False})
    assert (status, body["same_loadout"]) == (200, False)
    status, body = _request("PUT", _url(flight, "/same-livery"), {"same": False})
    assert (status, body["same_livery"]) == (200, False)


def test_routes_refuse_with_a_readable_message(game: Game) -> None:
    flight = _sead(game)

    status, body = _request(
        "PUT", _url(flight, "/members/1/loadout"), {"name": "whatever"}
    )
    assert status == 409
    assert "share one loadout" in body["detail"]

    status, body = _request("PUT", _url(flight, "/members/7/custom"), {"custom": True})
    assert status == 404
    assert body["detail"] == "This flight member no longer exists."

    other = f"/packages/{flight.package.id}/flights/{flight.package.id}/payload"
    status, body = _request("GET", other)
    assert status == 404
    assert body["detail"] == "This flight is no longer planned."

    status, _ = _request("PUT", _url(flight, "/fuel"), {"fuel": "lots"})
    assert status == 422


def test_loadout_change_does_not_touch_the_flight_plan(game: Game) -> None:
    flight = _sead(game)
    member = flight.roster.members[0]
    waypoints = [(w.name, w.x, w.y, w.alt) for w in flight.flight_plan.waypoints]
    tot = flight.package.time_over_target

    set_member_custom(game, flight, member, True)
    number, weapon = _unused_weapon(game, flight)
    set_member_pylon(game, flight, member, number, weapon.clsid)

    assert [
        (w.name, w.x, w.y, w.alt) for w in flight.flight_plan.waypoints
    ] == waypoints
    assert flight.package.time_over_target == tot

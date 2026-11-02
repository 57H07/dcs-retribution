"""WEB-04.2: the General and Pilots tabs of a flight, on a real generated game.

W16 checks what the engine plans (`tests/flightplans`). Here: the rules and the routes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator, cast
from uuid import uuid4

import pytest

from game import Game
from game.ato import Flight, FlightType, Package
from game.ato.flightplans.planningerror import PlanningError
from game.ato.starttype import StartType
from game.commands import CommandError
from game.commands.flightsettings import (
    change_flight_squadron,
    default_start_type,
    divert_options,
    flight_squadron_candidates,
    max_flight_resize,
    reconcile_player_laser_codes,
    resize_flight,
    set_callsign,
    set_flight_custom_name,
    set_flight_divert,
    set_flight_pilot,
    set_flight_slot_player,
    set_flight_start_type,
    set_flight_tot_offset,
)
from game.commands.packageflights import add_flight
from game.commands.packages import create_package
from game.server import GameContext
from game.server.eventstream import EventStream
from game.settings.settings import DefaultPlayerLaserCode
from game.sim import GameUpdateEvents
from game.squadrons import Pilot, Squadron
from game.theater import TheaterGroundObject
from game.theater.theatergroundobject import SamGroundObject
from tests.flightplans.fingerprint import fingerprint_package
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)
from tests.server.test_packages_routes import _request

F16 = "F-16CM Fighting Falcon (Block 50)"


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
    for package in list(reference_game.blue.ato.packages):
        for flight in list(package.flights):
            for pilot in flight.roster.iter_pilots():
                if pilot is not None:
                    pilot.player = False
    reference_game.blue.ato.clear()


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


def _squadron(game: Game) -> Squadron:
    return next(
        s for s in game.blue.air_wing.iter_squadrons() if s.aircraft.display_name == F16
    )


def _sead(game: Game, size: int = 2) -> tuple[Package, Flight]:
    package = create_package(game, _sam(game), _now(game))
    flight = add_flight(
        game, package, FlightType.SEAD, _squadron(game), size, _now(game)
    )
    return package, flight


def _dead(game: Game) -> tuple[Package, Flight]:
    """F-15E squadrons can take it over: a SEAD flight has no other squadron."""
    package = create_package(game, _sam(game), _now(game))
    return package, add_flight(
        game, package, FlightType.DEAD, _squadron(game), 2, _now(game)
    )


def _url(package: Package, flight: Flight, tail: str) -> str:
    return f"/packages/{package.id}/flights/{flight.id}/{tail}"


def _under_way(flight: Flight, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(flight, "state", SimpleNamespace(cancelable=False))


# --- Size ------------------------------------------------------------------------


def test_resizing_claims_and_returns_aircraft_and_pilots(game: Game) -> None:
    _, flight = _sead(game)
    squadron = flight.squadron
    aircraft = squadron.untasked_aircraft
    pilots = len(squadron.available_pilots)

    resize_flight(flight, 3, _now(game))
    assert flight.count == 3
    assert squadron.untasked_aircraft == aircraft - 1
    assert len(squadron.available_pilots) == pilots - 1

    resize_flight(flight, 1, _now(game))
    assert flight.count == 1
    assert squadron.untasked_aircraft == aircraft + 1
    assert len(squadron.available_pilots) == pilots + 1


def test_a_flight_cannot_outgrow_its_squadron_or_be_empty(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, flight = _sead(game)
    monkeypatch.setattr(flight.squadron, "untasked_aircraft", 1)
    assert max_flight_resize(flight) == 3

    with pytest.raises(CommandError, match="at most 3"):
        resize_flight(flight, 4, _now(game))
    with pytest.raises(CommandError, match="at least one"):
        resize_flight(flight, 0, _now(game))
    assert flight.count == 2


def test_size_route_answers_the_package(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    package, flight = _sead(game)

    status, body = _request("PUT", _url(package, flight, "size"), {"size": 1})

    assert status == 200
    assert body["flights"][0]["count"] == 1
    assert flight in published[-1].updated_flights


# --- Pilots -----------------------------------------------------------------------


def test_a_free_pilot_takes_a_slot_and_the_previous_one_is_free_again(
    game: Game,
) -> None:
    _, flight = _sead(game)
    squadron = flight.squadron
    previous = flight.roster.pilot_at(0)
    free = squadron.available_pilots[0]

    set_flight_pilot(flight, 0, free, _now(game))

    assert flight.roster.pilot_at(0) is free
    assert any(p is previous for p in squadron.available_pilots)
    assert not any(p is free for p in squadron.available_pilots)


def test_an_empty_slot_counts_as_missing_a_pilot(game: Game) -> None:
    _, flight = _sead(game)
    set_flight_pilot(flight, 1, None, _now(game))
    assert flight.missing_pilots == 1


def test_a_pilot_of_another_flight_is_refused(game: Game) -> None:
    _, flight = _sead(game)
    taken = flight.roster.pilot_at(1)
    with pytest.raises(CommandError, match="not available"):
        set_flight_pilot(flight, 0, taken, _now(game))


def test_a_slot_outside_the_flight_is_unknown(game: Game) -> None:
    package, flight = _sead(game)
    status, _ = _request("PUT", _url(package, flight, "pilots/2"), {"pilot_id": None})
    assert status == 404


def test_a_gone_pilot_is_refused_by_the_route(game: Game) -> None:
    package, flight = _sead(game)
    status, body = _request(
        "PUT", _url(package, flight, "pilots/0"), {"pilot_id": str(uuid4())}
    )
    assert status == 409
    assert body["detail"] == "This pilot is no longer available."


def test_a_player_gets_the_player_start_type_and_an_ai_flight_goes_back(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, flight = _sead(game)
    monkeypatch.setattr(game.settings, "default_start_type_client", StartType.RUNWAY)
    monkeypatch.setattr(game.settings, "default_start_type", StartType.COLD)
    flight.start_type = StartType.WARM
    events = GameUpdateEvents()

    set_flight_slot_player(flight, 0, True, events, _now(game))
    assert flight.client_count == 1
    assert flight.start_type is StartType.RUNWAY
    assert flight in events.updated_flights

    set_flight_slot_player(flight, 0, False, events, _now(game))
    assert flight.client_count == 0
    assert flight.start_type is StartType.COLD


def test_an_empty_slot_cannot_be_a_player(game: Game) -> None:
    _, flight = _sead(game)
    set_flight_pilot(flight, 0, None, _now(game))
    with pytest.raises(CommandError, match="Assign a pilot"):
        set_flight_slot_player(flight, 0, True, GameUpdateEvents(), _now(game))


def _laser_codes(flight: Flight) -> tuple[Any, Any]:
    lead = flight.roster.members[0]
    return lead.tgp_laser_code, lead.weapon_laser_code


def test_players_get_their_laser_code_and_ai_gives_it_back(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, flight = _sead(game)
    monkeypatch.setattr(
        game.settings, "default_player_laser_code", DefaultPlayerLaserCode.ALLOCATE_OWN
    )
    set_flight_slot_player(flight, 0, True, GameUpdateEvents(), _now(game))
    lead = flight.roster.members[0]
    own_code = lead.tgp_laser_code
    assert own_code is not None
    assert _laser_codes(flight) == (own_code, own_code)

    set_flight_slot_player(flight, 0, False, GameUpdateEvents(), _now(game))
    assert _laser_codes(flight) == (None, None)

    reconcile_player_laser_codes(flight)
    assert _laser_codes(flight) == (None, None)


def test_player_route_answers_the_clients_of_the_flight(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    package, flight = _sead(game)

    status, body = _request(
        "PUT", _url(package, flight, "pilots/0/player"), {"player": True}
    )

    assert status == 200
    assert body["flights"][0]["clients"] == 1
    assert any(flight in events.updated_flights for events in published)


# --- Squadron ---------------------------------------------------------------------


def test_candidates_can_fly_the_task_and_exclude_the_current_squadron(
    game: Game,
) -> None:
    _, flight = _dead(game)
    candidates = flight_squadron_candidates(flight)
    assert flight.squadron not in candidates
    assert all(s.can_auto_assign(FlightType.DEAD) for s in candidates)


def _other_squadron(game: Game, flight: Flight) -> Squadron:
    candidates = flight_squadron_candidates(flight)
    assert candidates, "The reference game has no other squadron for the flight."
    return candidates[0]


def test_changing_squadron_replaces_the_flight_in_place(game: Game) -> None:
    package, flight = _dead(game)
    escort = add_flight(game, package, FlightType.DEAD, _squadron(game), 1, _now(game))
    set_flight_custom_name(flight, "Viper")
    old_squadron = flight.squadron
    aircraft = old_squadron.untasked_aircraft
    other = _other_squadron(game, flight)
    other_aircraft = other.untasked_aircraft

    replacement = change_flight_squadron(flight, other, _now(game))

    assert package.flights == [replacement, escort]
    assert replacement.id != flight.id
    assert replacement.squadron is other
    assert replacement.count == 2
    assert replacement.flight_type is FlightType.DEAD
    assert replacement.custom_name == "Viper"
    assert replacement.divert != other.location
    assert replacement.flight_plan.waypoints
    assert old_squadron.untasked_aircraft == aircraft + 2
    assert other.untasked_aircraft == other_aircraft - 2


def test_a_squadron_that_cannot_take_the_flight_is_refused(game: Game) -> None:
    _, flight = _dead(game)
    with pytest.raises(CommandError, match="cannot take"):
        change_flight_squadron(flight, flight.squadron, _now(game))


def test_a_flight_that_cannot_be_planned_keeps_its_squadron(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    package, flight = _dead(game)
    other = _other_squadron(game, flight)
    other_aircraft = other.untasked_aircraft

    def refuse(_self: Flight, dump_debug_info: bool = False) -> None:
        raise PlanningError("no route")

    monkeypatch.setattr(Flight, "recreate_flight_plan", refuse)
    with pytest.raises(CommandError, match="no route"):
        change_flight_squadron(flight, other, _now(game))

    assert package.flights == [flight]
    assert other.untasked_aircraft == other_aircraft


def test_squadron_route_names_the_new_flight_and_publishes_the_swap(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    package, flight = _dead(game)
    other = _other_squadron(game, flight)

    status, body = _request(
        "PUT",
        _url(package, flight, "squadron"),
        {"squadron_id": str(other.id)},
    )

    assert status == 200
    replacement = package.flights[0]
    assert body["flight_id"] == str(replacement.id)
    assert body["package"]["flights"][0]["id"] == str(replacement.id)
    assert flight.id in published[-1].deleted_flights
    assert replacement in published[-1].new_flights


def test_squadron_route_refuses_an_unknown_squadron(game: Game) -> None:
    package, flight = _dead(game)
    status, _ = _request(
        "PUT", _url(package, flight, "squadron"), {"squadron_id": str(uuid4())}
    )
    assert status == 404


# --- Start type -------------------------------------------------------------------


def test_start_type_moves_the_startup_time_of_the_flight(game: Game) -> None:
    package, flight = _sead(game)
    flight.start_type = StartType.COLD
    package.auto_asap = False
    package.set_tot_asap(_now(game))
    cold = flight.flight_plan.startup_time()

    set_flight_start_type(flight, StartType.WARM, _now(game))

    assert flight.start_type is StartType.WARM
    assert flight.flight_plan.startup_time() > cold


def test_start_type_moves_the_tot_of_an_asap_package(game: Game) -> None:
    package, flight = _sead(game)
    set_flight_start_type(flight, StartType.COLD, _now(game))
    cold = package.time_over_target

    set_flight_start_type(flight, StartType.IN_FLIGHT, _now(game))

    assert package.time_over_target < cold


def test_a_base_that_dictates_the_start_type_wins(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, flight = _sead(game)
    monkeypatch.setattr(
        type(flight.departure),
        "required_aircraft_start_type",
        property(lambda _self: StartType.IN_FLIGHT),
    )

    with pytest.raises(CommandError, match="starts as In Flight"):
        set_flight_start_type(flight, StartType.COLD, _now(game))
    assert default_start_type(flight) is StartType.IN_FLIGHT


def test_start_type_route_validates_the_value(game: Game) -> None:
    package, flight = _sead(game)
    url = _url(package, flight, "start-type")

    assert _request("PUT", url, {"start_type": "Warm"})[0] == 200
    assert flight.start_type is StartType.WARM
    assert _request("PUT", url, {"start_type": "Teleport"})[0] == 422


# --- Divert -----------------------------------------------------------------------


def _divert(flight: Flight) -> Any:
    return flight.divert


def test_divert_options_are_friendly_and_usable(game: Game) -> None:
    _, flight = _sead(game)
    options = divert_options(flight)
    assert options
    assert all(cp.captured == game.blue.player for cp in options)
    assert all(cp.can_operate(flight.unit_type) for cp in options)
    assert [cp.name for cp in options] == sorted(cp.name for cp in options)


def test_divert_replans_the_flight_and_can_be_removed(game: Game) -> None:
    _, flight = _sead(game)
    divert = divert_options(flight)[0]

    set_flight_divert(flight, divert)
    assert _divert(flight) == divert
    assert flight.flight_plan.layout.divert is not None

    set_flight_divert(flight, None)
    assert _divert(flight) is None


def test_divert_to_an_enemy_field_is_refused(game: Game) -> None:
    _, flight = _sead(game)
    enemy = next(
        cp for cp in game.theater.controlpoints if cp.captured != game.blue.player
    )
    with pytest.raises(CommandError, match="cannot divert"):
        set_flight_divert(flight, enemy)
    assert flight.divert is None


def test_a_plan_that_fails_keeps_the_divert(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, flight = _sead(game)
    divert = divert_options(flight)[0]

    def refuse(_self: Flight, dump_debug_info: bool = False) -> None:
        raise PlanningError("no route")

    monkeypatch.setattr(Flight, "recreate_flight_plan", refuse)
    with pytest.raises(CommandError, match="no route"):
        set_flight_divert(flight, divert)
    assert flight.divert is None


def test_divert_route_takes_an_id_or_null(game: Game) -> None:
    package, flight = _sead(game)
    url = _url(package, flight, "divert")
    divert = divert_options(flight)[0]

    assert _request("PUT", url, {"divert_id": str(divert.id)})[0] == 200
    assert _divert(flight) == divert
    assert _request("PUT", url, {"divert_id": None})[0] == 200
    assert _divert(flight) is None
    assert _request("PUT", url, {"divert_id": str(uuid4())})[0] == 404


# --- TOT offset, name, callsign ------------------------------------------------------


def test_tot_offset_moves_the_flight_and_stays_in_range(game: Game) -> None:
    package, flight = _sead(game)
    package.auto_asap = False
    default = flight.flight_plan.tot
    offset = flight.flight_plan.tot_offset

    set_flight_tot_offset(flight, offset - timedelta(seconds=90), _now(game))
    assert flight.flight_plan.tot == default - timedelta(seconds=90)

    with pytest.raises(CommandError, match="59:59"):
        set_flight_tot_offset(flight, timedelta(hours=1), _now(game))
    with pytest.raises(CommandError, match="59:59"):
        set_flight_tot_offset(flight, -timedelta(hours=1), _now(game))


def test_custom_name_is_trimmed_and_refuses_a_bar(game: Game) -> None:
    package, flight = _sead(game)
    url = _url(package, flight, "custom-name")

    status, body = _request("PUT", url, {"name": "  Viper 1 "})
    assert status == 200
    assert body["flights"][0]["custom_name"] == "Viper 1"

    assert _request("PUT", url, {"name": "a|b"}) == (
        409,
        {"detail": "Cannot include | in flight name"},
    )
    assert flight.custom_name == "Viper 1"

    assert _request("PUT", url, {"name": " "})[0] == 200
    assert flight.custom_name is None


def test_callsign_comes_from_the_list_with_a_number_of_one_digit(game: Game) -> None:
    _, flight = _sead(game)
    name = flight.available_callsigns[0]

    set_callsign(flight, name, 3)
    assert flight.callsign is not None
    assert (flight.callsign.name, flight.callsign.nr) == (name, 3)

    with pytest.raises(CommandError, match="not an available"):
        set_callsign(flight, "Nobody", 1)
    with pytest.raises(CommandError, match="1 to 9"):
        set_callsign(flight, name, 10)


def test_callsign_routes_set_and_reset(game: Game) -> None:
    package, flight = _sead(game)
    url = _url(package, flight, "callsign")
    name = flight.available_callsigns[0]

    assert _request("PUT", url, {"name": name, "number": 2})[0] == 200
    _, settings = _request("GET", _url(package, flight, "settings"))
    assert settings["callsign"] == {"name": name, "number": 2}

    assert _request("DELETE", url)[0] == 200
    assert flight.callsign is None
    _, settings = _request("GET", _url(package, flight, "settings"))
    assert settings["callsign"] is None


def test_a_callsign_follows_a_new_squadron_of_the_same_country(game: Game) -> None:
    _, flight = _dead(game)
    set_callsign(flight, flight.available_callsigns[0], 4)
    replacement = change_flight_squadron(
        flight, _other_squadron(game, flight), _now(game)
    )
    assert replacement.callsign is flight.callsign


# --- A flight under way --------------------------------------------------------------


@pytest.mark.parametrize(
    "tail, body",
    [
        ("size", {"size": 1}),
        ("start-type", {"start_type": "Warm"}),
        ("divert", {"divert_id": None}),
        ("tot-offset", {"seconds": 0}),
        ("pilots/0", {"pilot_id": None}),
        ("pilots/0/player", {"player": True}),
    ],
)
def test_a_flight_under_way_cannot_change(
    game: Game,
    monkeypatch: pytest.MonkeyPatch,
    tail: str,
    body: dict[str, Any],
) -> None:
    package, flight = _sead(game)
    _under_way(flight, monkeypatch)

    status, answer = _request("PUT", _url(package, flight, tail), body)

    assert status == 409
    assert "under way" in answer["detail"]


# --- Read model -----------------------------------------------------------------------


def test_settings_read_model_lists_what_the_engine_offers(game: Game) -> None:
    package, flight = _sead(game)
    set_flight_pilot(flight, 1, None, _now(game))

    status, body = _request("GET", _url(package, flight, "settings"))

    assert status == 200
    assert body["id"] == str(flight.id)
    assert body["task"] == "SEAD"
    assert body["aircraft"] == str(flight.unit_type)
    assert body["squadron"]["id"] == str(flight.squadron.id)
    assert body["count"] == 2
    assert body["max_count"] == max_flight_resize(flight)
    assert body["start_type"] == flight.start_type.value
    assert body["start_types"] == [s.value for s in StartType]
    assert body["start_type_locked"] is False
    assert body["divert_id"] is None
    assert body["editable"] is True
    assert body["callsign"] is None
    assert body["callsign_names"] == flight.available_callsigns
    assert len(body["slots"]) == 2
    assert body["slots"][0]["pilot"]["id"] == str(flight.roster.pilot_at(0).id)  # type: ignore[union-attr]
    assert body["slots"][1] == {"pilot": None, "player_refusal": None}
    free_ids = {pilot["id"] for pilot in body["free_pilots"]}
    assert free_ids == {str(p.id) for p in flight.squadron.available_pilots}


def test_free_pilots_list_players_first(game: Game) -> None:
    package, flight = _sead(game)
    squadron = flight.squadron
    pilot: Pilot = squadron.available_pilots[-1]
    pilot.player = True
    try:
        _, body = _request("GET", _url(package, flight, "settings"))
        assert body["free_pilots"][0]["id"] == str(pilot.id)
    finally:
        pilot.player = False


def test_settings_of_an_unknown_flight_is_404(game: Game) -> None:
    package, _ = _sead(game)
    status, _body = _request(
        "GET", f"/packages/{package.id}/flights/{uuid4()}/settings"
    )
    assert status == 404


# --- W16 ------------------------------------------------------------------------------


def test_name_and_callsign_leave_the_fingerprint_alone(game: Game) -> None:
    package, flight = _sead(game)
    before = fingerprint_package(package)

    set_flight_custom_name(flight, "Viper")
    set_callsign(flight, flight.available_callsigns[0], 1)
    set_flight_divert(flight, None)

    assert fingerprint_package(package) == before


def test_off_map_bases_lock_the_start_type_in_the_read_model(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    package, flight = _sead(game)
    monkeypatch.setattr(
        type(flight.departure),
        "required_aircraft_start_type",
        property(lambda _self: StartType.IN_FLIGHT),
    )
    _, body = _request("GET", _url(package, flight, "settings"))
    assert body["start_type_locked"] is True


def test_a_country_without_air_callsigns_still_has_a_settings_sheet() -> None:
    # pydcs has no "Air" callsigns for some countries: the sheet must still load.
    from dcs.countries import Ukraine

    assert "Air" not in Ukraine.callsign
    flight = Flight.__new__(Flight)
    flight.squadron = cast(
        Any,
        SimpleNamespace(
            aircraft=SimpleNamespace(
                dcs_unit_type=SimpleNamespace(category="Air", callnames={})
            ),
            coalition=SimpleNamespace(faction=SimpleNamespace(country=Ukraine)),
        ),
    )
    assert flight.available_callsigns == []

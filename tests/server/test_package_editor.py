"""WEB-04.1: the commands of the package editor, on a real generated game.

W16 checks what they plan (`tests/flightplans`). Here: the rules and the routes.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator
from uuid import uuid4

import pytest

from game import Game, liberation_install
from game.dcs.aircrafttype import AircraftType
from game.ato import Flight, FlightType, Package
from game.ato.flightplans.planningerror import PlanningError
from game.ato.starttype import StartType
from game.commander.packagefulfiller import PackageFulfiller
from game.commands import CommandError
from game.commands.packageflights import (
    add_flight,
    auto_create_default_count,
    default_loadout,
)
from game.commands.packages import create_package, set_package_tot
from game.server import GameContext
from game.server.eventstream import EventStream
from game.sim import GameUpdateEvents
from game.squadrons import Squadron
from game.theater import TheaterGroundObject
from game.theater.theatergroundobject import SamGroundObject
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)
from tests.server.test_packages_routes import _request

F15C = "F-15C Eagle"
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


def _squadron(game: Game, aircraft: str) -> Squadron:
    return next(
        s
        for s in game.blue.air_wing.iter_squadrons()
        if s.aircraft.display_name == aircraft
    )


def _sam_package(game: Game) -> Package:
    return create_package(game, _sam(game), _now(game))


def _add_sead(game: Game, package: Package, size: int = 2) -> Flight:
    return add_flight(
        game, package, FlightType.SEAD, _squadron(game, F16), size, _now(game)
    )


def _post_flight(
    package: Package, squadron: Squadron, **fields: Any
) -> tuple[int, Any]:
    body = {"task": "SEAD", "squadron_id": str(squadron.id), "size": 2, **fields}
    return _request("POST", f"/packages/{package.id}/flights", body)


# --- create and read -----------------------------------------------------------


def test_create_route_plans_an_empty_asap_package(game: Game) -> None:
    sam = _sam(game)
    status, body = _request(
        "POST", "/packages/", {"target_kind": "tgo", "target_id": str(sam.id)}
    )

    assert status == 201
    assert [str(p.id) for p in game.blue.ato.packages] == [body["id"]]
    assert body["target"] == sam.name
    assert body["auto_asap"] is True
    assert body["blue"] is True
    assert body["flights"] == []
    assert body["can_auto_create"] is True
    assert body["tot_locked"] is False
    assert body["tot"] == _now(game).isoformat()


def test_get_package_describes_its_flights(game: Game) -> None:
    package = _sam_package(game)
    flight = _add_sead(game, package)

    status, body = _request("GET", f"/packages/{package.id}")

    assert status == 200
    assert body["task"] == "SEAD"
    assert body["can_auto_create"] is False
    assert body["closest_base"] == flight.departure.name
    assert body["closest_base_distance_nm"] > 0
    row = body["flights"][0]
    assert row["id"] == str(flight.id)
    assert row["start_type"] == flight.start_type.value
    assert row["cancelable"] is True
    assert row["startup"] < row["takeoff"] < body["tot"]


def test_unknown_package_is_a_404(game: Game) -> None:
    assert _request("GET", f"/packages/{uuid4()}") == (
        404,
        {"detail": "This package is no longer planned."},
    )


def test_rename_route(game: Game) -> None:
    package = _sam_package(game)
    url = f"/packages/{package.id}/name"
    status, body = _request("PUT", url, {"name": " Viper "})
    assert (status, body["custom_name"]) == (200, "Viper")
    _, body = _request("PUT", url, {"name": "  "})
    assert body["custom_name"] is None


# --- TOT -----------------------------------------------------------------------


def test_typed_tot_ends_asap_and_keeps_the_day(game: Game) -> None:
    package = _sam_package(game)
    _add_sead(game, package)
    day = package.time_over_target.date()

    status, body = _request("PUT", f"/packages/{package.id}/tot", {"tot": "23:45:10"})

    assert status == 200
    assert body["auto_asap"] is False
    assert package.time_over_target == datetime.combine(day, time(23, 45, 10))


def test_tot_of_a_package_without_one_starts_from_now(game: Game) -> None:
    package = _sam_package(game)
    package.time_over_target = datetime.min
    set_package_tot(package, time(8, 0), _now(game))
    assert package.time_over_target.date() == _now(game).date()


def test_earliest_tot_goes_back_to_asap(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    package = _sam_package(game)
    flight = _add_sead(game, package)
    earliest = package.time_over_target
    package.auto_asap = False
    package.time_over_target = earliest + timedelta(hours=3)

    status, body = _request("POST", f"/packages/{package.id}/tot/earliest")

    assert status == 200
    assert body["auto_asap"] is True
    assert package.time_over_target == earliest
    assert flight in published[-1].updated_flights


def test_tot_is_fixed_once_a_flight_started(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _sam_package(game)
    monkeypatch.setattr(Package, "all_flights_waiting_for_start", lambda self: False)
    for method, path, body in (
        ("PUT", "tot", {"tot": "08:00:00"}),
        ("POST", "tot/earliest", None),
    ):
        status, _ = _request(method, f"/packages/{package.id}/{path}", body)
        assert status == 409
    _, detail = _request("GET", f"/packages/{package.id}")
    assert detail["tot_locked"] is True


# --- add flight ----------------------------------------------------------------


def test_flight_options_list_the_players_modules_first(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = f"/packages/{_sam_package(game).id}/flight-options"
    aircraft = next(
        t["aircraft"]
        for t in _request("GET", path)[1]["tasks"]
        if len(t["aircraft"]) > 1
    )
    assert not any(a["player_module"] for a in aircraft)
    last = aircraft[-1]
    module = AircraftType.named(last["id"]).dcs_unit_type.id
    monkeypatch.setattr(liberation_install, "owned_modules", lambda: [module])

    tasks = _request("GET", path)[1]["tasks"]

    listed = next(t["aircraft"] for t in tasks if last["id"] in map(_id, t["aircraft"]))
    assert listed[0]["id"] == last["id"]
    assert listed[0]["player_module"] is True


def _id(option: dict[str, Any]) -> str:
    return option["id"]


def test_flight_options_follow_the_target_and_the_air_wing(game: Game) -> None:
    package = _sam_package(game)

    status, body = _request("GET", f"/packages/{package.id}/flight-options")

    assert status == 200
    assert body["start_types"] == [s.value for s in StartType]
    tasks = {t["task"]: t for t in body["tasks"]}
    assert "SEAD" in tasks
    assert "BARCAP" not in tasks
    viper = next(a for a in tasks["SEAD"]["aircraft"] if a["name"] == F16)
    squadron = viper["squadrons"][0]
    expected = _squadron(game, F16)
    assert squadron["id"] == str(expected.id)
    assert squadron["base"] == expected.location.name
    assert squadron["max_size"] == min(
        expected.untasked_aircraft, expected.aircraft.max_group_size
    )
    assert squadron["required_start_type"] is None


def test_add_flight_route_plans_it(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    package = _sam_package(game)
    squadron = _squadron(game, F16)
    available = squadron.untasked_aircraft

    status, body = _post_flight(package, squadron)

    assert status == 201
    flight = package.flights[0]
    assert body["flights"][0]["id"] == str(flight.id)
    assert flight.flight_plan.waypoints
    assert squadron.untasked_aircraft == available - 2
    assert flight.start_type is game.settings.start_type_for(
        FlightType.SEAD, has_players=False
    )
    # An ASAP package gets the earliest TOT of its flights.
    assert package.time_over_target > _now(game)
    assert flight in published[-1].new_flights
    member = next(iter(flight.iter_members()))
    assert (
        member.loadout.name
        == default_loadout(squadron.aircraft, flight.flight_type).name
    )


def test_add_flight_route_takes_a_start_type(game: Game) -> None:
    package = _sam_package(game)
    status, _ = _post_flight(package, _squadron(game, F16), start_type="Runway")
    assert status == 201
    assert package.flights[0].start_type is StartType.RUNWAY


def test_a_base_that_dictates_its_start_type_wins(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _sam_package(game)
    squadron = _squadron(game, F16)
    monkeypatch.setattr(
        type(squadron.location),
        "required_aircraft_start_type",
        property(lambda self: StartType.IN_FLIGHT),
    )
    flight = add_flight(
        game,
        package,
        FlightType.SEAD,
        squadron,
        2,
        _now(game),
        StartType.COLD,
    )
    assert flight.start_type is StartType.IN_FLIGHT


@pytest.mark.parametrize(
    "fields, detail",
    [
        ({"task": "BARCAP"}, "cannot be flown"),
        ({"size": 0}, "at least one aircraft"),
        ({"size": 500}, "aircraft available"),
    ],
)
def test_add_flight_refusals_claim_nothing(
    game: Game, fields: dict[str, Any], detail: str
) -> None:
    package = _sam_package(game)
    squadron = _squadron(game, F16)
    available = squadron.untasked_aircraft

    status, body = _post_flight(package, squadron, **fields)

    assert status == 409
    assert detail in body["detail"]
    assert package.flights == []
    assert squadron.untasked_aircraft == available


def test_add_flight_refuses_more_than_a_group(game: Game) -> None:
    package = _sam_package(game)
    squadron = _squadron(game, F16)
    size = squadron.aircraft.max_group_size + 1
    squadron.owned_aircraft += size
    try:
        status, body = _post_flight(package, squadron, size=size)
    finally:
        squadron.owned_aircraft -= size
    assert status == 409
    assert "at most" in body["detail"]


def test_add_flight_unknown_task_and_squadron(game: Game) -> None:
    package = _sam_package(game)
    squadron = _squadron(game, F16)
    assert _post_flight(package, squadron, task="Nope")[0] == 422
    assert _post_flight(package, squadron, squadron_id=str(uuid4()))[0] == 404
    assert _post_flight(package, squadron, start_type="Nope")[0] == 422


def test_a_flight_that_cannot_be_planned_leaves_the_package(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _sam_package(game)
    squadron = _squadron(game, F16)
    available = squadron.untasked_aircraft

    def fail(self: Flight) -> None:
        raise PlanningError("no route")

    monkeypatch.setattr(Flight, "recreate_flight_plan", fail)
    status, body = _post_flight(package, squadron)

    assert status == 409
    assert "no route" in body["detail"]
    assert package.flights == []
    assert squadron.untasked_aircraft == available


# --- only escorts --------------------------------------------------------------


def test_an_escort_needs_a_flight_to_escort(game: Game) -> None:
    package = _sam_package(game)
    with pytest.raises(CommandError, match="escort first"):
        add_flight(
            game,
            package,
            FlightType.SEAD_ESCORT,
            _squadron(game, F16),
            2,
            _now(game),
        )
    assert package.flights == []


def test_the_last_escorted_flight_stays_until_its_escorts_left(game: Game) -> None:
    package = _sam_package(game)
    main = _add_sead(game, package)
    escort = add_flight(
        game, package, FlightType.ESCORT, _squadron(game, F15C), 2, _now(game)
    )

    status, body = _request("DELETE", f"/packages/{package.id}/flights/{main.id}")
    assert status == 409
    assert "only escort" in body["detail"]
    assert package.flights == [main, escort]

    assert _request("DELETE", f"/packages/{package.id}/flights/{escort.id}")[0] == 200
    assert _request("DELETE", f"/packages/{package.id}/flights/{main.id}")[0] == 200
    assert package.flights == []


# --- remove flight -------------------------------------------------------------


def test_remove_flight_returns_its_aircraft(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    package = _sam_package(game)
    squadron = _squadron(game, F16)
    available = squadron.untasked_aircraft
    flight = _add_sead(game, package)

    status, body = _request("DELETE", f"/packages/{package.id}/flights/{flight.id}")

    assert status == 200
    assert body["flights"] == []
    assert body["can_auto_create"] is True
    assert squadron.untasked_aircraft == available
    assert flight.id in published[-1].deleted_flights


def test_remove_an_unknown_flight(game: Game) -> None:
    package = _sam_package(game)
    status, body = _request("DELETE", f"/packages/{package.id}/flights/{uuid4()}")
    assert (status, body) == (404, {"detail": "This flight is no longer planned."})


# --- auto-create ---------------------------------------------------------------


def test_auto_create_options(game: Game) -> None:
    package = _sam_package(game)

    status, body = _request("GET", f"/packages/{package.id}/auto-create")

    assert status == 200
    assert "DEAD" in [p["task"] for p in body["primary"]]
    primary = body["primary"][0]
    assert primary["default_count"] == auto_create_default_count(package.target)
    assert [s["task"] for s in body["support"]][:2] == ["TARCAP", "Escort"]
    assert sorted(body["excluded_with_cas"]) == ["Escort", "SEAD", "SEAD Escort"]
    assert (body["min_count"], body["max_count"]) == (1, 4)


def test_auto_create_keeps_the_package_id_and_place(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    other = _sam_package(game)
    package = _sam_package(game)
    last = _sam_package(game)
    package.custom_name = "Viper"

    status, body = _request(
        "POST",
        f"/packages/{package.id}/auto-create",
        {"flights": [{"task": "DEAD", "count": 2}]},
    )

    assert status == 200
    assert body["id"] == str(package.id)
    assert body["custom_name"] == "Viper"
    assert body["task"] == "DEAD"
    assert body["auto_asap"] is True
    planned = game.blue.ato.packages[1]
    assert planned is not package
    assert game.blue.ato.packages == [other, planned, last]
    assert {f.id for f in published[-1].new_flights} == {f.id for f in planned.flights}


def test_auto_create_needs_an_empty_package(game: Game) -> None:
    package = _sam_package(game)
    _add_sead(game, package)
    status, body = _request(
        "POST",
        f"/packages/{package.id}/auto-create",
        {"flights": [{"task": "DEAD", "count": 2}]},
    )
    assert (status, body) == (409, {"detail": "Auto-create needs an empty package."})


def test_auto_create_without_aircraft_keeps_the_empty_package(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _sam_package(game)
    monkeypatch.setattr(PackageFulfiller, "plan_mission", lambda *_, **__: None)
    status, body = _request(
        "POST",
        f"/packages/{package.id}/auto-create",
        {"flights": [{"task": "DEAD", "count": 2}]},
    )
    assert status == 409
    assert "insufficient" in body["detail"]
    assert game.blue.ato.packages == [package]


@pytest.mark.parametrize(
    "flights, status",
    [
        ([], 409),
        ([{"task": "BARCAP", "count": 2}], 409),
        ([{"task": "DEAD", "count": 9}], 409),
        ([{"task": "DEAD", "count": 2}, {"task": "BARCAP", "count": 2}], 409),
        ([{"task": "Nope", "count": 2}], 422),
        ([{"task": "DEAD", "count": 2, "aircraft": "Nope"}], 422),
    ],
)
def test_auto_create_refusals(
    game: Game, flights: list[dict[str, Any]], status: int
) -> None:
    package = _sam_package(game)
    answer, _ = _request(
        "POST", f"/packages/{package.id}/auto-create", {"flights": flights}
    )
    assert answer == status
    assert game.blue.ato.packages == [package]


def test_a_cas_package_takes_no_escort(game: Game) -> None:
    front = next(iter(game.theater.conflicts()))
    package = create_package(game, front, _now(game))
    status, body = _request(
        "POST",
        f"/packages/{package.id}/auto-create",
        {"flights": [{"task": "CAS", "count": 2}, {"task": "Escort", "count": 2}]},
    )
    assert status == 409
    assert "CAS package" in body["detail"]


# --- delete --------------------------------------------------------------------


def test_delete_an_empty_package(game: Game) -> None:
    package = _sam_package(game)
    assert _request("DELETE", f"/packages/{package.id}") == (204, None)
    assert game.blue.ato.packages == []

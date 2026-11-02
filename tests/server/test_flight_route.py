"""WEB-04.4: the commands of the Route tab, on a real generated game."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator
from uuid import uuid4

import pytest
from shapely.geometry import Polygon

from game import Game
from game.ato import Flight, FlightType, Package
from game.ato.flightplans.custom import CustomFlightPlan
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.commands import CommandError
from game.commands.flightroute import (
    WaypointTimeKind,
    add_predefined_waypoint,
    add_rtb_waypoint,
    delete_waypoint,
    deletion_degrades,
    insert_nav_after,
    is_bulk_editable,
    move_waypoint,
    predefined_waypoints,
    recreate_route,
    select_predefined_waypoints,
    set_en_route_altitude,
    set_waypoint_altitude,
    threat_warning,
    waypoint_times,
)
from game.commands.packageflights import add_flight
from game.commands.packages import create_package
from game.server import GameContext
from game.server.eventstream import EventStream
from game.server.flightroute.models import FlightRouteJs
from game.sim import GameUpdateEvents
from game.squadrons import Squadron
from game.theater.theatergroundobject import BuildingGroundObject, SamGroundObject
from game.threatzones import ThreatZones
from game.utils import feet
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)
from tests.server.test_packages_routes import _request

F15C = "F-15C Eagle"
F15E = "F-15E Strike Eagle (AI)"


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
            package.remove_flight(flight)
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


def _plan(
    game: Game, task: FlightType = FlightType.STRIKE, aircraft: str = F15E
) -> tuple[Package, Flight]:
    target = min(
        (
            tgo
            for tgo in game.theater.ground_objects
            if isinstance(tgo, BuildingGroundObject)
            and not tgo.is_friendly(game.blue.player)
            and not tgo.is_dead
        ),
        key=lambda t: (
            t.position.distance_to_point(
                game.theater.control_point_named("Ramat David").position
            ),
            t.name,
        ),
    )
    now = game.conditions.start_time
    package = create_package(game, target, now)
    flight = add_flight(game, package, task, _squadron(game, aircraft), 2, now)
    return package, flight


def _of_type(flight: Flight, *types: FlightWaypointType) -> FlightWaypoint:
    return next(w for w in flight.flight_plan.waypoints if w.waypoint_type in types)


def _index(flight: Flight, waypoint: FlightWaypoint) -> int:
    return [w is waypoint for w in flight.flight_plan.waypoints].index(True)


def _added(before: list[FlightWaypoint], after: list[FlightWaypoint]) -> FlightWaypoint:
    new = [w for w in after if all(w is not old for old in before)]
    assert len(new) == 1
    return new[0]


def _url(flight: Flight, rest: str = "") -> str:
    return f"/flights/{flight.id}/route{rest}"


def test_route_reads_the_table_of_the_plan(game: Game) -> None:
    _, flight = _plan(game)
    route = FlightRouteJs.for_flight(game, flight)
    assert [w.index for w in route.waypoints] == list(
        range(len(flight.flight_plan.waypoints))
    )
    first = route.waypoints[0]
    assert first.type == "TAKEOFF"
    assert first.time == flight.flight_plan.takeoff_time()
    assert first.time_kind == "takeoff"
    assert not first.is_movable
    assert not first.can_delete
    target = next(w for w in route.waypoints if w.is_tot)
    assert target.time == flight.flight_plan.tot
    assert target.time_kind == "tot"
    assert route.recreate_tasks[0] == "Strike"
    assert not route.is_custom
    assert route.bulk_altitude_ft == max(
        round(w.alt.feet) for w in flight.flight_plan.waypoints if is_bulk_editable(w)
    )
    # Not flown: not on the path of the map.
    bullseye = next(w for w in route.waypoints if w.type == "BULLSEYE")
    assert not bullseye.include_in_path


def test_times_are_in_flying_order(game: Game) -> None:
    _, flight = _plan(game)
    times = [t for t in waypoint_times(flight) if t is not None]
    assert times[0].kind is WaypointTimeKind.TAKEOFF
    estimated = [t for t in times if t.kind is WaypointTimeKind.ESTIMATED]
    assert estimated
    # What the Qt list shows.
    depart = next(t for t in times if t.kind is WaypointTimeKind.DEPART)
    assert str(depart).startswith("Depart ")
    assert str(times[0]) == f"{times[0].time:%H:%M:%S}"


def test_min_fuel_falls_to_the_safe_reserve_at_landing(game: Game) -> None:
    squadron = next(
        s
        for s in game.blue.air_wing.iter_squadrons()
        if s.aircraft.fuel_consumption is not None
        and s.capable_of(FlightType.STRIKE)
        and s.untasked_aircraft >= 2
    )
    _, flight = _plan(game, aircraft=squadron.aircraft.display_name)
    consumption = flight.unit_type.fuel_consumption
    assert consumption is not None
    route = FlightRouteJs.for_flight(game, flight)
    fuel = [w.min_fuel_lb for w in route.waypoints]
    landing = next(
        i for i, w in enumerate(route.waypoints) if w.type == "LANDING_POINT"
    )
    assert fuel[landing] == round(consumption.min_safe)
    # Past the landing point there is nothing to estimate.
    assert all(f is None for f in fuel[landing + 1 :])
    flown = [f for f in fuel[: landing + 1] if f is not None]
    assert flown == sorted(flown, reverse=True)
    assert flown[0] > flown[-1]


def test_min_fuel_is_empty_without_fuel_data_or_a_landing_point(game: Game) -> None:
    _, flight = _plan(game)
    assert flight.unit_type.fuel_consumption is None
    assert flight.flight_plan.estimate_min_fuel(flight.flight_plan.waypoints) == {}

    squadron = next(
        s
        for s in game.blue.air_wing.iter_squadrons()
        if s.aircraft.fuel_consumption is not None
        and s.capable_of(FlightType.STRIKE)
        and s.untasked_aircraft >= 2
    )
    _, flight = _plan(game, aircraft=squadron.aircraft.display_name)
    plan = flight.flight_plan
    assert plan.estimate_min_fuel(plan.waypoints[:2]) == {}


def test_read_changes_nothing(game: Game) -> None:
    _, flight = _plan(game)
    before = list(flight.flight_plan.waypoints)
    FlightRouteJs.for_flight(game, flight)
    after = flight.flight_plan.waypoints
    assert len(before) == len(after)
    assert all(a is b for a, b in zip(before, after))


def test_move_refuses_a_fixed_waypoint(game: Game) -> None:
    _, flight = _plan(game)
    takeoff = flight.flight_plan.waypoints[0]
    with pytest.raises(CommandError, match="cannot be moved"):
        move_waypoint(flight, takeoff, takeoff.position)


def test_moving_a_primary_flight_waypoint_moves_the_package(game: Game) -> None:
    package, flight = _plan(game)
    now = game.conditions.start_time
    escort = add_flight(game, package, FlightType.ESCORT, _squadron(game, F15C), 2, now)
    assert package.primary_flight is flight
    join = _of_type(flight, FlightWaypointType.JOIN)
    moved = join.position.point_from_heading(90, 5000)
    move_waypoint(flight, join, moved)
    assert package.waypoints is not None
    assert package.waypoints.join == moved
    assert _of_type(escort, FlightWaypointType.JOIN).position == moved


def test_altitude_limits(game: Game) -> None:
    _, flight = _plan(game)
    waypoint = flight.flight_plan.waypoints[1]
    set_waypoint_altitude(waypoint, 25000)
    assert round(waypoint.alt.feet) == 25000
    with pytest.raises(CommandError, match="between 0 and 40000"):
        set_waypoint_altitude(waypoint, 40001)


def test_bulk_altitude_leaves_the_tied_waypoints(game: Game) -> None:
    _, flight = _plan(game)
    fixed = {
        id(w): w.alt for w in flight.flight_plan.waypoints if not is_bulk_editable(w)
    }
    assert fixed
    set_en_route_altitude(flight, 31000)
    for waypoint in flight.flight_plan.waypoints:
        if id(waypoint) in fixed:
            assert waypoint.alt == fixed[id(waypoint)]
        else:
            assert waypoint.alt == feet(31000)


def test_insert_nav_goes_halfway_after_the_selected_waypoint(game: Game) -> None:
    _, flight = _plan(game)
    waypoints = flight.flight_plan.waypoints
    insert_nav_after(flight, 0)
    after = flight.flight_plan.waypoints
    assert len(after) == len(waypoints) + 1
    added = _added(waypoints, after)
    assert added.waypoint_type is FlightWaypointType.NAV
    assert added.position == waypoints[0].position.lerp(waypoints[1].position, 0.5)


def test_insert_nav_refused_where_the_plan_has_no_room(game: Game) -> None:
    _, flight = _plan(game)
    route = FlightRouteJs.for_flight(game, flight)
    refused = next(w for w in route.waypoints if not w.can_insert_after)
    with pytest.raises(CommandError, match="NAV point cannot follow"):
        insert_nav_after(flight, refused.index)
    assert len(flight.flight_plan.waypoints) == len(route.waypoints)


def test_insert_nav_works_on_a_custom_plan(game: Game) -> None:
    _, flight = _plan(game)
    flight.degrade_to_custom_flight_plan()
    before = flight.flight_plan.waypoints
    insert_nav_after(flight, 1)
    after = flight.flight_plan.waypoints
    assert len(after) == len(before) + 1
    assert after[1] is before[1]
    assert after[2].waypoint_type is FlightWaypointType.NAV
    assert after[3] is before[2]


def test_delete_a_nav_point_keeps_the_plan(game: Game) -> None:
    _, flight = _plan(game)
    plan = flight.flight_plan
    before = plan.waypoints
    insert_nav_after(flight, 0)
    nav = _added(before, plan.waypoints)
    assert not deletion_degrades(flight, nav)
    delete_waypoint(flight, nav, allow_degrade=False)
    assert flight.flight_plan is plan
    assert all(w is not nav for w in plan.waypoints)


def test_delete_a_structural_waypoint_needs_the_confirmation(game: Game) -> None:
    _, flight = _plan(game)
    join = _of_type(flight, FlightWaypointType.JOIN)
    count = len(flight.flight_plan.waypoints)
    assert deletion_degrades(flight, join)
    # Asking changes nothing.
    assert len(flight.flight_plan.waypoints) == count
    assert not flight.flight_plan.is_custom
    with pytest.raises(CommandError, match="custom flight plan"):
        delete_waypoint(flight, join, allow_degrade=False)
    assert not flight.flight_plan.is_custom

    delete_waypoint(flight, join, allow_degrade=True)
    assert isinstance(flight.flight_plan, CustomFlightPlan)
    assert len(flight.flight_plan.waypoints) == count - 1
    assert all(w is not join for w in flight.flight_plan.waypoints)


def test_the_first_waypoint_stays(game: Game) -> None:
    _, flight = _plan(game)
    with pytest.raises(CommandError, match="first waypoint"):
        delete_waypoint(flight, flight.flight_plan.waypoints[0], allow_degrade=True)


def test_rtb_needs_the_confirmation_and_ends_custom(game: Game) -> None:
    _, flight = _plan(game)
    with pytest.raises(CommandError, match="custom flight plan"):
        add_rtb_waypoint(flight, allow_degrade=False)
    add_rtb_waypoint(flight, allow_degrade=True)
    assert flight.flight_plan.is_custom
    assert (
        flight.flight_plan.waypoints[-1].waypoint_type
        is FlightWaypointType.LANDING_POINT
    )


def test_predefined_waypoints_come_with_their_object(game: Game) -> None:
    player = game.blue.player
    waypoints = predefined_waypoints(game, player)
    kinds = {w.description.split(":")[0] for w in waypoints}
    assert {"Frontline", "Enemy unit", "Friendly unit"} <= kinds
    assert any(w.description.endswith("[Enemy Airbase]") for w in waypoints)
    assert not predefined_waypoints(
        game, player, include_frontlines=False, include_airbases=False
    )[0].description.startswith("Frontline")

    enemy = next(w for w in waypoints if w.description.startswith("Enemy unit"))
    assert enemy.waypoint_type is FlightWaypointType.TARGET_POINT
    same = select_predefined_waypoints(waypoints, enemy.pretty_name, True)
    assert all(w.obj_name == enemy.obj_name for w in same)
    assert select_predefined_waypoints(waypoints, enemy.pretty_name, False) == [enemy]
    assert select_predefined_waypoints(waypoints, "nowhere", True) == []


def test_add_predefined_goes_at_the_end(game: Game) -> None:
    _, flight = _plan(game)
    name = next(
        w.pretty_name
        for w in predefined_waypoints(game, game.blue.player)
        if w.description.endswith("[Friendly Airbase]")
    )
    add_predefined_waypoint(game, flight, name, False)
    assert flight.flight_plan.waypoints[-1].pretty_name == name
    assert not flight.flight_plan.is_custom
    with pytest.raises(CommandError, match="no longer available"):
        add_predefined_waypoint(game, flight, "nowhere", True)


def test_recreate_restores_a_degraded_route(game: Game) -> None:
    _, flight = _plan(game)
    types = [w.waypoint_type for w in flight.flight_plan.waypoints]
    delete_waypoint(
        flight, _of_type(flight, FlightWaypointType.JOIN), allow_degrade=True
    )
    recreate_route(game, flight, FlightType.STRIKE)
    assert not flight.flight_plan.is_custom
    assert [w.waypoint_type for w in flight.flight_plan.waypoints] == types


def test_recreate_as_another_task(game: Game) -> None:
    package, flight = _plan(game)
    now = game.conditions.start_time
    add_flight(game, package, FlightType.ESCORT, _squadron(game, F15C), 2, now)
    second = package.flights[1]
    recreate_route(game, second, FlightType.SEAD_ESCORT)
    assert second.flight_type is FlightType.SEAD_ESCORT


def test_recreate_refuses_a_task_the_target_cannot_take(game: Game) -> None:
    _, flight = _plan(game)
    with pytest.raises(CommandError, match="cannot be flown"):
        recreate_route(game, flight, FlightType.BARCAP)
    assert flight.flight_type is FlightType.STRIKE


def test_recreate_refuses_a_package_of_escorts(game: Game) -> None:
    _, flight = _plan(game)
    with pytest.raises(CommandError, match="only escort"):
        recreate_route(game, flight, FlightType.ESCORT)
    assert flight.flight_type is FlightType.STRIKE


def test_threat_warning_names_the_air_defense(game: Game) -> None:
    _, flight = _plan(game)
    waypoint = flight.flight_plan.waypoints[1]
    sam = next(
        tgo
        for tgo in game.theater.ground_objects
        if isinstance(tgo, SamGroundObject)
        and not tgo.is_friendly(game.blue.player)
        and tgo.has_aa
        and game.red.threat_zone.threatened_by_air_defense(tgo.position)
    )
    original = waypoint.position
    waypoint.position = sam.position
    try:
        warning = threat_warning(flight, 1, waypoint)
        assert warning is not None
        assert warning.startswith("Waypoint 1 is inside the threat ring of ")
        assert sam.obj_name in warning
    finally:
        waypoint.position = original


def test_no_threat_warning_at_a_safe_point_or_off_the_path(game: Game) -> None:
    _, flight = _plan(game)
    bullseye = _of_type(flight, FlightWaypointType.BULLSEYE)
    assert threat_warning(flight, 9, bullseye) is None
    takeoff = flight.flight_plan.waypoints[0]
    zones = game.red.threat_zone
    if not zones.threatened(takeoff.position):
        assert threat_warning(flight, 0, takeoff) is None


def test_threat_warning_for_enemy_aircraft_only(
    game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, flight = _plan(game)
    waypoint = flight.flight_plan.waypoints[1]
    zones = game.red.threat_zone
    # In reach of the enemy CAP, with no air defense around.
    monkeypatch.setattr(
        game.red,
        "_threat_zone",
        ThreatZones(game.theater, zones.airbases, Polygon(), Polygon()),
    )
    point = next(iter(game.theater.control_points_for(game.red.player))).position
    original = waypoint.position
    waypoint.position = point
    try:
        assert (
            threat_warning(flight, 1, waypoint)
            == "Waypoint 1 is within reach of enemy aircraft."
        )
    finally:
        waypoint.position = original


def test_routes_answer_the_route(game: Game, published: list[GameUpdateEvents]) -> None:
    package, flight = _plan(game)
    status, body = _request("GET", _url(flight))
    assert status == 200
    assert body["flight_id"] == str(flight.id)
    first = body["waypoints"][1]

    position = flight.flight_plan.waypoints[1].position.point_from_heading(90, 5000)
    latlng = position.latlng()
    status, moved = _request(
        "PUT",
        _url(flight, "/waypoints/1/position"),
        {"lat": latlng.lat, "lng": latlng.lng},
    )
    assert status == 200
    assert moved["waypoints"][1]["position"] != first["position"]
    assert any(flight in events.updated_flights for events in published)

    status, body = _request(
        "PUT", _url(flight, "/waypoints/1/altitude"), {"altitude_ft": 12000}
    )
    assert status == 200
    assert body["waypoints"][1]["altitude_ft"] == 12000

    status, body = _request("PUT", _url(flight, "/waypoints/1/name"), {"name": "Hold"})
    assert status == 200
    assert body["waypoints"][1]["name"] == "Hold"

    status, body = _request("PUT", _url(flight, "/altitude"), {"altitude_ft": 22000})
    assert status == 200
    assert body["bulk_altitude_ft"] == 22000

    count = len(body["waypoints"])
    status, body = _request("POST", _url(flight, "/waypoints/0/nav"))
    assert status == 200
    assert len(body["waypoints"]) == count + 1
    nav = next(w for w in body["waypoints"] if w["type"] == "NAV")
    assert nav["delete_degrades"] is False

    status, body = _request("DELETE", _url(flight, f"/waypoints/{nav['index']}"))
    assert status == 200
    assert len(body["waypoints"]) == count


def test_route_errors(game: Game, published: list[GameUpdateEvents]) -> None:
    _, flight = _plan(game)
    status, body = _request("GET", f"/flights/{uuid4()}/route")
    assert (status, body["detail"]) == (404, "This flight is no longer planned.")

    status, body = _request(
        "PUT", _url(flight, "/waypoints/99/altitude"), {"altitude_ft": 1000}
    )
    assert (status, body["detail"]) == (404, "This waypoint no longer exists.")

    status, body = _request(
        "PUT", _url(flight, "/waypoints/1/altitude"), {"altitude_ft": 99000}
    )
    assert status == 409

    takeoff = flight.flight_plan.waypoints[0].position.latlng()
    status, body = _request(
        "PUT",
        _url(flight, "/waypoints/0/position"),
        {"lat": takeoff.lat, "lng": takeoff.lng},
    )
    assert status == 409
    assert "cannot be moved" in body["detail"]

    status, body = _request("POST", _url(flight, "/recreate"), {"task": "Nothing"})
    assert (status, body["detail"]) == (422, "Unknown task: Nothing.")


def test_delete_and_rtb_routes_ask_for_the_degrade(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    _, flight = _plan(game)
    index = _index(flight, _of_type(flight, FlightWaypointType.JOIN))
    status, body = _request("DELETE", _url(flight, f"/waypoints/{index}"))
    assert status == 409
    assert "custom flight plan" in body["detail"]
    status, body = _request("POST", _url(flight, "/rtb"))
    assert status == 409
    assert not flight.flight_plan.is_custom


def test_predefined_and_recreate_routes(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    _, flight = _plan(game)
    status, options = _request("GET", _url(flight, "/predefined-waypoints"))
    assert status == 200
    name = next(o["name"] for o in options if o["description"].startswith("Enemy unit"))
    count = len(flight.flight_plan.waypoints)
    status, body = _request(
        "POST",
        _url(flight, "/predefined-waypoints"),
        {"name": name, "same_location": False},
    )
    assert status == 200
    assert len(body["waypoints"]) == count + 1

    status, body = _request("POST", _url(flight, "/recreate"), {"task": "Strike"})
    assert status == 200
    assert body["recreate_tasks"][0] == "Strike"
    assert len(body["waypoints"]) == count


def test_map_drag_shares_the_command(
    game: Game, published: list[GameUpdateEvents]
) -> None:
    """The drag on the main map (`/waypoints`) counts the synthetic departure as 0."""
    _, flight = _plan(game)
    before = flight.flight_plan.waypoints[1].position
    latlng = before.point_from_heading(90, 5000).latlng()
    point: Any = {"lat": latlng.lat, "lng": latlng.lng}
    status, _ = _request("POST", f"/waypoints/{flight.id}/2/position", point)
    assert status == 204
    assert flight.flight_plan.waypoints[1].position != before
    assert any(flight in events.updated_flights for events in published)

    status, body = _request("POST", f"/waypoints/{flight.id}/1/position", point)
    assert status == 409
    status, _ = _request("POST", f"/waypoints/{flight.id}/0/position", point)
    assert status == 403

"""The Route tab of a flight in the package editor (WEB-04.4).

Rules in `game/commands/flightroute.py`. Waypoints are addressed by their place in the
flight plan (0 is the departure), the # of the table.
"""

from datetime import datetime
from uuid import UUID

from dcs.mapping import LatLng, Point
from fastapi import APIRouter, Depends

from game import Game
from game.ato import Flight, FlightType
from game.commands import CommandError
from game.commands.flightroute import (
    add_predefined_waypoint,
    add_rtb_waypoint,
    delete_waypoint,
    insert_nav_after,
    move_waypoint,
    predefined_waypoints,
    recreate_route,
    require_waypoint,
    set_en_route_altitude,
    set_waypoint_altitude,
)
from game.gamelock import locked
from game.server import EventStream
from game.server.leaflet import LeafletPoint
from .models import (
    FlightRouteJs,
    NewPredefinedWaypointJs,
    PredefinedWaypointJs,
    RecreateRouteJs,
    WaypointAltitudeJs,
    WaypointNameJs,
)
from ..commanderrors import command_error_responses
from ..dependencies import GameContext, QtCallbacks, QtContext

router: APIRouter = APIRouter(prefix="/flights/{flight_id}/route")


def _require_game(game: Game | None) -> Game:
    if game is None:
        raise CommandError("No campaign is loaded.")
    return game


def _flight(game: Game, flight_id: UUID) -> Flight:
    try:
        return game.db.flights.get(flight_id)
    except KeyError:
        raise CommandError("This flight is no longer planned.", status_code=404)


def _now(game: Game) -> datetime:
    now = GameContext.get_sim().current_time_in_sim_if_game_loaded
    return game.conditions.start_time if now is None else now


def _changed(game: Game, flight: Flight, qt: QtCallbacks | None) -> FlightRouteJs:
    """After a change: the TOT of an ASAP package moves with the route, the waypoints
    it shares may have moved with its primary flight, and every screen shows it."""
    package = flight.package
    if package.auto_asap:
        package.set_tot_asap(_now(game))
    with EventStream.event_context() as events:
        events.update_flights_in_package(package)
    if qt is not None and qt.packages_changed is not None:
        qt.packages_changed()
    return FlightRouteJs.for_flight(game, flight)


@router.get(
    "",
    operation_id="get_flight_route",
    response_model=FlightRouteJs,
    responses=command_error_responses("No campaign is loaded, or no such flight."),
)
@locked
def get_route(
    flight_id: UUID, game: Game | None = Depends(GameContext.get)
) -> FlightRouteJs:
    game = _require_game(game)
    return FlightRouteJs.for_flight(game, _flight(game, flight_id))


@router.put(
    "/waypoints/{index}/position",
    operation_id="move_flight_waypoint",
    response_model=FlightRouteJs,
    responses=command_error_responses("This waypoint cannot be moved."),
)
@locked
def put_position(
    flight_id: UUID,
    index: int,
    position: LeafletPoint,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRouteJs:
    game = _require_game(game)
    flight = _flight(game, flight_id)
    move_waypoint(
        flight,
        require_waypoint(flight, index),
        Point.from_latlng(LatLng(position.lat, position.lng), game.theater.terrain),
    )
    return _changed(game, flight, qt)


@router.put(
    "/waypoints/{index}/altitude",
    operation_id="set_flight_waypoint_altitude",
    response_model=FlightRouteJs,
    responses=command_error_responses("The altitude is out of range."),
)
@locked
def put_altitude(
    flight_id: UUID,
    index: int,
    body: WaypointAltitudeJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRouteJs:
    game = _require_game(game)
    flight = _flight(game, flight_id)
    set_waypoint_altitude(require_waypoint(flight, index), body.altitude_ft)
    return _changed(game, flight, qt)


@router.put(
    "/waypoints/{index}/name",
    operation_id="rename_flight_waypoint",
    response_model=FlightRouteJs,
    responses=command_error_responses("No such waypoint."),
)
@locked
def put_name(
    flight_id: UUID,
    index: int,
    body: WaypointNameJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRouteJs:
    game = _require_game(game)
    flight = _flight(game, flight_id)
    require_waypoint(flight, index).apply_name_edit(body.name)
    return _changed(game, flight, qt)


@router.delete(
    "/waypoints/{index}",
    operation_id="delete_flight_waypoint",
    response_model=FlightRouteJs,
    responses=command_error_responses(
        "The first waypoint stays, and a change that makes the plan custom needs "
        "allow_degrade."
    ),
)
@locked
def delete_route_waypoint(
    flight_id: UUID,
    index: int,
    allow_degrade: bool = False,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRouteJs:
    game = _require_game(game)
    flight = _flight(game, flight_id)
    delete_waypoint(flight, require_waypoint(flight, index), allow_degrade)
    return _changed(game, flight, qt)


@router.post(
    "/waypoints/{index}/nav",
    operation_id="insert_flight_nav_waypoint",
    response_model=FlightRouteJs,
    responses=command_error_responses("A NAV point cannot follow this waypoint."),
)
@locked
def post_nav(
    flight_id: UUID,
    index: int,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRouteJs:
    """Inserts a NAV point after this waypoint, halfway to the next one."""
    game = _require_game(game)
    flight = _flight(game, flight_id)
    insert_nav_after(flight, index)
    return _changed(game, flight, qt)


@router.post(
    "/rtb",
    operation_id="add_flight_rtb_waypoint",
    response_model=FlightRouteJs,
    responses=command_error_responses(
        "A change that makes the plan custom needs allow_degrade."
    ),
)
@locked
def post_rtb(
    flight_id: UUID,
    allow_degrade: bool = False,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRouteJs:
    game = _require_game(game)
    flight = _flight(game, flight_id)
    add_rtb_waypoint(flight, allow_degrade)
    return _changed(game, flight, qt)


@router.get(
    "/predefined-waypoints",
    operation_id="list_predefined_waypoints",
    response_model=list[PredefinedWaypointJs],
    responses=command_error_responses("No campaign is loaded, or no such flight."),
)
@locked
def get_predefined(
    flight_id: UUID, game: Game | None = Depends(GameContext.get)
) -> list[PredefinedWaypointJs]:
    """What "Add waypoint" offers."""
    game = _require_game(game)
    waypoints = predefined_waypoints(game, _flight(game, flight_id).coalition.player)
    objects = [w.obj_name for w in waypoints if w.obj_name]
    return [
        PredefinedWaypointJs(
            name=w.pretty_name,
            description=w.description,
            has_siblings=bool(w.obj_name) and objects.count(w.obj_name) > 1,
        )
        for w in waypoints
    ]


@router.post(
    "/predefined-waypoints",
    operation_id="add_predefined_waypoint",
    response_model=FlightRouteJs,
    responses=command_error_responses("This waypoint is no longer available."),
)
@locked
def post_predefined(
    flight_id: UUID,
    body: NewPredefinedWaypointJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRouteJs:
    game = _require_game(game)
    flight = _flight(game, flight_id)
    add_predefined_waypoint(game, flight, body.name, body.same_location)
    return _changed(game, flight, qt)


@router.put(
    "/altitude",
    operation_id="set_flight_route_altitude",
    response_model=FlightRouteJs,
    responses=command_error_responses("The altitude is out of range."),
)
@locked
def put_route_altitude(
    flight_id: UUID,
    body: WaypointAltitudeJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRouteJs:
    """One altitude for all en-route waypoints."""
    game = _require_game(game)
    flight = _flight(game, flight_id)
    set_en_route_altitude(flight, body.altitude_ft)
    return _changed(game, flight, qt)


@router.post(
    "/recreate",
    operation_id="recreate_flight_route",
    response_model=FlightRouteJs,
    responses=command_error_responses("The route cannot be planned for this task."),
)
@locked
def post_recreate(
    flight_id: UUID,
    body: RecreateRouteJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> FlightRouteJs:
    """Plans the route again, which resets the player's changes to it."""
    game = _require_game(game)
    flight = _flight(game, flight_id)
    try:
        task = FlightType(body.task)
    except ValueError:
        raise CommandError(f"Unknown task: {body.task}.", status_code=422)
    recreate_route(game, flight, task)
    return _changed(game, flight, qt)

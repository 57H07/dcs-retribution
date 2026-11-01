from uuid import UUID

from dcs.mapping import LatLng, Point
from game.commands.flightroute import move_waypoint, require_waypoint
from game.gamelock import locked
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import Response

from game import Game
from game.ato import Flight
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.server import GameContext
from game.server.commanderrors import command_error_responses
from game.server.dependencies import QtCallbacks, QtContext
from game.server.leaflet import LeafletPoint
from game.server.waypoints.models import FlightWaypointJs
from game.utils import meters

router: APIRouter = APIRouter(prefix="/waypoints")


def waypoints_for_flight(flight: Flight) -> list[FlightWaypointJs]:
    departure = FlightWaypointJs.for_waypoint(
        FlightWaypoint(
            "TAKEOFF",
            FlightWaypointType.TAKEOFF,
            flight.departure.position,
            meters(0),
            "RADIO",
        ),
        flight,
        0,
    )
    return [departure] + [
        FlightWaypointJs.for_waypoint(w, flight, i)
        for i, w in enumerate(flight.flight_plan.waypoints, 1)
    ]


@router.get(
    "/{flight_id}",
    operation_id="list_all_waypoints_for_flight",
    response_model=list[FlightWaypointJs],
)
@locked
def all_waypoints_for_flight(
    flight_id: UUID, game: Game = Depends(GameContext.require)
) -> list[FlightWaypointJs]:
    return waypoints_for_flight(game.db.flights.get(flight_id))


@router.post(
    "/{flight_id}/{waypoint_idx}/position",
    operation_id="set_waypoint_position",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("This waypoint cannot be moved."),
)
@locked
def set_position(
    flight_id: UUID,
    waypoint_idx: int,
    position: LeafletPoint,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> None:
    from game.server import EventStream

    flight = game.db.flights.get(flight_id)
    if waypoint_idx == 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    waypoint = require_waypoint(flight, waypoint_idx - 1)
    move_waypoint(
        flight,
        waypoint,
        Point.from_latlng(LatLng(position.lat, position.lng), game.theater.terrain),
    )
    package = flight.package
    if package.auto_asap:
        now = GameContext.get_sim().current_time_in_sim_if_game_loaded
        package.set_tot_asap(game.conditions.start_time if now is None else now)
    with EventStream.event_context() as events:
        events.update_flights_in_package(package)
    if qt is not None and qt.packages_changed is not None:
        qt.packages_changed()

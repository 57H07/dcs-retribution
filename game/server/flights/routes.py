from uuid import UUID

from game.gamelock import locked
from fastapi import APIRouter, Depends, HTTPException, status
from shapely.geometry import LineString, Point as ShapelyPoint

from game import Game
from game.ato.flightplans.uizonedisplay import UiZoneDisplay
from game.server import GameContext
from game.server.flights.models import FlightJs
from game.server.leaflet import LeafletPoly, ShapelyUtil

router: APIRouter = APIRouter(prefix="/flights")


@router.get("/", operation_id="list_flights", response_model=list[FlightJs])
@locked
def list_flights(
    with_waypoints: bool = False, game: Game = Depends(GameContext.require)
) -> list[FlightJs]:
    return FlightJs.all_in_game(game, with_waypoints)


@router.post(
    "/{flight_id}/select",
    operation_id="select_flight",
    status_code=status.HTTP_200_OK,
)
@locked
def select_flight(flight_id: UUID, game: Game = Depends(GameContext.require)) -> None:
    """A flight was clicked on the map: the packages panel follows (WEB-01.2)."""
    # Here: the event stream models import this package.
    from game.server import EventStream

    flight = game.db.flights.get(flight_id)
    if flight is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no flight with ID {flight_id}",
        )
    with EventStream.event_context() as events:
        events.select_flight(flight)


@router.get("/{flight_id}", operation_id="get_flight_by_id", response_model=FlightJs)
@locked
def get_flight(
    flight_id: UUID,
    with_waypoints: bool = False,
    game: Game = Depends(GameContext.require),
) -> FlightJs:
    flight = game.db.flights.get(flight_id)
    return FlightJs.for_flight(flight, with_waypoints)


@router.get(
    "/{flight_id}/commit-boundary",
    operation_id="get_commit_boundary_for_flight",
    response_model=LeafletPoly,
)
@locked
def commit_boundary(
    flight_id: UUID, game: Game = Depends(GameContext.require)
) -> LeafletPoly:
    flight = game.db.flights.get(flight_id)
    if not isinstance(flight.flight_plan, UiZoneDisplay):
        return []
    zone = flight.flight_plan.ui_zone()
    if len(zone.points) == 1:
        center = ShapelyPoint(zone.points[0].x, zone.points[0].y)
    else:
        center = LineString([ShapelyPoint(p.x, p.y) for p in zone.points])
    bubble = center.buffer(zone.radius.meters)
    return ShapelyUtil.poly_to_leaflet(bubble, game.theater)

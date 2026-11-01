from uuid import UUID

from dcs import Point
from dcs.mapping import LatLng
from game.gamelock import locked
from fastapi import APIRouter, Body, Depends, HTTPException, status
from starlette.responses import Response

from game import Game
from game.commands import (
    AircraftOrder,
    cancel_aircraft_orders,
    create_squadron,
    order_aircraft,
    order_all_repairs,
    order_repair,
    squadron_choices,
)
from game.squadrons import Squadron
from game.theater import ControlPoint
from game.theater.player import Player
from .aircraftorders import AircraftOrdersJs, NewSquadronJs, SquadronChoiceJs
from .base import BaseJs
from .models import ControlPointJs
from .summary import ControlPointSummaryJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext
from ..leaflet import LeafletPoint

router: APIRouter = APIRouter(prefix="/control-points")


@router.get(
    "/", operation_id="list_control_points", response_model=list[ControlPointJs]
)
@locked
def list_control_points(
    game: Game = Depends(GameContext.require),
) -> list[ControlPointJs]:
    return ControlPointJs.all_in_game(game)


@router.get(
    "/{cp_id}", operation_id="get_control_point_by_id", response_model=ControlPointJs
)
@locked
def get_control_point(
    cp_id: UUID, game: Game = Depends(GameContext.require)
) -> ControlPointJs:
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )
    return ControlPointJs.for_control_point(cp)


@router.get(
    "/{cp_id}/summary",
    operation_id="get_control_point_summary",
    response_model=ControlPointSummaryJs,
)
@locked
def get_control_point_summary(
    cp_id: UUID, game: Game = Depends(GameContext.require)
) -> ControlPointSummaryJs:
    """What the map inspector shows about a base (WEB-01.3)."""
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )
    return ControlPointSummaryJs.for_control_point(game, cp)


def _find(game: Game, cp_id: UUID) -> ControlPoint:
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )
    return cp


@router.get("/{cp_id}/base", operation_id="get_base", response_model=BaseJs)
@locked
def get_base(cp_id: UUID, game: Game = Depends(GameContext.require)) -> BaseJs:
    """What the base screen shows (WEB-02.1): status, air defense, repairs."""
    return BaseJs.for_control_point(game, _find(game, cp_id))


@router.post(
    "/{cp_id}/repairs/{repair_id}",
    operation_id="order_repair",
    response_model=BaseJs,
    responses=command_error_responses(
        "not a player base, nothing to repair, or not enough budget"
    ),
)
@locked
def order_base_repair(
    cp_id: UUID, repair_id: str, game: Game = Depends(GameContext.require)
) -> BaseJs:
    """Pays for one repair listed by `GET /control-points/{cp_id}/base`."""
    cp = _find(game, cp_id)
    from .. import EventStream

    with EventStream.event_context() as events:
        order_repair(game, cp, repair_id, events)
    return BaseJs.for_control_point(game, cp)


@router.post(
    "/{cp_id}/repair-all",
    operation_id="order_all_repairs",
    response_model=BaseJs,
    responses=command_error_responses(
        "not a player base, nothing to repair, or not enough budget for all"
    ),
)
@locked
def order_all_base_repairs(
    cp_id: UUID, game: Game = Depends(GameContext.require)
) -> BaseJs:
    """Pays for every orderable repair of the base, or for none."""
    cp = _find(game, cp_id)
    from .. import EventStream

    with EventStream.event_context() as events:
        order_all_repairs(game, cp, events)
    return BaseJs.for_control_point(game, cp)


def _stationed_squadron(cp: ControlPoint, squadron_id: UUID) -> Squadron:
    for squadron in cp.squadrons:
        if squadron.id == squadron_id:
            return squadron
    raise HTTPException(
        status.HTTP_404_NOT_FOUND,
        detail=f"{cp.name} has no squadron with ID {squadron_id}",
    )


@router.post(
    "/{cp_id}/purchases/aircraft",
    operation_id="order_aircraft",
    response_model=BaseJs,
    responses=command_error_responses(
        "not a player base, empty order, or refused by the budget, parking or "
        "squadron limits (then nothing is ordered)"
    ),
)
@locked
def order_base_aircraft(
    cp_id: UUID, body: AircraftOrdersJs, game: Game = Depends(GameContext.require)
) -> BaseJs:
    """Applies a whole order: negative quantities cancel orders, then sell aircraft."""
    cp = _find(game, cp_id)
    orders = [
        AircraftOrder(_stationed_squadron(cp, line.squadron_id), line.quantity)
        for line in body.orders
    ]
    from .. import EventStream

    with EventStream.event_context() as events:
        order_aircraft(cp, orders, events)
    return BaseJs.for_control_point(game, cp)


@router.delete(
    "/{cp_id}/purchases/aircraft/{squadron_id}",
    operation_id="cancel_aircraft_order",
    response_model=BaseJs,
    responses=command_error_responses(
        "not a player base, nothing pending, or a pending sale that cannot be undone"
    ),
)
@locked
def cancel_base_aircraft_order(
    cp_id: UUID, squadron_id: UUID, game: Game = Depends(GameContext.require)
) -> BaseJs:
    """Cancels the pending deliveries of a squadron."""
    cp = _find(game, cp_id)
    squadron = _stationed_squadron(cp, squadron_id)
    from .. import EventStream

    with EventStream.event_context() as events:
        cancel_aircraft_orders(cp, squadron, events)
    return BaseJs.for_control_point(game, cp)


@router.get(
    "/{cp_id}/squadron-choices",
    operation_id="get_squadron_choices",
    response_model=list[SquadronChoiceJs],
)
@locked
def get_squadron_choices(
    cp_id: UUID, game: Game = Depends(GameContext.require)
) -> list[SquadronChoiceJs]:
    """What the "create a squadron" dialog offers at this base."""
    return [
        SquadronChoiceJs.from_choice(choice)
        for choice in squadron_choices(_find(game, cp_id))
    ]


@router.post(
    "/{cp_id}/squadrons",
    operation_id="create_squadron",
    response_model=BaseJs,
    responses=command_error_responses(
        "not a player base, or an aircraft, task or preset this base does not offer"
    ),
)
@locked
def create_base_squadron(
    cp_id: UUID, body: NewSquadronJs, game: Game = Depends(GameContext.require)
) -> BaseJs:
    """Adds an empty squadron to the base."""
    cp = _find(game, cp_id)
    from .. import EventStream

    with EventStream.event_context() as events:
        create_squadron(game, cp, body.aircraft, body.primary_task, body.preset, events)
    return BaseJs.for_control_point(game, cp)


@router.get(
    "/{cp_id}/destination-in-range",
    operation_id="control_point_destination_in_range",
    response_model=bool,
)
@locked
def destination_in_range(
    cp_id: UUID, lat: float, lng: float, game: Game = Depends(GameContext.require)
) -> bool:
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )

    point = Point.from_latlng(LatLng(lat, lng), game.theater.terrain)
    return cp.destination_in_range(point)


@router.put(
    "/{cp_id}/destination",
    operation_id="set_control_point_destination",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def set_destination(
    cp_id: UUID,
    destination: LeafletPoint = Body(..., title="destination"),
    game: Game = Depends(GameContext.require),
) -> None:
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )
    if not cp.moveable:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"{cp} is not mobile")
    if not cp.captured.is_blue:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail=f"{cp} is not owned by the player"
        )

    point = Point.from_latlng(
        LatLng(destination.lat, destination.lng), game.theater.terrain
    )
    if not cp.destination_in_range(point):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move {cp} more than "
            f"{cp.max_move_distance.nautical_miles}nm.",
        )
    if (
        cp.is_fleet
        and game.theater.landmap
        and game.theater.landmap.land_inbetween(cp.position, point)
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move {cp} over land.",
        )
    cp.target_position = point
    from .. import EventStream

    with EventStream.event_context() as events:
        events.update_control_point(cp)


@router.put(
    "/{cp_id}/cancel-travel",
    operation_id="clear_control_point_destination",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def cancel_travel(cp_id: UUID, game: Game = Depends(GameContext.require)) -> None:
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )
    if not cp.moveable:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"{cp} is not mobile")
    if not cp.captured.is_blue:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail=f"{cp} is not owned by the player"
        )

    cp.target_position = None
    from .. import EventStream

    with EventStream.event_context() as events:
        events.update_control_point(cp)

from uuid import UUID

from dcs import Point
from dcs.mapping import LatLng
from game.gamelock import locked
from fastapi import APIRouter, Body, Depends, HTTPException, status
from starlette.responses import Response

from game import Game
from game.commands import (
    TgoPurchase,
    buy_ground_object_group,
    disband_ground_object,
    quote_purchase,
    repair_ground_unit,
    resolve_purchase,
    rotate_ground_object,
    set_hidden_on_mfd,
)
from game.utils import Heading
from .models import TgoJs
from .sheet import (
    PurchaseQuoteJs,
    TgoHeadingChangeJs,
    TgoHiddenChangeJs,
    TgoPurchaseJs,
    TgoPurchaseOptionsJs,
    TgoSheetJs,
)
from .summary import TgoSummaryJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext
from ..leaflet import LeafletPoint
from game.theater import TheaterGroundObject
from game.theater.theatergroundobject import ShipGroundObject

router: APIRouter = APIRouter(prefix="/tgos")


def _find(game: Game, tgo_id: UUID) -> TheaterGroundObject:
    try:
        return game.db.tgos.get(tgo_id)
    except KeyError:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Game has no TGO with ID {tgo_id}"
        )


@router.get("/", operation_id="list_tgos", response_model=list[TgoJs])
@locked
def list_tgos(game: Game = Depends(GameContext.require)) -> list[TgoJs]:
    return TgoJs.all_in_game(game)


@router.get("/{tgo_id}", operation_id="get_tgo_by_id", response_model=TgoJs)
@locked
def get_tgo(tgo_id: UUID, game: Game = Depends(GameContext.require)) -> TgoJs:
    return TgoJs.for_tgo(game.db.tgos.get(tgo_id))


@router.get(
    "/{tgo_id}/summary",
    operation_id="get_tgo_summary",
    response_model=TgoSummaryJs,
)
@locked
def get_tgo_summary(
    tgo_id: UUID, game: Game = Depends(GameContext.require)
) -> TgoSummaryJs:
    """What the map inspector shows about a ground object (WEB-01.3)."""
    return TgoSummaryJs.for_tgo(game, _find(game, tgo_id))


@router.get(
    "/{tgo_id}/sheet",
    operation_id="get_tgo_sheet",
    response_model=TgoSheetJs,
)
@locked
def get_tgo_sheet(
    tgo_id: UUID, game: Game = Depends(GameContext.require)
) -> TgoSheetJs:
    """The ground object screen: units with their status and what can be done."""
    return TgoSheetJs.for_tgo(game, _find(game, tgo_id))


@router.post(
    "/{tgo_id}/units/{unit_id}/repair",
    operation_id="repair_tgo_unit",
    response_model=TgoSheetJs,
    responses=command_error_responses(
        "nothing to repair on this unit, or not enough budget"
    ),
)
@locked
def repair_tgo_unit(
    tgo_id: UUID, unit_id: int, game: Game = Depends(GameContext.require)
) -> TgoSheetJs:
    tgo = _find(game, tgo_id)
    from .. import EventStream

    with EventStream.event_context() as events:
        repair_ground_unit(game, tgo, unit_id, events)
    return TgoSheetJs.for_tgo(game, tgo)


@router.put(
    "/{tgo_id}/heading",
    operation_id="set_tgo_heading",
    response_model=TgoSheetJs,
    responses=command_error_responses("not a player site, or a building site"),
)
@locked
def set_tgo_heading(
    tgo_id: UUID,
    body: TgoHeadingChangeJs,
    game: Game = Depends(GameContext.require),
) -> TgoSheetJs:
    tgo = _find(game, tgo_id)
    from .. import EventStream

    with EventStream.event_context() as events:
        rotate_ground_object(tgo, Heading.from_degrees(body.degrees), events)
    return TgoSheetJs.for_tgo(game, tgo)


@router.put(
    "/{tgo_id}/hidden-on-mfd",
    operation_id="set_tgo_hidden_on_mfd",
    response_model=TgoSheetJs,
    responses=command_error_responses("not an enemy air defense site"),
)
@locked
def set_tgo_hidden_on_mfd(
    tgo_id: UUID,
    body: TgoHiddenChangeJs,
    game: Game = Depends(GameContext.require),
) -> TgoSheetJs:
    tgo = _find(game, tgo_id)
    from .. import EventStream

    with EventStream.event_context() as events:
        set_hidden_on_mfd(tgo, body.hidden, events)
    return TgoSheetJs.for_tgo(game, tgo)


@router.delete(
    "/{tgo_id}/group",
    operation_id="disband_tgo_group",
    response_model=TgoSheetJs,
    responses=command_error_responses("the site cannot be sold, or is empty"),
)
@locked
def disband_tgo_group(
    tgo_id: UUID, game: Game = Depends(GameContext.require)
) -> TgoSheetJs:
    """Sells the whole group of a site."""
    tgo = _find(game, tgo_id)
    from .. import EventStream

    with EventStream.event_context() as events:
        disband_ground_object(game, tgo, events)
    return TgoSheetJs.for_tgo(game, tgo)


@router.get(
    "/{tgo_id}/purchase-options",
    operation_id="get_tgo_purchase_options",
    response_model=TgoPurchaseOptionsJs,
)
@locked
def get_tgo_purchase_options(
    tgo_id: UUID, game: Game = Depends(GameContext.require)
) -> TgoPurchaseOptionsJs:
    """The force groups and layouts this site can be replaced with."""
    return TgoPurchaseOptionsJs.for_tgo(_find(game, tgo_id))


def _purchase(tgo: TheaterGroundObject, body: TgoPurchaseJs) -> TgoPurchase:
    return resolve_purchase(
        tgo,
        body.force_group,
        body.layout,
        [choice.to_choice() for choice in body.choices],
    )


@router.post(
    "/{tgo_id}/purchase/quote",
    operation_id="quote_tgo_purchase",
    response_model=PurchaseQuoteJs,
    responses=command_error_responses("the layout does not take this purchase"),
)
@locked
def quote_tgo_purchase(
    tgo_id: UUID, body: TgoPurchaseJs, game: Game = Depends(GameContext.require)
) -> PurchaseQuoteJs:
    """What a purchase would cost: changes nothing."""
    tgo = _find(game, tgo_id)
    return PurchaseQuoteJs.for_quote(quote_purchase(game, tgo, _purchase(tgo, body)))


@router.post(
    "/{tgo_id}/purchase",
    operation_id="buy_tgo_group",
    response_model=TgoSheetJs,
    responses=command_error_responses(
        "the site cannot be bought, the layout does not take this purchase, or not "
        "enough budget (then nothing changes)"
    ),
)
@locked
def buy_tgo_group(
    tgo_id: UUID, body: TgoPurchaseJs, game: Game = Depends(GameContext.require)
) -> TgoSheetJs:
    """Replaces the group of a site."""
    tgo = _find(game, tgo_id)
    purchase = _purchase(tgo, body)
    from .. import EventStream

    with EventStream.event_context() as events:
        buy_ground_object_group(game, tgo, purchase, events)
    return TgoSheetJs.for_tgo(game, tgo)


@router.get(
    "/{tgo_id}/destination-in-range",
    operation_id="tgo_destination_in_range",
    response_model=bool,
)
@locked
def tgo_destination_in_range(
    tgo_id: UUID, lat: float, lng: float, game: Game = Depends(GameContext.require)
) -> bool:
    tgo = game.db.tgos.get(tgo_id)
    if not isinstance(tgo, ShipGroundObject):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"{tgo} is not a movable ship"
        )
    if not tgo.control_point.captured.is_blue:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail=f"{tgo} is not owned by the player"
        )
    point = Point.from_latlng(LatLng(lat, lng), game.theater.terrain)
    return tgo.destination_in_range(point)


@router.put(
    "/{tgo_id}/destination",
    operation_id="set_tgo_destination",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def set_tgo_destination(
    tgo_id: UUID,
    destination: LeafletPoint = Body(..., title="destination"),
    game: Game = Depends(GameContext.require),
) -> None:
    tgo = game.db.tgos.get(tgo_id)
    if not isinstance(tgo, ShipGroundObject):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"{tgo} is not a movable ship"
        )
    if not tgo.control_point.captured.is_blue:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail=f"{tgo} is not owned by the player"
        )
    point = Point.from_latlng(
        LatLng(destination.lat, destination.lng), game.theater.terrain
    )
    if not tgo.destination_in_range(point):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move {tgo} more than "
            f"{tgo.max_move_distance.nautical_miles}nm.",
        )
    # Only enforce the sea/land constraint when the theater has a landmap;
    # without one is_in_sea() returns False for every point, which would reject
    # all moves (carriers face the same gap and likewise skip the check).
    if game.theater.landmap and (
        not game.theater.is_in_sea(point)
        or game.theater.landmap.land_inbetween(tgo.position, point)
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move {tgo} over land or out of the sea.",
        )
    tgo.target_position = point
    from .. import EventStream

    with EventStream.event_context() as events:
        events.update_tgo(tgo)


@router.put(
    "/{tgo_id}/cancel-travel",
    operation_id="clear_tgo_destination",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def clear_tgo_destination(
    tgo_id: UUID, game: Game = Depends(GameContext.require)
) -> None:
    tgo = game.db.tgos.get(tgo_id)
    if not isinstance(tgo, ShipGroundObject):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"{tgo} is not a movable ship"
        )
    if not tgo.control_point.captured.is_blue:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail=f"{tgo} is not owned by the player"
        )
    tgo.target_position = None
    from .. import EventStream

    with EventStream.event_context() as events:
        events.update_tgo(tgo)

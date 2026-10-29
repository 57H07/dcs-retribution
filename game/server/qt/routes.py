from typing import Callable, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from game import Game
from game.commands import CommandError
from game.gamelock import locked
from game.theater.player import Player
from .models import QtDialog, QtLink
from ..commanderrors import command_error_responses
from ..dependencies import GameContext, QtCallbacks, QtContext

T = TypeVar("T")

router: APIRouter = APIRouter(prefix="/qt")


@router.post(
    "/create-package/front-line/{front_line_id}",
    operation_id="open_new_front_line_package_dialog",
    status_code=status.HTTP_200_OK,
)
@locked
def new_front_line_package(
    front_line_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    qt.create_new_package(game.db.front_lines.get(front_line_id))


@router.post(
    "/create-package/tgo/{tgo_id}",
    operation_id="open_new_tgo_package_dialog",
    status_code=status.HTTP_200_OK,
)
@locked
def new_tgo_package(
    tgo_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    qt.create_new_package(game.db.tgos.get(tgo_id))


@router.post(
    "/info/tgo/{tgo_id}",
    operation_id="open_tgo_info_dialog",
    status_code=status.HTTP_200_OK,
)
@locked
def show_tgo_info(
    tgo_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    qt.show_tgo_info(game.db.tgos.get(tgo_id))


@router.post(
    "/create-package/control-point/{cp_id}",
    operation_id="open_new_control_point_package_dialog",
    status_code=status.HTTP_200_OK,
)
@locked
def new_cp_package(
    cp_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )
    qt.create_new_package(cp)


@router.post(
    "/create-package/downed-pilot/{pilot_id}",
    operation_id="open_new_downed_pilot_package_dialog",
    status_code=status.HTTP_200_OK,
)
@locked
def new_downed_pilot_package(
    pilot_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    try:
        downed = game.db.downed_pilots.get(pilot_id)
    except KeyError:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no downed pilot with ID {pilot_id}",
        )
    if not downed.is_friendly(Player.BLUE):
        # Only the owning coalition can rescue its pilots, so an enemy downed pilot
        # offers no mission type and would open an empty package dialog.
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Downed pilot {pilot_id} is not a friendly pilot",
        )
    qt.create_new_package(downed)


@router.post(
    "/select-flight/{flight_id}",
    operation_id="select_flight",
    status_code=status.HTTP_200_OK,
)
@locked
def select_flight(
    flight_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    flight = game.db.flights.get(flight_id)
    if flight is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no flight with ID {flight_id}",
        )
    qt.select_flight(flight)


@router.post(
    "/info/control-point/{cp_id}",
    operation_id="open_control_point_info_dialog",
    status_code=status.HTTP_200_OK,
)
@locked
def show_control_point_info(
    cp_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )
    qt.show_control_point_info(cp)


def _require_callback(callback: Callable[[T], None] | None) -> Callable[[T], None]:
    if callback is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Qt window is not available.",
        )
    return callback


@router.post(
    "/dialogs/{dialog}",
    operation_id="open_qt_dialog",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("when the dialog needs a campaign and none is"),
)
@locked
def open_qt_dialog(
    dialog: QtDialog,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    """Opens a Qt screen that the web UI does not have yet (WEB-00.3).

    Only queues the dialog onto the Qt main thread: never waits for it.
    """
    open_dialog = _require_callback(qt.open_dialog)
    if dialog.needs_game and game is None:
        raise CommandError("No campaign is loaded.")
    open_dialog(dialog)


@router.post(
    "/links/{link}",
    operation_id="open_external_link",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def open_external_link(link: QtLink, qt: QtCallbacks = Depends(QtContext.get)) -> None:
    """Opens a Help page in the system browser (the web view cannot)."""
    _require_callback(qt.open_link)(link)


@router.post(
    "/edit-package/flight/{flight_id}",
    operation_id="open_edit_package_dialog",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def edit_package_of_flight(
    flight_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    """Opens the Qt package editor of the package flying this flight.

    Packages have no ID in the API yet (WEB-03 adds them): a flight stands for its
    package.
    """
    edit_package = _require_callback(qt.edit_package)
    try:
        flight = game.db.flights.get(flight_id)
    except KeyError:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no flight with ID {flight_id}",
        )
    edit_package(flight.package)

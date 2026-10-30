from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from game import Game
from game.commands import CommandError
from game.commands.packages import delete_package
from game.gamelock import locked
from game.server import EventStream
from game.theater import MissionTarget
from game.theater.player import Player
from .models import NewPackageJs, PackageJs, PackageTargetKind
from ..commanderrors import command_error_responses
from ..dependencies import GameContext, QtCallbacks, QtContext

router: APIRouter = APIRouter(prefix="/packages")


def _require_game(game: Game | None) -> Game:
    if game is None:
        raise CommandError("No campaign is loaded.")
    return game


@router.get("/", operation_id="list_packages", response_model=list[PackageJs])
@locked
def list_packages(game: Game | None = Depends(GameContext.get)) -> list[PackageJs]:
    """The packages of both air tasking orders (friendly and enemy ATO)."""
    if game is None:
        return []
    return PackageJs.all_in_game(game)


def _target(game: Game, new: NewPackageJs) -> MissionTarget:
    try:
        if new.target_kind is PackageTargetKind.CONTROL_POINT:
            cp = game.theater.find_control_point_by_id(new.target_id)
            if cp is None:
                raise KeyError(new.target_id)
            return cp
        if new.target_kind is PackageTargetKind.TGO:
            return game.db.tgos.get(new.target_id)
        if new.target_kind is PackageTargetKind.FRONT_LINE:
            return game.db.front_lines.get(new.target_id)
        pilot = game.db.downed_pilots.get(new.target_id)
    except KeyError:
        raise CommandError("This target no longer exists.", status_code=404)
    if not pilot.is_friendly(Player.BLUE):
        # Only the owning coalition rescues its pilots (see /qt/create-package).
        raise CommandError("Only friendly pilots can be rescued.")
    return pilot


@router.post(
    "/",
    operation_id="create_package",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses(
        "No campaign is loaded, the target is gone or cannot be planned against."
    ),
)
@locked
def create_package(
    new: NewPackageJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> None:
    """Opens the package editor on a target (the Qt dialog until WEB-04.1).

    Only queues the dialog onto the Qt main thread: the package joins the ATO when
    the player saves it, and its flights reach the event stream then.
    """
    target = _target(_require_game(game), new)
    if qt is None:
        raise CommandError("The package editor is not available.", status_code=503)
    qt.create_new_package(target)


@router.delete(
    "/{package_id}",
    operation_id="delete_package",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("No campaign is loaded."),
)
@locked
def remove_package(
    package_id: UUID,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> None:
    """Cancels a package of either ATO, or aborts its flights already under way.

    Deleted and aborted flights are published on the event stream. 404 when no
    package has this id.
    """
    game = _require_game(game)
    now = GameContext.get_sim().current_time_in_sim_if_game_loaded
    with EventStream.event_context() as events:
        delete_package(game, package_id, events, now)
    if qt is not None and qt.packages_changed is not None:
        qt.packages_changed()

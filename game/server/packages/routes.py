from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from game import Game
from game.ato import Flight, FlightType, Package
from game.commander.missionproposals import ProposedFlight
from game.commands import CommandError
from game.commands.packageflights import add_flight, auto_create, remove_flight
from game.commands.packages import (
    coalition_of,
    create_package,
    delete_package,
    rename_package,
    require_package,
    set_package_tot,
    set_package_tot_earliest,
)
from game.dcs.aircrafttype import AircraftType
from game.gamelock import locked
from game.server import EventStream
from game.squadrons import Squadron
from game.theater import MissionTarget
from game.theater.player import Player
from .models import (
    AutoCreateOptionsJs,
    AutoCreateRequestJs,
    FlightOptionsJs,
    NewFlightJs,
    NewPackageJs,
    PackageDetailJs,
    PackageJs,
    PackageNameJs,
    PackageTargetKind,
    PackageTotJs,
)
from ..commanderrors import command_error_responses
from ..dependencies import GameContext, QtCallbacks, QtContext

router: APIRouter = APIRouter(prefix="/packages")


def _require_game(game: Game | None) -> Game:
    if game is None:
        raise CommandError("No campaign is loaded.")
    return game


def _now(game: Game) -> datetime:
    now = GameContext.get_sim().current_time_in_sim_if_game_loaded
    return game.conditions.start_time if now is None else now


def _refresh_qt(qt: QtCallbacks | None) -> None:
    """Keeps the Qt ATO panel, when shown, in step with a command."""
    if qt is not None and qt.packages_changed is not None:
        qt.packages_changed()


def _task(value: str) -> FlightType:
    try:
        return FlightType(value)
    except ValueError:
        raise CommandError(f"Unknown task: {value}.", status_code=422)


def _squadron(game: Game, package: Package, squadron_id: UUID) -> Squadron:
    air_wing = coalition_of(game, package).air_wing
    for squadron in air_wing.iter_squadrons():
        if squadron.id == squadron_id:
            return squadron
    raise CommandError("This squadron no longer exists.", status_code=404)


def _flight(package: Package, flight_id: UUID) -> Flight:
    for flight in package.flights:
        if flight.id == flight_id:
            return flight
    raise CommandError("This flight is no longer planned.", status_code=404)


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
    status_code=status.HTTP_201_CREATED,
    response_model=PackageDetailJs,
    responses=command_error_responses(
        "No campaign is loaded, the target is gone or cannot be planned against."
    ),
)
@locked
def new_package(
    new: NewPackageJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> PackageDetailJs:
    """Plans an empty package against a target, for the package editor (WEB-04.1)."""
    game = _require_game(game)
    package = create_package(game, _target(game, new), _now(game))
    _refresh_qt(qt)
    return PackageDetailJs.for_package(game, package)


@router.get(
    "/{package_id}",
    operation_id="get_package",
    response_model=PackageDetailJs,
    responses=command_error_responses("No campaign is loaded, or no such package."),
)
@locked
def get_package(
    package_id: UUID, game: Game | None = Depends(GameContext.get)
) -> PackageDetailJs:
    game = _require_game(game)
    return PackageDetailJs.for_package(game, require_package(game, package_id))


@router.put(
    "/{package_id}/name",
    operation_id="rename_package",
    response_model=PackageDetailJs,
    responses=command_error_responses("No campaign is loaded, or no such package."),
)
@locked
def put_package_name(
    package_id: UUID,
    body: PackageNameJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> PackageDetailJs:
    game = _require_game(game)
    package = require_package(game, package_id)
    rename_package(package, body.name)
    _refresh_qt(qt)
    return PackageDetailJs.for_package(game, package)


@router.put(
    "/{package_id}/tot",
    operation_id="set_package_tot",
    response_model=PackageDetailJs,
    responses=command_error_responses("Flights of the package have started."),
)
@locked
def put_package_tot(
    package_id: UUID,
    body: PackageTotJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> PackageDetailJs:
    """Sets the time over target, which ends the ASAP mode of the package."""
    game = _require_game(game)
    package = require_package(game, package_id)
    set_package_tot(package, body.tot, _now(game))
    with EventStream.event_context() as events:
        events.update_flights_in_package(package)
    _refresh_qt(qt)
    return PackageDetailJs.for_package(game, package)


@router.post(
    "/{package_id}/tot/earliest",
    operation_id="set_package_tot_earliest",
    response_model=PackageDetailJs,
    responses=command_error_responses("Flights of the package have started."),
)
@locked
def post_package_tot_earliest(
    package_id: UUID,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> PackageDetailJs:
    """Earliest TOT: the package flies ASAP, now and when its flights change."""
    game = _require_game(game)
    package = require_package(game, package_id)
    set_package_tot_earliest(package, _now(game))
    with EventStream.event_context() as events:
        events.update_flights_in_package(package)
    _refresh_qt(qt)
    return PackageDetailJs.for_package(game, package)


@router.get(
    "/{package_id}/flight-options",
    operation_id="get_flight_options",
    response_model=FlightOptionsJs,
    responses=command_error_responses("No campaign is loaded, or no such package."),
)
@locked
def get_flight_options(
    package_id: UUID, game: Game | None = Depends(GameContext.get)
) -> FlightOptionsJs:
    """What the Add flight form offers for this package."""
    game = _require_game(game)
    return FlightOptionsJs.for_package(game, require_package(game, package_id))


@router.post(
    "/{package_id}/flights",
    operation_id="add_package_flight",
    status_code=status.HTTP_201_CREATED,
    response_model=PackageDetailJs,
    responses=command_error_responses("The flight cannot be created or planned."),
)
@locked
def post_package_flight(
    package_id: UUID,
    body: NewFlightJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> PackageDetailJs:
    game = _require_game(game)
    package = require_package(game, package_id)
    flight = add_flight(
        game,
        package,
        _task(body.task),
        _squadron(game, package, body.squadron_id),
        body.size,
        _now(game),
        body.start_type,
    )
    with EventStream.event_context() as events:
        events.new_flight(flight)
        # The TOT of an ASAP package moves with its slowest flight.
        for other in package.flights:
            if other is not flight:
                events.update_flight(other)
    _refresh_qt(qt)
    return PackageDetailJs.for_package(game, package)


@router.delete(
    "/{package_id}/flights/{flight_id}",
    operation_id="remove_package_flight",
    response_model=PackageDetailJs,
    responses=command_error_responses("Only escort flights would remain."),
)
@locked
def delete_package_flight(
    package_id: UUID,
    flight_id: UUID,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> PackageDetailJs:
    """Removes a flight of the package, or aborts it if it is under way."""
    game = _require_game(game)
    package = require_package(game, package_id)
    with EventStream.event_context() as events:
        remove_flight(game, package, _flight(package, flight_id), events, _now(game))
        events.update_flights_in_package(package)
    _refresh_qt(qt)
    return PackageDetailJs.for_package(game, package)


@router.get(
    "/{package_id}/auto-create",
    operation_id="get_auto_create_options",
    response_model=AutoCreateOptionsJs,
    responses=command_error_responses("No campaign is loaded, or no such package."),
)
@locked
def get_auto_create_options(
    package_id: UUID, game: Game | None = Depends(GameContext.get)
) -> AutoCreateOptionsJs:
    """What the Auto-create form offers for this package."""
    game = _require_game(game)
    return AutoCreateOptionsJs.for_package(game, require_package(game, package_id))


@router.post(
    "/{package_id}/auto-create",
    operation_id="auto_create_package",
    response_model=PackageDetailJs,
    responses=command_error_responses(
        "The package has flights, or there are not enough aircraft or pilots."
    ),
)
@locked
def post_auto_create(
    package_id: UUID,
    body: AutoCreateRequestJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> PackageDetailJs:
    """Fills an empty package through the auto-planner; it keeps its id."""
    game = _require_game(game)
    package = require_package(game, package_id)
    try:
        flights = [
            ProposedFlight(
                _task(flight.task),
                flight.count,
                preferred_type=(
                    None
                    if flight.aircraft is None
                    else AircraftType.named(flight.aircraft)
                ),
            )
            for flight in body.flights
        ]
    except KeyError:
        raise CommandError("Unknown aircraft type.", status_code=422)
    planned = auto_create(game, package, flights, _now(game))
    with EventStream.event_context() as events:
        for flight in planned.flights:
            events.new_flight(flight)
    _refresh_qt(qt)
    return PackageDetailJs.for_package(game, planned)


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
    _refresh_qt(qt)

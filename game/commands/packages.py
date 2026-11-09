"""Packages of the air tasking orders (WEB-01.2), shared by the web UI and Qt."""

from __future__ import annotations

from datetime import datetime, time
from typing import Iterator, TYPE_CHECKING
from uuid import UUID

from game.ato.package import Package
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight
    from game.coalition import Coalition
    from game.sim import GameUpdateEvents
    from game.theater import MissionTarget
    from game.transfers import TransferOrder


def _packages(game: Game) -> Iterator[tuple[Coalition, Package]]:
    for coalition in game.coalitions:
        for package in coalition.ato.packages:
            yield coalition, package


def find_package(game: Game, package_id: UUID) -> Package | None:
    """The package of either coalition with this id, or None."""
    for _, package in _packages(game):
        if package.id == package_id:
            return package
    return None


def require_package(game: Game, package_id: UUID) -> Package:
    """`find_package`, or a 404 CommandError."""
    package = find_package(game, package_id)
    if package is None:
        raise CommandError("This package is no longer planned.", status_code=404)
    return package


def coalition_of(game: Game, package: Package) -> Coalition:
    """The coalition whose ATO holds this package, or a 404 CommandError."""
    for coalition, candidate in _packages(game):
        if candidate is package:
            return coalition
    raise CommandError("This package is no longer planned.", status_code=404)


def _player_airlift(coalition: Coalition, flight: Flight) -> TransferOrder | None:
    return coalition.transfers.player_airlift_for(flight)


def cancel_or_abort_flight(
    coalition: Coalition,
    package: Package,
    flight: Flight,
    events: GameUpdateEvents,
) -> None:
    """The flight leaves the package, or aborts (returns to base) if under way.

    A cancelled player Transport flight returns its cargo to the origin.
    """
    if not flight.state.cancelable:
        flight.abort()
        events.update_flight(flight)
        return
    transfer = _player_airlift(coalition, flight)
    package.remove_flight(flight)
    events.delete_flight(flight)
    if transfer is not None:
        coalition.transfers.cancel_transfer(transfer)


def cancel_or_abort_package(
    game: Game,
    package: Package,
    events: GameUpdateEvents,
    now: datetime | None = None,
) -> bool:
    """Cancel the package, or abort the flights already under way.

    A package whose flights are all still cancelable leaves the ATO. Otherwise its
    cancelable flights leave the package and the others abort (return to base).
    A cancelled player Transport flight returns its cargo to the origin. `now` is
    the simulation time, used to keep an ASAP package's TOT current.

    Returns True when the package left the ATO.
    """
    removed = _cancel_or_abort(game, package, events, now)
    game.compute_unculled_zones(events)
    return removed


def delete_player_packages(
    game: Game, events: GameUpdateEvents, now: datetime | None
) -> int:
    """`cancel_or_abort_package` for every package of the player ATO (#206).

    The enemy ATO is left alone. Returns how many packages left the ATO; those
    with flights under way stay, with only those flights.
    """
    removed = sum(
        _cancel_or_abort(game, package, events, now)
        for package in list(game.blue.ato.packages)
    )
    game.compute_unculled_zones(events)
    return removed


def _cancel_or_abort(
    game: Game, package: Package, events: GameUpdateEvents, now: datetime | None
) -> bool:
    coalition = coalition_of(game, package)
    if all(f.state.cancelable for f in package.flights):
        transfers = [
            transfer
            for flight in package.flights
            if (transfer := _player_airlift(coalition, flight)) is not None
        ]
        events.delete_flights_in_package(package)
        coalition.ato.remove_package(package)
        for transfer in transfers:
            coalition.transfers.cancel_transfer(transfer)
        return True

    for flight in list(package.flights):
        cancel_or_abort_flight(coalition, package, flight, events)
    if package.auto_asap and now is not None and package.flights:
        package.set_tot_asap(now)
    return False


def delete_package(
    game: Game, package_id: UUID, events: GameUpdateEvents, now: datetime | None
) -> bool:
    """`cancel_or_abort_package` by id.

    Raises:
        CommandError: no package of either coalition has this id (404).
    """
    return cancel_or_abort_package(game, require_package(game, package_id), events, now)


def create_package(game: Game, target: MissionTarget, now: datetime) -> Package:
    """A new empty package against this target, in the player ATO (WEB-04.1).

    Qt keeps a new package out of the ATO until its dialog is saved. The web editor
    has no such draft: every change applies at once, as for an existing package, and
    an empty package has no effect when the mission is generated. ASAP by default,
    so its TOT follows the flights added to it.
    """
    package = Package(target, game.db.flights, auto_asap=True)
    package.set_tot_asap(now)
    game.blue.ato.add_package(package)
    return package


def rename_package(package: Package, name: str) -> None:
    package.custom_name = name.strip() or None


def _require_tot_editable(package: Package) -> None:
    if not package.all_flights_waiting_for_start():
        raise CommandError("Flights of this package have started: its TOT is fixed.")


def set_package_tot(package: Package, tot: time, now: datetime) -> None:
    """A TOT typed by the player, on the day of the current one. Ends ASAP mode."""
    _require_tot_editable(package)
    package.auto_asap = False
    # An empty package saved by the Qt dialog with ASAP off has no TOT yet.
    current = package.time_over_target
    package.time_over_target = (now if current == datetime.min else current).replace(
        hour=tot.hour, minute=tot.minute, second=tot.second, microsecond=0
    )


def set_package_tot_earliest(package: Package, now: datetime) -> None:
    """ "Earliest TOT": all flights reach the target as soon as they can, and the TOT
    follows from now on when flights change (the ASAP box of the Qt dialog)."""
    _require_tot_editable(package)
    package.auto_asap = True
    package.set_tot_asap(now)

"""Packages of the air tasking orders (WEB-01.2), shared by the web UI and Qt."""

from __future__ import annotations

from datetime import datetime
from typing import Iterator, TYPE_CHECKING
from uuid import UUID

from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight, Package
    from game.coalition import Coalition
    from game.sim import GameUpdateEvents
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


def _coalition_of(game: Game, package: Package) -> Coalition:
    for coalition, candidate in _packages(game):
        if candidate is package:
            return coalition
    raise CommandError("This package is no longer planned.", status_code=404)


def _player_airlift(coalition: Coalition, flight: Flight) -> TransferOrder | None:
    return coalition.transfers.player_airlift_for(flight)


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
    coalition = _coalition_of(game, package)
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
        game.compute_unculled_zones(events)
        return True

    for flight in list(package.flights):
        if flight.state.cancelable:
            transfer = _player_airlift(coalition, flight)
            package.remove_flight(flight)
            events.delete_flight(flight)
            if transfer is not None:
                coalition.transfers.cancel_transfer(transfer)
        else:
            flight.abort()
            events.update_flight(flight)
    if package.auto_asap and now is not None and package.flights:
        package.set_tot_asap(now)
    game.compute_unculled_zones(events)
    return False


def delete_package(
    game: Game, package_id: UUID, events: GameUpdateEvents, now: datetime | None
) -> bool:
    """`cancel_or_abort_package` by id.

    Raises:
        CommandError: no package of either coalition has this id (404).
    """
    package = find_package(game, package_id)
    if package is None:
        raise CommandError("This package is no longer planned.", status_code=404)
    return cancel_or_abort_package(game, package, events, now)

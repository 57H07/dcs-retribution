"""Take off: the checks before a mission and its generation (WEB-01.1).

Extracted from `qt_ui/widgets/QTopPanel.py` so that the Qt top panel and the web
UI apply the same rules. The confirmations themselves (continue without player
pilots, fix the TOTs or not) stay with the front end: these functions only report
what needs confirming and do what was chosen.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol, TYPE_CHECKING

from game import persistency
from game.ato.flightstate import Uninitialized
from game.ato.traveltime import TotEstimator
from game.profiling import logged_duration
from game.settings.settings import FastForwardStopCondition
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight, Package

MISSION_FILE_NAME = "retribution_nextturn.miz"


class MissionSim(Protocol):
    """The part of the simulation a mission launch needs (`SimController`)."""

    @property
    def current_time_in_sim(self) -> datetime: ...

    def run_to_first_contact(self) -> None: ...

    def generate_miz(self, output: Path) -> None: ...


def flights_missing_pilots(game: Game) -> list[tuple[Package, Flight]]:
    """The player flights that lack one or more pilots: they block a take off."""
    return [
        (package, flight)
        for package in game.blue.ato.packages
        for flight in package.flights
        if flight.missing_pilots > 0
    ]


def packages_starting_in_the_past(game: Game, now: datetime) -> list[Package]:
    """The player packages with a flight due to start before `now`.

    Flight start times derive from the package TOT, so such a flight may not reach
    its target in time. A flight not initialized yet never counts: initialized now,
    it would either wait for a later start or already be under way.
    """
    packages = []
    for package in game.blue.ato.packages:
        for flight in package.flights:
            if isinstance(flight.state, Uninitialized):
                continue
            if (
                flight.state.is_waiting_for_start
                and flight.flight_plan.startup_time() < now
            ):
                packages.append(package)
                break
    return packages


def fix_tots(packages: list[Package], now: datetime) -> None:
    """Move the TOT of each package to its earliest feasible time from `now`."""
    for package in packages:
        package.time_over_target = TotEstimator(package).earliest_tot(now)


def fix_past_tots(game: Game, now: datetime) -> list[Package]:
    """ "Fix TOTs automatically": reschedule the packages starting in the past.

    Returns the packages whose TOT changed.
    """
    packages = packages_starting_in_the_past(game, now)
    fix_tots(packages, now)
    return packages


def max_player_count(game: Game) -> int:
    """Number of client slots in the player ATO ("Max Players")."""
    return sum(
        flight.client_count
        for package in game.blue.ato.packages
        for flight in package.flights
    )


def describe_package(package: Package) -> str:
    return f"{package.primary_task} {package.target.name}"


def describe_flight(package: Package, flight: Flight) -> str:
    return f"{package.primary_task} {package.target}: {flight}"


def generate_mission(game: Game, sim: MissionSim) -> Path:
    """Finish planning and write the mission for DCS ("Take off").

    Fast forwards the simulation to first contact when the settings ask for it,
    then writes the `.miz`. Returns its path. The front end then waits for the
    mission result.

    Raises:
        CommandError: the campaign has not begun, or flights are missing pilots.
    """
    if game.turn == 0:
        raise CommandError("Begin the campaign before taking off.")
    missing = flights_missing_pilots(game)
    if missing:
        flights = "; ".join(describe_flight(p, f) for p, f in missing)
        raise CommandError(
            "Some flights are missing pilots: assign pilots or cancel those "
            f"missions ({flights})."
        )
    if game.settings.fast_forward_stop_condition not in (
        FastForwardStopCondition.DISABLED,
        FastForwardStopCondition.MANUAL,
    ):
        with logged_duration("Simulating to first contact"):
            sim.run_to_first_contact()
    output = persistency.mission_path_for(MISSION_FILE_NAME)
    sim.generate_miz(output)
    return output

"""Mission timeline of the command view (WEB-01.4).

Read model of the friendly packages on the mission time axis: for each package,
the first startup, the TOT and the last landing of its flights, as the flight
plans already compute them. Times are sent as seconds since the mission start so
that the client only places bars, without any date or game rule.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight, Package


class TimelinePackageJs(BaseModel):
    #: Key of the package: the id of its first flight, as the routes that act on a
    #: package through one of its flights (`/qt/edit-package/flight/{id}`).
    id: str
    #: The FlightType value of the primary task ("BARCAP", "Strike"...).
    task: str
    target: str
    #: Seconds since the mission start (negative before it).
    startup: int
    tot: int
    landing: int
    flight_ids: list[str]

    class Config:
        title = "TimelinePackage"


class TimelineJs(BaseModel):
    #: Mission start time, "HH:MM:SS": origin of every offset.
    start_time: str
    packages: list[TimelinePackageJs]

    class Config:
        title = "Timeline"

    @staticmethod
    def for_game(game: Game) -> TimelineJs:
        start = game.conditions.start_time
        packages = [
            _package(package, start)
            for package in game.blue.ato.packages
            if package.flights
        ]
        packages.sort(key=lambda p: (p.startup, p.tot))
        return TimelineJs(start_time=f"{start:%H:%M:%S}", packages=packages)


def _landing_time(flight: Flight) -> datetime:
    plan = flight.flight_plan
    try:
        return plan.landing_time
    except NotImplementedError:
        # Plans without a modelled return leg end at their TOT.
        return plan.tot


def _package(package: Package, start: datetime) -> TimelinePackageJs:
    def offset(time: datetime) -> int:
        return int((time - start).total_seconds())

    flights = package.flights
    task = package.primary_task
    return TimelinePackageJs(
        id=str(flights[0].id),
        task=str(task) if task is not None else "",
        target=package.target.name,
        startup=offset(min(f.flight_plan.startup_time() for f in flights)),
        tot=offset(package.time_over_target),
        landing=offset(max(_landing_time(f) for f in flights)),
        flight_ids=[str(f.id) for f in flights],
    )

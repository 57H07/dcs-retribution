"""Packages of both air tasking orders for the web UI (WEB-01.2)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight, Package


class PackageFlightJs(BaseModel):
    id: UUID
    #: A FlightType value, e.g. "BARCAP".
    task: str
    aircraft: str
    count: int
    #: Player slots of the flight.
    clients: int
    missing_pilots: int
    squadron: str
    departure: str
    custom_name: str | None

    class Config:
        title = "PackageFlight"

    @staticmethod
    def for_flight(flight: Flight) -> PackageFlightJs:
        return PackageFlightJs(
            id=flight.id,
            task=flight.flight_type.value,
            aircraft=str(flight.unit_type),
            count=flight.count,
            clients=flight.client_count,
            missing_pilots=flight.missing_pilots,
            squadron=flight.squadron.name,
            departure=flight.departure.name,
            custom_name=flight.custom_name,
        )


class PackageJs(BaseModel):
    id: UUID
    blue: bool
    #: The primary task (a FlightType value), or None without flights.
    task: str | None
    #: "OCA Strike", "BARCAP"... as the Qt ATO named the package.
    description: str
    custom_name: str | None
    target: str
    #: Time over target, None until the package is scheduled.
    tot: datetime | None
    auto_asap: bool
    flights: list[PackageFlightJs]
    #: Pilots missing in all the flights: they block a take off.
    missing_pilots: int

    class Config:
        title = "Package"

    @staticmethod
    def for_package(package: Package, blue: bool) -> PackageJs:
        task = package.primary_task
        tot = package.time_over_target
        flights = [PackageFlightJs.for_flight(f) for f in package.flights]
        return PackageJs(
            id=package.id,
            blue=blue,
            task=None if task is None else task.value,
            description=package.package_description,
            custom_name=package.custom_name,
            target=package.target.name,
            tot=None if tot == datetime.min else tot,
            auto_asap=package.auto_asap,
            flights=flights,
            missing_pilots=sum(f.missing_pilots for f in flights),
        )

    @staticmethod
    def all_in_game(game: Game) -> list[PackageJs]:
        """The packages of both coalitions, friendly first, in ATO order."""
        return [
            PackageJs.for_package(package, coalition.player.is_blue)
            for coalition in game.coalitions
            for package in coalition.ato.packages
        ]


class PackageTargetKind(str, Enum):
    CONTROL_POINT = "control-point"
    TGO = "tgo"
    FRONT_LINE = "front-line"
    DOWNED_PILOT = "downed-pilot"


class NewPackageJs(BaseModel):
    """What to plan a package against: opens the package editor on it."""

    target_kind: PackageTargetKind
    target_id: UUID

    class Config:
        title = "NewPackage"

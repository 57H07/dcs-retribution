"""Packages of both air tasking orders for the web UI (WEB-01.2)."""

from __future__ import annotations

from datetime import datetime, time
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.ato.flighttype import FlightType
from game.ato.starttype import StartType
from game.commands.packageflights import (
    AUTO_CREATE_EXCLUDED_WITH_CAS,
    AUTO_CREATE_MAX_COUNT,
    AUTO_CREATE_MIN_COUNT,
    AUTO_CREATE_SUPPORT_TASKS,
    auto_create_aircraft,
    auto_create_default_count,
    auto_create_primary_tasks,
    max_flight_size,
    plannable_tasks,
    squadrons_for,
)
from game.commands.packages import coalition_of
from game.commands.preferences import is_player_module
from game.commands.transfers import can_plan_transport_mission
from game.objectives import aimed_at
from game.theater.controlpoint import ControlPoint
from game.theater.frontline import FrontLine
from game.utils import meters

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight, Package
    from game.squadrons import AirWing, Squadron
    from game.theater.missiontarget import MissionTarget


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


def _objectives(game: Game, target: MissionTarget) -> list[str]:
    """The titles of the objectives in progress about `target`.

    A front line is about the bases on both of its sides.
    """
    ids = [getattr(target, "id", None)]
    if isinstance(target, FrontLine):
        ids += [target.blue_cp.id, target.red_cp.id]
    titles: list[str] = []
    for target_id in ids:
        if target_id is None:
            continue
        for objective in aimed_at(game, target_id):
            if objective.title not in titles:
                titles.append(objective.title)
    return titles


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
    #: The campaign objectives in progress about its target (#194).
    objectives: list[str]

    class Config:
        title = "Package"

    @staticmethod
    def for_package(game: Game, package: Package, blue: bool) -> PackageJs:
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
            objectives=_objectives(game, package.target),
        )

    @staticmethod
    def all_in_game(game: Game) -> list[PackageJs]:
        """The packages of both coalitions, friendly first, in ATO order."""
        return [
            PackageJs.for_package(game, package, coalition.player.is_blue)
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


class PackageNameJs(BaseModel):
    name: str

    class Config:
        title = "PackageName"


class PackageTotJs(BaseModel):
    """A time of day: the date is the one of the current TOT."""

    tot: time

    class Config:
        title = "PackageTot"


class PackageEditorFlightJs(PackageFlightJs):
    #: A StartType value, e.g. "Cold".
    start_type: str
    startup: datetime
    takeoff: datetime
    #: False once under way: removing the flight then aborts it.
    cancelable: bool

    class Config:
        title = "PackageEditorFlight"

    @staticmethod
    def for_editor(flight: Flight) -> PackageEditorFlightJs:
        return PackageEditorFlightJs(
            **PackageFlightJs.for_flight(flight).model_dump(),
            start_type=flight.start_type.value,
            startup=flight.flight_plan.startup_time(),
            takeoff=flight.flight_plan.takeoff_time(),
            cancelable=flight.state.cancelable,
        )


class PackageDetailJs(BaseModel):
    """What the package editor shows (WEB-04.1)."""

    id: UUID
    blue: bool
    task: str | None
    description: str
    custom_name: str | None
    target: str
    tot: datetime | None
    #: "Earliest TOT" is on: the TOT follows the flights.
    auto_asap: bool
    #: The TOT cannot change once a flight has started.
    tot_locked: bool
    #: The auto-planner only fills an empty package.
    can_auto_create: bool
    #: Closest departure base of the flights and its distance to the target.
    closest_base: str | None
    closest_base_distance_nm: int | None
    #: An empty package on a player base can become a Transport mission from there.
    transport_origin_id: UUID | None
    #: The campaign objectives in progress about its target (#194).
    objectives: list[str]
    flights: list[PackageEditorFlightJs]

    class Config:
        title = "PackageDetail"

    @staticmethod
    def for_package(game: Game, package: Package) -> PackageDetailJs:
        summary = PackageJs.for_package(
            game, package, coalition_of(game, package).player.is_blue
        )
        closest = min(
            (flight.departure for flight in package.flights),
            key=package.target.distance_to,
            default=None,
        )
        return PackageDetailJs(
            id=summary.id,
            blue=summary.blue,
            task=summary.task,
            description=summary.description,
            custom_name=summary.custom_name,
            target=summary.target,
            objectives=summary.objectives,
            tot=summary.tot,
            auto_asap=summary.auto_asap,
            tot_locked=not package.all_flights_waiting_for_start(),
            can_auto_create=not package.flights,
            closest_base=None if closest is None else closest.name,
            closest_base_distance_nm=(
                None
                if closest is None
                else round(meters(package.target.distance_to(closest)).nautical_miles)
            ),
            transport_origin_id=(
                package.target.id
                if not package.flights
                and isinstance(package.target, ControlPoint)
                and can_plan_transport_mission(package.target)
                else None
            ),
            flights=[PackageEditorFlightJs.for_editor(f) for f in package.flights],
        )


class FlightSquadronOptionJs(BaseModel):
    id: UUID
    name: str
    base: str
    available: int
    #: The most aircraft a new flight of this squadron can have.
    max_size: int
    #: The StartType value its base dictates (carrier, off-map spawn), if any.
    required_start_type: str | None

    class Config:
        title = "FlightSquadronOption"

    @staticmethod
    def for_squadron(squadron: Squadron) -> FlightSquadronOptionJs:
        required = squadron.location.required_aircraft_start_type
        return FlightSquadronOptionJs(
            id=squadron.id,
            name=str(squadron),
            base=squadron.location.name,
            available=squadron.untasked_aircraft,
            max_size=max_flight_size(squadron),
            required_start_type=None if required is None else required.value,
        )


class FlightAircraftOptionJs(BaseModel):
    #: The id `POST /packages/{id}/auto-create` takes.
    id: str
    name: str
    #: The player owns the module: listed first, on the player's side only.
    player_module: bool
    squadrons: list[FlightSquadronOptionJs]

    class Config:
        title = "FlightAircraftOption"


class FlightTaskOptionJs(BaseModel):
    task: str
    #: The player's modules first, then the best aircraft for the task, each with the
    #: squadrons that can fly it now.
    aircraft: list[FlightAircraftOptionJs]

    class Config:
        title = "FlightTaskOption"

    @staticmethod
    def for_task(air_wing: AirWing, task: FlightType) -> FlightTaskOptionJs:
        aircraft = []
        for aircraft_type in air_wing.best_available_aircrafts_for(task):
            squadrons = squadrons_for(air_wing, task, aircraft_type)
            if squadrons:
                aircraft.append(
                    FlightAircraftOptionJs(
                        id=aircraft_type.variant_id,
                        name=str(aircraft_type),
                        player_module=(
                            air_wing.player.is_blue and is_player_module(aircraft_type)
                        ),
                        squadrons=[
                            FlightSquadronOptionJs.for_squadron(s) for s in squadrons
                        ],
                    )
                )
        aircraft.sort(key=lambda option: not option.player_module)
        return FlightTaskOptionJs(task=task.value, aircraft=aircraft)


class FlightOptionsJs(BaseModel):
    tasks: list[FlightTaskOptionJs]
    #: StartType values.
    start_types: list[str]

    class Config:
        title = "FlightOptions"

    @staticmethod
    def for_package(game: Game, package: Package) -> FlightOptionsJs:
        coalition = coalition_of(game, package)
        return FlightOptionsJs(
            tasks=[
                FlightTaskOptionJs.for_task(coalition.air_wing, task)
                for task in plannable_tasks(
                    package.target, game.settings, coalition.player
                )
            ],
            start_types=[start_type.value for start_type in StartType],
        )


class NewFlightJs(BaseModel):
    task: str
    squadron_id: UUID
    size: int
    #: None for the default of the task and pilots.
    start_type: StartType | None = None

    class Config:
        title = "NewFlight"


class AutoCreateAircraftJs(BaseModel):
    id: str
    name: str
    #: The largest flight the auto-planner can fill with it this turn.
    max_count: int

    class Config:
        title = "AutoCreateAircraft"


class AutoCreateTaskJs(BaseModel):
    task: str
    default_count: int
    aircraft: list[AutoCreateAircraftJs]

    class Config:
        title = "AutoCreateTask"

    @staticmethod
    def for_task(
        air_wing: AirWing, target: MissionTarget, task: FlightType, default_count: int
    ) -> AutoCreateTaskJs:
        return AutoCreateTaskJs(
            task=task.value,
            default_count=default_count,
            aircraft=[
                AutoCreateAircraftJs(
                    id=aircraft.variant_id, name=str(aircraft), max_count=max_count
                )
                for aircraft, max_count in auto_create_aircraft(
                    air_wing, target, task
                ).items()
            ],
        )


class AutoCreateOptionsJs(BaseModel):
    """The form of `QAutoCreateDialog`: one main flight, then optional ones."""

    primary: list[AutoCreateTaskJs]
    support: list[AutoCreateTaskJs]
    #: Support tasks a CAS package does not take.
    excluded_with_cas: list[str]
    min_count: int
    max_count: int

    class Config:
        title = "AutoCreateOptions"

    @staticmethod
    def for_package(game: Game, package: Package) -> AutoCreateOptionsJs:
        coalition = coalition_of(game, package)
        air_wing = coalition.air_wing
        count = auto_create_default_count(package.target)
        return AutoCreateOptionsJs(
            primary=[
                AutoCreateTaskJs.for_task(air_wing, package.target, task, count)
                for task in auto_create_primary_tasks(package.target, coalition.player)
            ],
            support=[
                AutoCreateTaskJs.for_task(air_wing, package.target, task, default)
                for task, default in AUTO_CREATE_SUPPORT_TASKS.items()
            ],
            excluded_with_cas=[
                task.value
                for task in AUTO_CREATE_SUPPORT_TASKS
                if task in AUTO_CREATE_EXCLUDED_WITH_CAS
            ],
            min_count=AUTO_CREATE_MIN_COUNT,
            max_count=AUTO_CREATE_MAX_COUNT,
        )


class AutoCreateFlightJs(BaseModel):
    task: str
    count: int
    #: The preferred aircraft id, None to let the planner choose.
    aircraft: str | None = None

    class Config:
        title = "AutoCreateFlight"


class AutoCreateRequestJs(BaseModel):
    #: The main flight first, then the optional ones.
    flights: list[AutoCreateFlightJs]

    class Config:
        title = "AutoCreateRequest"

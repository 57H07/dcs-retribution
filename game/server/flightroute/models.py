from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.commands.flightroute import (
    MAX_ALTITUDE_FT,
    MIN_ALTITUDE_FT,
    can_insert_nav_after,
    default_bulk_altitude,
    deletion_degrades,
    is_flown,
    is_movable,
    recreation_tasks,
    threat_warning,
    waypoint_times,
)
from game.server.leaflet import LeafletPoint

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight


class FlightRouteWaypointJs(BaseModel):
    #: Place in the flight plan, the # of the table: 0 is the departure.
    index: int
    name: str
    #: A FlightWaypointType name, e.g. "INGRESS_STRIKE".
    type: str
    position: LeafletPoint
    altitude_ft: int
    #: "MSL" or "AGL".
    altitude_reference: str
    #: None when the plan gives this waypoint no time.
    time: datetime | None
    #: "takeoff", "tot", "depart" or "estimated", None without a time.
    time_kind: str | None
    #: The waypoint the package TOT applies to.
    is_tot: bool
    #: Fuel needed here to land with a safe reserve. None without fuel data or past the
    #: landing point.
    min_fuel_lb: int | None
    is_movable: bool
    #: Bullseye and divert are listed but not flown.
    include_in_path: bool
    can_delete: bool
    #: Deleting it turns the route into a custom flight plan: ask first.
    delete_degrades: bool
    can_insert_after: bool
    #: Why this waypoint is inside an enemy threat zone.
    threat: str | None

    class Config:
        title = "FlightRouteWaypoint"


class FlightRouteJs(BaseModel):
    """The Route tab of a flight (WEB-04.4). Commands answer it whole."""

    flight_id: UUID
    blue: bool
    #: The tasks it can be recreated as (FlightType values), the current one first.
    recreate_tasks: list[str]
    #: A custom flight plan no longer respects the TOTs of the package.
    is_custom: bool
    bulk_altitude_ft: int
    min_altitude_ft: int
    max_altitude_ft: int
    waypoints: list[FlightRouteWaypointJs]

    class Config:
        title = "FlightRoute"

    @staticmethod
    def for_flight(game: Game, flight: Flight) -> FlightRouteJs:
        plan = flight.flight_plan
        waypoints = plan.waypoints
        times = waypoint_times(flight)
        min_fuel = plan.estimate_min_fuel(waypoints)
        rows = []
        for index, waypoint in enumerate(waypoints):
            time = times[index]
            fuel = min_fuel.get(waypoint)
            rows.append(
                FlightRouteWaypointJs(
                    index=index,
                    name=waypoint.display_name.strip(),
                    type=waypoint.waypoint_type.name,
                    position=LeafletPoint.model_validate(waypoint.position.latlng()),
                    altitude_ft=round(waypoint.alt.feet),
                    altitude_reference="AGL" if waypoint.alt_type == "RADIO" else "MSL",
                    time=None if time is None else time.time,
                    time_kind=None if time is None else time.kind.value,
                    is_tot=waypoint is plan.tot_waypoint,
                    min_fuel_lb=None if fuel is None else round(fuel),
                    is_movable=is_movable(waypoint),
                    include_in_path=is_flown(waypoint),
                    can_delete=index > 0,
                    delete_degrades=index > 0 and deletion_degrades(flight, waypoint),
                    can_insert_after=can_insert_nav_after(flight, index),
                    threat=threat_warning(flight, index, waypoint),
                )
            )
        return FlightRouteJs(
            flight_id=flight.id,
            blue=flight.blue.is_blue,
            recreate_tasks=[task.value for task in recreation_tasks(game, flight)],
            is_custom=plan.is_custom,
            bulk_altitude_ft=default_bulk_altitude(flight),
            min_altitude_ft=MIN_ALTITUDE_FT,
            max_altitude_ft=MAX_ALTITUDE_FT,
            waypoints=rows,
        )


class PredefinedWaypointJs(BaseModel):
    #: Its identifier for `add_predefined_waypoint`.
    name: str
    description: str
    #: Other waypoints of the same object can come with it.
    has_siblings: bool

    class Config:
        title = "PredefinedWaypoint"


class WaypointAltitudeJs(BaseModel):
    altitude_ft: float

    class Config:
        title = "WaypointAltitude"


class WaypointNameJs(BaseModel):
    #: Blank goes back to the automatic name.
    name: str

    class Config:
        title = "WaypointName"


class NewPredefinedWaypointJs(BaseModel):
    name: str
    #: Also adds the other targets of the same object.
    same_location: bool = True

    class Config:
        title = "NewPredefinedWaypoint"


class RecreateRouteJs(BaseModel):
    #: A value of `FlightRouteJs.recreate_tasks`.
    task: str

    class Config:
        title = "RecreateRoute"

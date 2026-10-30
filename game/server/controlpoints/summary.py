"""Summary of a base for the map inspector of the command view (WEB-01.3)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from game.config import RUNWAY_REPAIR_COST
from game.theater.controlpoint import ParkingType
from game.utils import meters

if TYPE_CHECKING:
    from dcs import Point

    from game import Game
    from game.theater import ControlPoint

CATEGORY_LABELS = {
    "airfield": "Airfield",
    "cv": "Carrier",
    "lha": "LHA",
    "offmap": "Off-map spawn",
    "fob": "FOB",
}

ALL_PARKING = ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)

RunwayState = Literal["operational", "damaged", "repairing"]


def distance_to_front_nm(game: Game, position: Point) -> Optional[float]:
    """Distance to the closest front line, in nautical miles; None without one."""
    distances = [
        position.distance_to_point(front_line.position)
        for front_line in game.theater.conflicts()
    ]
    if not distances:
        return None
    return round(meters(min(distances)).nautical_miles, 1)


class CountJs(BaseModel):
    current: int
    total: int

    class Config:
        title = "Count"


class RunwayJs(BaseModel):
    state: RunwayState
    repair_turns_remaining: Optional[int]

    class Config:
        title = "Runway"


class ControlPointSummaryJs(BaseModel):
    id: UUID
    name: str
    blue: bool
    sidc: str
    category: str
    distance_to_front_nm: Optional[float]
    #: None for bases without a destroyable runway (carriers, FOBs, off-map).
    runway: Optional[RunwayJs]
    #: Aircraft present / parking slots; None for a base without parking.
    parking: Optional[CountJs]
    #: Ground units present / deployable limit; None without an active front.
    ground_units: Optional[CountJs]
    ammo_depots: CountJs
    fuel_depots: CountJs
    can_buy_aircraft: bool
    can_buy_ground_units: bool
    can_repair_runway: bool
    can_afford_runway_repair: bool
    runway_repair_cost: int

    class Config:
        title = "ControlPointSummary"

    @staticmethod
    def for_control_point(game: Game, cp: ControlPoint) -> ControlPointSummaryJs:
        blue = cp.captured.is_blue
        runway: Optional[RunwayJs] = None
        if cp.runway_is_destroyable:
            status = cp.runway_status
            state: RunwayState = "operational"
            if status.damaged:
                state = (
                    "damaged" if status.repair_turns_remaining is None else "repairing"
                )
            runway = RunwayJs(
                state=state, repair_turns_remaining=status.repair_turns_remaining
            )
        total_parking = cp.total_aircraft_parking(ALL_PARKING)
        parking: Optional[CountJs] = None
        if total_parking > 0:
            parking = CountJs(
                current=cp.allocated_aircraft(ALL_PARKING).total_present,
                total=total_parking,
            )
        ground_units: Optional[CountJs] = None
        if cp.has_active_frontline:
            ground_units = CountJs(
                current=cp.base.total_armor, total=cp.frontline_unit_count_limit
            )
        return ControlPointSummaryJs(
            id=cp.id,
            name=cp.name,
            blue=blue,
            sidc=str(cp.sidc()),
            category=CATEGORY_LABELS.get(cp.category, cp.category.capitalize()),
            distance_to_front_nm=distance_to_front_nm(game, cp.position),
            runway=runway,
            parking=parking,
            ground_units=ground_units,
            ammo_depots=CountJs(
                current=cp.active_ammo_depots_count,
                total=cp.total_ammo_depots_count,
            ),
            fuel_depots=CountJs(
                current=cp.active_fuel_depots_count,
                total=cp.total_fuel_depots_count,
            ),
            can_buy_aircraft=blue and total_parking > 0,
            can_buy_ground_units=blue and cp.can_recruit_ground_units(game),
            can_repair_runway=blue and cp.runway_can_be_repaired,
            can_afford_runway_repair=game.blue.budget >= RUNWAY_REPAIR_COST,
            runway_repair_cost=RUNWAY_REPAIR_COST,
        )

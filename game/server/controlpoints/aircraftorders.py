"""Squadrons of a base and their aircraft orders (WEB-02.2).

The rules are in `game.commands.aircraftorders`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import BaseModel

from game.commands import SquadronChoice, max_aircraft_to_add, max_aircraft_to_remove
from .summary import ALL_PARKING, CountJs

if TYPE_CHECKING:
    from game.squadrons import Squadron
    from game.theater import ControlPoint


def _by_aircraft_and_name(squadron: Squadron) -> tuple[str, str]:
    return squadron.aircraft.display_name, squadron.name


class SquadronOrderRowJs(BaseModel):
    squadron_id: UUID
    squadron: str
    aircraft: str
    unit_cost: float
    owned: int
    #: Most aircraft the squadron may hold; None without the limits setting.
    max_aircraft: Optional[int]
    #: Paid orders delivered next turn; negative for pending sales.
    pending: int
    #: Most aircraft this row alone can order now (budget, parking, squadron size).
    max_add: int
    #: Most aircraft this row can cancel or sell now.
    max_remove: int

    class Config:
        title = "SquadronOrderRow"

    @staticmethod
    def for_squadron(cp: ControlPoint, squadron: Squadron) -> SquadronOrderRowJs:
        limited = squadron.settings.enable_squadron_aircraft_limits
        return SquadronOrderRowJs(
            squadron_id=squadron.id,
            squadron=squadron.name,
            aircraft=squadron.aircraft.display_name,
            unit_cost=squadron.aircraft.price,
            owned=squadron.owned_aircraft,
            max_aircraft=squadron.max_size if limited else None,
            pending=squadron.pending_deliveries,
            max_add=max_aircraft_to_add(cp, squadron),
            max_remove=max_aircraft_to_remove(squadron),
        )


class IncomingSquadronJs(BaseModel):
    squadron: str
    aircraft: str
    owned: int
    origin: str

    class Config:
        title = "IncomingSquadron"


class AirfieldJs(BaseModel):
    #: Empty for an enemy base.
    squadrons: list[SquadronOrderRowJs]
    #: Aircraft at the base once orders and transfers arrive, and its parking.
    parking_after_delivery: CountJs
    #: Squadrons transferring here next turn.
    incoming: list[IncomingSquadronJs]

    class Config:
        title = "Airfield"

    @staticmethod
    def for_control_point(cp: ControlPoint) -> AirfieldJs:
        if not cp.captured.is_blue:
            return AirfieldJs(
                squadrons=[],
                parking_after_delivery=CountJs(current=0, total=0),
                incoming=[],
            )
        return AirfieldJs(
            squadrons=[
                SquadronOrderRowJs.for_squadron(cp, squadron)
                for squadron in sorted(cp.squadrons, key=_by_aircraft_and_name)
            ],
            parking_after_delivery=CountJs(
                current=cp.allocated_aircraft(ALL_PARKING).total,
                total=cp.total_aircraft_parking(ALL_PARKING),
            ),
            incoming=[
                IncomingSquadronJs(
                    squadron=squadron.name,
                    aircraft=squadron.aircraft.display_name,
                    owned=squadron.owned_aircraft,
                    origin=squadron.location.name,
                )
                for squadron in sorted(
                    cp.coalition.air_wing.iter_squadrons(), key=_by_aircraft_and_name
                )
                if squadron.destination == cp
            ],
        )


class AircraftOrderLineJs(BaseModel):
    squadron_id: UUID
    #: Aircraft to buy; negative to cancel orders, then sell.
    quantity: int

    class Config:
        title = "AircraftOrderLine"


class AircraftOrdersJs(BaseModel):
    orders: list[AircraftOrderLineJs]

    class Config:
        title = "AircraftOrders"


class SquadronPresetJs(BaseModel):
    name: str
    label: str

    class Config:
        title = "SquadronPreset"


class SquadronChoiceJs(BaseModel):
    aircraft: str
    display_name: str
    tasks: list[str]
    presets: list[SquadronPresetJs]

    class Config:
        title = "SquadronChoice"

    @staticmethod
    def from_choice(choice: SquadronChoice) -> SquadronChoiceJs:
        return SquadronChoiceJs(
            aircraft=choice.aircraft.variant_id,
            display_name=choice.aircraft.display_name,
            tasks=[task.value for task in choice.tasks],
            presets=[
                SquadronPresetJs(
                    name=preset.name,
                    label=(
                        f"{preset.name} ({preset.nickname})"
                        if preset.nickname
                        else preset.name
                    ),
                )
                for preset in choice.presets
            ],
        )


class NewSquadronJs(BaseModel):
    aircraft: str
    primary_task: str
    #: Name of a preset; None generates a squadron.
    preset: Optional[str] = None

    class Config:
        title = "NewSquadron"

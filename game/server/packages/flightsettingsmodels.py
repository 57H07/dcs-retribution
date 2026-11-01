"""The General and Pilots tabs of a flight in the package editor (WEB-04.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.ato.starttype import StartType
from game.commands.flightsettings import (
    CALLSIGN_MAX_NUMBER,
    CALLSIGN_MIN_NUMBER,
    divert_options,
    flight_squadron_candidates,
    max_flight_resize,
)
from game.commands.squadrons import player_flag_refusal
from .models import PackageDetailJs

if TYPE_CHECKING:
    from game.ato import Flight
    from game.squadrons import Pilot, Squadron


class FlightSettingsSquadronJs(BaseModel):
    id: UUID
    name: str
    aircraft: str
    base: str
    available: int

    class Config:
        title = "FlightSettingsSquadron"

    @staticmethod
    def for_squadron(squadron: Squadron) -> FlightSettingsSquadronJs:
        return FlightSettingsSquadronJs(
            id=squadron.id,
            name=squadron.name,
            aircraft=str(squadron.aircraft),
            base=squadron.location.name,
            available=squadron.untasked_aircraft,
        )


class FlightDivertOptionJs(BaseModel):
    id: UUID
    name: str

    class Config:
        title = "FlightDivertOption"


class FlightPilotOptionJs(BaseModel):
    id: UUID
    name: str
    player: bool

    class Config:
        title = "FlightPilotOption"

    @staticmethod
    def for_pilot(pilot: Pilot) -> FlightPilotOptionJs:
        return FlightPilotOptionJs(id=pilot.id, name=pilot.name, player=pilot.player)


class FlightPilotSlotJs(BaseModel):
    pilot: Optional[FlightPilotOptionJs]
    #: Why the player box is locked; null when it can change.
    player_refusal: Optional[str]

    class Config:
        title = "FlightPilotSlot"

    @staticmethod
    def for_slot(squadron: Squadron, pilot: Optional[Pilot]) -> FlightPilotSlotJs:
        if pilot is None:
            return FlightPilotSlotJs(pilot=None, player_refusal=None)
        return FlightPilotSlotJs(
            pilot=FlightPilotOptionJs.for_pilot(pilot),
            player_refusal=player_flag_refusal(squadron, pilot),
        )


class FlightCallsignJs(BaseModel):
    name: str
    number: int

    class Config:
        title = "FlightCallsign"


class FlightSettingsJs(BaseModel):
    """What the engine has and offers for these tabs: the client lists and sends."""

    id: UUID
    task: str
    aircraft: str
    departure: str
    arrival: str
    startup: datetime
    #: False once under way: only its name and callsign can change.
    editable: bool

    squadron: FlightSettingsSquadronJs
    #: The other squadrons it can move to.
    squadron_options: list[FlightSettingsSquadronJs]

    count: int
    max_count: int

    #: A StartType value.
    start_type: str
    start_types: list[str]
    #: The base dictates the start type.
    start_type_locked: bool

    divert_id: Optional[UUID]
    divert_options: list[FlightDivertOptionJs]

    #: Negative is ahead of the package.
    tot_offset_seconds: int

    custom_name: Optional[str]
    #: None is automatic.
    callsign: Optional[FlightCallsignJs]
    callsign_names: list[str]
    callsign_min_number: int
    callsign_max_number: int

    #: One per aircraft, lead first.
    slots: list[FlightPilotSlotJs]
    #: The free pilots of the squadron, players first.
    free_pilots: list[FlightPilotOptionJs]

    class Config:
        title = "FlightSettings"

    @staticmethod
    def for_flight(flight: Flight) -> FlightSettingsJs:
        squadron = flight.squadron
        callsign = flight.callsign
        return FlightSettingsJs(
            id=flight.id,
            task=flight.flight_type.value,
            aircraft=str(flight.unit_type),
            departure=flight.departure.name,
            arrival=flight.arrival.name,
            startup=flight.flight_plan.startup_time(),
            editable=flight.state.cancelable,
            squadron=FlightSettingsSquadronJs.for_squadron(squadron),
            squadron_options=[
                FlightSettingsSquadronJs.for_squadron(s)
                for s in flight_squadron_candidates(flight)
            ],
            count=flight.count,
            max_count=max_flight_resize(flight),
            start_type=flight.start_type.value,
            start_types=[start_type.value for start_type in StartType],
            start_type_locked=(
                flight.departure.required_aircraft_start_type is not None
            ),
            divert_id=None if flight.divert is None else flight.divert.id,
            divert_options=[
                FlightDivertOptionJs(id=cp.id, name=cp.name)
                for cp in divert_options(flight)
            ],
            tot_offset_seconds=int(flight.flight_plan.tot_offset.total_seconds()),
            custom_name=flight.custom_name,
            callsign=(
                None
                if callsign is None or callsign.name is None or callsign.nr is None
                else FlightCallsignJs(name=callsign.name, number=callsign.nr)
            ),
            callsign_names=flight.available_callsigns,
            callsign_min_number=CALLSIGN_MIN_NUMBER,
            callsign_max_number=CALLSIGN_MAX_NUMBER,
            slots=[
                FlightPilotSlotJs.for_slot(squadron, pilot)
                for pilot in flight.roster.iter_pilots()
            ],
            free_pilots=[
                FlightPilotOptionJs.for_pilot(pilot)
                for pilot in sorted(
                    squadron.available_pilots, key=lambda p: (not p.player, p.name)
                )
            ],
        )


class FlightSquadronChoiceJs(BaseModel):
    squadron_id: UUID

    class Config:
        title = "FlightSquadronChoice"


class FlightSquadronChangedJs(BaseModel):
    #: The flight that took the place of the old one: it has another id.
    flight_id: UUID
    package: PackageDetailJs

    class Config:
        title = "FlightSquadronChanged"


class FlightSizeJs(BaseModel):
    size: int

    class Config:
        title = "FlightSize"


class FlightStartTypeJs(BaseModel):
    start_type: StartType

    class Config:
        title = "FlightStartType"


class FlightDivertJs(BaseModel):
    #: None for no divert field.
    divert_id: Optional[UUID] = None

    class Config:
        title = "FlightDivert"


class FlightTotOffsetJs(BaseModel):
    seconds: int

    class Config:
        title = "FlightTotOffset"


class FlightCustomNameJs(BaseModel):
    name: str

    class Config:
        title = "FlightCustomName"


class FlightPilotChoiceJs(BaseModel):
    #: None to leave the slot empty.
    pilot_id: Optional[UUID] = None

    class Config:
        title = "FlightPilotChoice"


class FlightSlotPlayerJs(BaseModel):
    player: bool

    class Config:
        title = "FlightSlotPlayer"

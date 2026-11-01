"""The Radios & TACAN tab of a flight in the package editor (WEB-04.5)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.commands.baseradios import FREQUENCY_MHZ_RANGE
from game.commands.flightradios import (
    datalink_fields,
    datalink_of,
    flight_radio_warnings,
    flight_tacan_warnings,
    frequency_ranges,
    has_flight_tacan,
    package_radio_warnings,
)
from game.radio.datalink import DataLinkKey

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight
    from game.radio.radios import RadioRange

_DATALINK_NAMES = {
    DataLinkKey.LINK16: "Link 16",
    DataLinkKey.SADL: "SADL",
    DataLinkKey.IDM: "IDM",
}


class RadioRangeJs(BaseModel):
    #: Inclusive.
    min_mhz: float
    #: Exclusive.
    max_mhz: float
    step_mhz: float
    #: "AM" or "FM".
    modulation: str

    class Config:
        title = "RadioRange"

    @staticmethod
    def for_range(radio_range: RadioRange) -> RadioRangeJs:
        return RadioRangeJs(
            min_mhz=radio_range.minimum.mhz,
            max_mhz=radio_range.maximum.mhz,
            step_mhz=radio_range.step.mhz,
            modulation=radio_range.modulation.name,
        )


class DatalinkFieldJs(BaseModel):
    #: The value `PUT .../radios/datalink/{member}` takes.
    identifier: str
    label: str
    max_length: int

    class Config:
        title = "DatalinkField"


class DatalinkMemberJs(BaseModel):
    #: The position in the flight.
    index: int
    pilot: str | None
    #: The values set, by identifier; a missing one is automatic.
    values: dict[str, str]

    class Config:
        title = "DatalinkMember"


class FlightDatalinkJs(BaseModel):
    #: "Link 16", "SADL" or "IDM".
    name: str
    fields: list[DatalinkFieldJs]
    members: list[DatalinkMemberJs]

    class Config:
        title = "FlightDatalink"

    @staticmethod
    def for_flight(flight: Flight) -> FlightDatalinkJs | None:
        key = datalink_of(flight)
        if key is None:
            return None
        fields = datalink_fields(flight)
        return FlightDatalinkJs(
            name=_DATALINK_NAMES[key],
            fields=[
                DatalinkFieldJs(
                    identifier=f.identifier, label=f.label, max_length=f.max_length
                )
                for f in fields
            ],
            members=[
                DatalinkMemberJs(
                    index=index,
                    pilot=None if member.pilot is None else member.pilot.name,
                    values={
                        f.identifier: str(member.properties[f.identifier])
                        for f in fields
                        if f.identifier in member.properties
                    },
                )
                for index, member in enumerate(flight.iter_members())
            ],
        )


class FlightRadiosJs(BaseModel):
    """What the Radios & TACAN tab shows: each command answers it whole."""

    frequency_mhz: float | None
    #: "AM" or "FM".
    modulation: str | None
    #: What the radio of the flight can tune.
    ranges: list[RadioRangeJs]
    warnings: list[str]
    package_frequency_mhz: float | None
    package_min_mhz: float
    package_max_mhz: float
    package_warnings: list[str]
    #: Only tankers with a beacon have a TACAN of their own.
    has_tacan: bool
    tacan_channel: int | None
    #: "X" or "Y".
    tacan_band: str | None
    tacan_callsign: str | None
    tacan_warnings: list[str]
    #: None when the aircraft has no datalink to set.
    datalink: FlightDatalinkJs | None
    #: Where ICLS and Link 4 are set: they belong to the carrier.
    departure_id: UUID
    departure: str

    class Config:
        title = "FlightRadios"

    @staticmethod
    def for_flight(game: Game, flight: Flight) -> FlightRadiosJs:
        package = flight.package
        frequency = flight.frequency
        tacan = flight.tacan
        return FlightRadiosJs(
            frequency_mhz=None if frequency is None else frequency.mhz,
            modulation=None if frequency is None else frequency.modulation.name,
            ranges=[RadioRangeJs.for_range(r) for r in frequency_ranges(flight)],
            warnings=flight_radio_warnings(game, flight),
            package_frequency_mhz=(
                None if package.frequency is None else package.frequency.mhz
            ),
            package_min_mhz=FREQUENCY_MHZ_RANGE[0],
            package_max_mhz=FREQUENCY_MHZ_RANGE[1],
            package_warnings=package_radio_warnings(game, package),
            has_tacan=has_flight_tacan(flight),
            tacan_channel=None if tacan is None else tacan.number,
            tacan_band=None if tacan is None else tacan.band.value,
            tacan_callsign=flight.tcn_name,
            tacan_warnings=flight_tacan_warnings(game, flight),
            datalink=FlightDatalinkJs.for_flight(flight),
            departure_id=flight.departure.id,
            departure=flight.departure.name,
        )


class FlightFrequencyJs(BaseModel):
    #: None goes back to automatic.
    mhz: float | None = None
    #: None for the first one the radio has at this frequency.
    modulation: str | None = None

    class Config:
        title = "FlightFrequency"


class PackageFrequencyJs(BaseModel):
    #: None goes back to automatic.
    mhz: float | None = None

    class Config:
        title = "PackageFrequency"


class FlightTacanJs(BaseModel):
    #: None goes back to automatic.
    channel: int | None = None
    band: str | None = None
    callsign: str | None = None

    class Config:
        title = "FlightTacan"


class DatalinkValueJs(BaseModel):
    identifier: str
    #: Empty goes back to automatic.
    value: str

    class Config:
        title = "DatalinkValue"

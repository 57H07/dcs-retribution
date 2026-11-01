"""Frequency, TACAN and datalink of a flight, frequency of a package (WEB-04.5).

The radio dialogs of the Qt flight editor (`QFrequencyWidget`, `QTacanWidget`,
`PropertyEditBox`) and of `QPackageDialog`. The limits are those of the base radios
(`baseradios.py`), whose warnings the flights share. A setting left to None is chosen
automatically at mission generation.

ICLS and Link 4 belong to a carrier, not to a flight: the radio tab of a flight edits
them on its departure base, through `set_base_radios`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from dcs.task import Modulation

from game.ato.flighttype import FlightType
from game.radio.datalink import (
    DataLinkKey,
    OWNSHIP_CALLSIGN,
    VOICE_CALLSIGN_LABEL,
    VOICE_CALLSIGN_NUMBER,
)
from game.radio.radios import MHz, RadioFrequency, RadioRange, kHz
from game.radio.tacan import TacanChannel
from .baseradios import (
    FREQUENCY_MHZ_RANGE,
    TACAN_CHANNEL_RANGE,
    check_channel,
    check_mhz,
    clean_callsign,
    frequency_warnings,
    tacan_band,
    tacan_channels_in_use,
    to_frequency,
)
from .errors import CommandError
from .packages import coalition_of

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight, Package
    from game.sim import GameUpdateEvents

#: What `QFrequencyWidget` offers for an aircraft with no known intra-flight radio.
DEFAULT_RANGES = (RadioRange(MHz(30), MHz(400), kHz(25)),)

_STN_LENGTHS = {DataLinkKey.LINK16: 5, DataLinkKey.SADL: 4}
_VOICE_CALLSIGN_LENGTH = 2
_IDM_ID_LENGTH = 2
_OWNSHIP_LENGTH = 5


@dataclass(frozen=True)
class DatalinkField:
    #: The DCS property it sets on the member.
    identifier: str
    label: str
    max_length: int


def frequency_ranges(flight: Flight) -> tuple[RadioRange, ...]:
    """What the radio of this flight can tune, as its Qt dialog offers it."""
    radio = flight.unit_type.intra_flight_radio
    return DEFAULT_RANGES if radio is None else tuple(radio.ranges)


def _modulation(value: str) -> Modulation:
    try:
        return Modulation[value]
    except KeyError:
        raise CommandError(f"Unknown modulation: {value}.", status_code=422)


def set_flight_frequency(
    flight: Flight,
    mhz: Optional[float],
    modulation: Optional[str],
    events: GameUpdateEvents,
) -> None:
    """Sets the frequency of the flight; None goes back to automatic.

    Without a modulation, the first one its radio has there, as the Qt dialog proposes.

    Raises:
        CommandError: the radio of the flight cannot tune it, or not with that
            modulation.
    """
    if mhz is None:
        flight.frequency = None
        events.update_flight(flight)
        return
    hertz = round(mhz * 10**6)
    covering = [
        r
        for r in frequency_ranges(flight)
        if r.minimum.hertz <= hertz < r.maximum.hertz
    ]
    if not covering:
        raise CommandError(f"The radio of {flight.unit_type} cannot tune {mhz:g} MHz.")
    offered = sorted({r.modulation for r in covering}, key=lambda m: m.name)
    chosen = offered[0] if modulation is None else _modulation(modulation)
    if chosen not in offered:
        raise CommandError(
            f"The radio of {flight.unit_type} has no {chosen.name} at {mhz:g} MHz."
        )
    flight.frequency = RadioFrequency(hertz=hertz, modulation=chosen)
    events.update_flight(flight)


def set_package_frequency(
    package: Package, mhz: Optional[float], events: GameUpdateEvents
) -> None:
    """Sets the frequency of the package; None goes back to automatic."""
    check_mhz("The frequency", mhz, FREQUENCY_MHZ_RANGE)
    package.frequency = to_frequency(mhz)
    events.update_flights_in_package(package)


def has_flight_tacan(flight: Flight) -> bool:
    """Only tankers with a beacon have a TACAN of their own (`QCommsEditor`)."""
    return bool(
        flight.flight_type is FlightType.REFUELING
        and flight.unit_type.dcs_unit_type.tacan
    )


def set_flight_tacan(
    flight: Flight,
    channel: Optional[int],
    band: Optional[str],
    callsign: Optional[str],
    events: GameUpdateEvents,
) -> None:
    """Sets the TACAN of the flight; no channel goes back to automatic, callsign too.

    Raises:
        CommandError: not a tanker with a beacon, or a value out of the limits.
    """
    if not has_flight_tacan(flight):
        raise CommandError("Only a tanker with a beacon has a TACAN channel to set.")
    check_channel("The TACAN channel", channel, TACAN_CHANNEL_RANGE)
    tacan = None if channel is None else TacanChannel(channel, tacan_band(band))
    tcn_name = clean_callsign("TACAN", callsign)
    flight.tacan = tacan
    flight.tcn_name = tcn_name if tacan is not None else None
    events.update_flight(flight)


def flight_radio_warnings(game: Game, flight: Flight) -> list[str]:
    return frequency_warnings(
        game,
        coalition_of(game, flight.package).player,
        "The flight frequency",
        flight.frequency,
        flight,
        shares_net_with=[flight.package],
    )


def package_radio_warnings(game: Game, package: Package) -> list[str]:
    return frequency_warnings(
        game,
        coalition_of(game, package).player,
        "The package frequency",
        package.frequency,
        package,
        shares_net_with=package.flights,
    )


def flight_tacan_warnings(game: Game, flight: Flight) -> list[str]:
    player = coalition_of(game, flight.package).player
    if flight.tacan is not None and flight.tacan in tacan_channels_in_use(
        game, flight, player
    ):
        return [f"TACAN {flight.tacan} is already in use: check this is intended."]
    return []


def datalink_of(flight: Flight) -> Optional[DataLinkKey]:
    """The datalink of this aircraft, or None when it has none to set."""
    key = DataLinkKey.from_aircraft_type(flight.unit_type)
    return None if key is DataLinkKey.Unknown else key


def datalink_fields(flight: Flight) -> list[DatalinkField]:
    """What each member of the flight sets on its datalink."""
    key = datalink_of(flight)
    if key is None:
        return []
    if key is DataLinkKey.IDM:
        lengths = {key.value: _IDM_ID_LENGTH, OWNSHIP_CALLSIGN: _OWNSHIP_LENGTH}
    else:
        lengths = {
            key.value: _STN_LENGTHS[key],
            VOICE_CALLSIGN_LABEL: _VOICE_CALLSIGN_LENGTH,
            VOICE_CALLSIGN_NUMBER: _VOICE_CALLSIGN_LENGTH,
        }
    properties = flight.unit_type.dcs_unit_type.properties
    return [
        DatalinkField(identifier, properties[identifier].label or identifier, length)
        for identifier, length in lengths.items()
        if identifier in properties
    ]


def _valid_idm_id(value: str) -> bool:
    if len(value) == 1:
        return value.isalnum()
    first, second = value[0], value[1]
    return (first in ("1", "2") and second.isalnum()) or (
        first == "3" and re.fullmatch(r"[A-I0-9]", second) is not None
    )


def _datalink_value(key: DataLinkKey, field: DatalinkField, value: str) -> str:
    """The rules of `PropertyEditBox`: refuses what it would not let be typed."""
    if len(value) > field.max_length:
        raise CommandError(f"{field.label} has {field.max_length} characters at most.")
    if field.identifier == VOICE_CALLSIGN_LABEL:
        valid = value.isalpha()
    elif field.identifier == VOICE_CALLSIGN_NUMBER:
        valid = value.isdigit()
    elif field.identifier == OWNSHIP_CALLSIGN:
        valid = re.fullmatch(r"[A-Z0-9/*\-+.]+", value) is not None
    elif key is DataLinkKey.IDM:
        valid = _valid_idm_id(value)
    else:
        if re.fullmatch(r"[0-7]+", value) is None:
            raise CommandError(f"{field.label} is an octal number.")
        return value.zfill(field.max_length)
    if not valid:
        raise CommandError(f"{value} is not a valid {field.label}.")
    return value


def set_datalink_value(
    flight: Flight,
    member_index: int,
    identifier: str,
    value: str,
    events: GameUpdateEvents,
) -> None:
    """Sets a datalink value of a flight member; empty goes back to automatic.

    Raises:
        CommandError: no such member (404), a field this aircraft does not have, or an
            invalid value.
    """
    members = list(flight.iter_members())
    if not 0 <= member_index < len(members):
        raise CommandError("This flight member no longer exists.", status_code=404)
    key = datalink_of(flight)
    field = next(
        (f for f in datalink_fields(flight) if f.identifier == identifier), None
    )
    if key is None or field is None:
        raise CommandError(f"{flight.unit_type} has no such datalink setting.")
    properties = members[member_index].properties
    cleaned = value.strip().upper()
    if cleaned == "":
        properties.pop(identifier, None)
    else:
        properties[identifier] = _datalink_value(key, field, cleaned)
    events.update_flight(flight)

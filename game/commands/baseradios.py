"""Frequency, TACAN, ICLS and Link 4 of a base (WEB-02.3).

The header of the Qt `QBaseMenu2` (`QFrequencyWidget`, `QTacanWidget`, `QICLSWidget`,
`QLink4Widget`) and the limits of their dialogs. A setting left to None is chosen
automatically at mission generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from game.dcs.beacons import Beacons
from game.radio.ICLSContainer import ICLSContainer
from game.radio.Link4Container import Link4Container
from game.radio.RadioFrequencyContainer import RadioFrequencyContainer
from game.radio.TacanContainer import TacanContainer
from game.radio.radios import RadioFrequency
from game.radio.tacan import TacanBand, TacanChannel
from game.theater.player import Player
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.sim import GameUpdateEvents
    from game.theater import ControlPoint

FREQUENCY_MHZ_RANGE = (30.0, 400.0)
LINK4_MHZ_RANGE = (225.0, 400.0)
TACAN_CHANNEL_RANGE = (1, 126)
ICLS_CHANNEL_RANGE = (1, 20)
CALLSIGN_LENGTH = 3
#: UHF and VHF guard: allowed, but worth a warning.
GUARD_FREQUENCIES_MHZ = (243.0, 121.5)


@dataclass(frozen=True)
class BaseRadios:
    frequency_mhz: Optional[float] = None
    tacan_channel: Optional[int] = None
    #: "X" or "Y".
    tacan_band: Optional[str] = None
    tacan_callsign: Optional[str] = None
    icls_channel: Optional[int] = None
    icls_callsign: Optional[str] = None
    link4_mhz: Optional[float] = None


def has_radios(cp: ControlPoint) -> bool:
    """A player base with at least one setting."""
    return cp.captured.is_blue and isinstance(
        cp, (RadioFrequencyContainer, TacanContainer, ICLSContainer)
    )


def base_radios(cp: ControlPoint) -> BaseRadios:
    frequency = cp.frequency if isinstance(cp, RadioFrequencyContainer) else None
    tacan = cp.tacan if isinstance(cp, TacanContainer) else None
    link4 = cp.link4 if isinstance(cp, Link4Container) else None
    return BaseRadios(
        frequency_mhz=frequency.mhz if frequency is not None else None,
        tacan_channel=tacan.number if tacan is not None else None,
        tacan_band=tacan.band.value if tacan is not None else None,
        tacan_callsign=cp.tcn_name if isinstance(cp, TacanContainer) else None,
        icls_channel=cp.icls_channel if isinstance(cp, ICLSContainer) else None,
        icls_callsign=cp.icls_name if isinstance(cp, ICLSContainer) else None,
        link4_mhz=link4.mhz if link4 is not None else None,
    )


def tacan_channels_in_use(game: Game, exclude: object = None) -> list[TacanChannel]:
    """Channels reserved by anything other than `exclude` itself.

    This always includes map beacon channels, even if `exclude`'s own current channel
    happens to share the same value (that's precisely the conflict to flag).
    """
    channels: set[TacanChannel] = set()
    for package in game.ato_for(Player.BLUE).packages:
        for flight in package.flights:
            if flight is not exclude and flight.tacan is not None:
                channels.add(flight.tacan)
    for cp in game.theater.control_points_for(Player.BLUE):
        if cp is not exclude and isinstance(cp, TacanContainer):
            if cp.tacan is not None:
                channels.add(cp.tacan)
    for beacon in Beacons.iter_theater(game.theater):
        if beacon.occupies_tacan_channel:
            if (channel := beacon.tacan_channel) is not None:
                channels.add(channel)
    return list(channels)


def radio_warnings(game: Game, cp: ControlPoint) -> list[str]:
    """What is allowed but worth checking, as the Qt widgets flag it."""
    settings = base_radios(cp)
    warnings = [
        f"{name} is on a guard frequency: check that this is intended."
        for name, mhz in (
            ("The base frequency", settings.frequency_mhz),
            ("Link 4", settings.link4_mhz),
        )
        if mhz in GUARD_FREQUENCIES_MHZ
    ]
    if isinstance(cp, TacanContainer) and cp.tacan in tacan_channels_in_use(game, cp):
        warnings.append(f"TACAN {cp.tacan} is already in use: check this is intended.")
    return warnings


def _check_mhz(name: str, mhz: Optional[float], limits: tuple[float, float]) -> None:
    if mhz is not None and not limits[0] <= mhz < limits[1]:
        raise CommandError(
            f"{name} must be from {limits[0]:g} MHz up to {limits[1]:g} MHz."
        )


def _check_channel(name: str, channel: Optional[int], limits: tuple[int, int]) -> None:
    if channel is not None and not limits[0] <= channel <= limits[1]:
        raise CommandError(f"{name} must be from {limits[0]} to {limits[1]}.")


def _callsign(name: str, callsign: Optional[str]) -> Optional[str]:
    if callsign is None or callsign == "":
        return None
    if len(callsign) > CALLSIGN_LENGTH:
        raise CommandError(
            f"The {name} callsign has {CALLSIGN_LENGTH} characters at most."
        )
    return callsign.upper()


def _tacan_band(band: Optional[str]) -> TacanBand:
    try:
        return TacanBand(band)
    except ValueError:
        raise CommandError("The TACAN band must be X or Y.")


def set_base_radios(
    cp: ControlPoint, radios: BaseRadios, events: GameUpdateEvents
) -> None:
    """Replaces every setting of the base, or none of them.

    A setting this base does not have must stay None. A callsign needs its channel and
    is dropped with it.

    Raises:
        CommandError: not a player base, a setting this base does not have, or a value
            out of the limits.
    """
    if not has_radios(cp):
        raise CommandError(f"{cp.name} has no radio settings you can change.")
    is_radio = isinstance(cp, RadioFrequencyContainer)
    is_tacan = isinstance(cp, TacanContainer)
    is_icls = isinstance(cp, ICLSContainer)
    is_link4 = isinstance(cp, Link4Container)
    for name, value, supported in (
        ("a frequency", radios.frequency_mhz, is_radio),
        ("a TACAN channel", radios.tacan_channel, is_tacan),
        ("an ICLS channel", radios.icls_channel, is_icls),
        ("a Link 4 frequency", radios.link4_mhz, is_link4),
    ):
        if value is not None and not supported:
            raise CommandError(f"{cp.name} cannot have {name}.")
    _check_mhz("The frequency", radios.frequency_mhz, FREQUENCY_MHZ_RANGE)
    _check_mhz("The Link 4 frequency", radios.link4_mhz, LINK4_MHZ_RANGE)
    _check_channel("The TACAN channel", radios.tacan_channel, TACAN_CHANNEL_RANGE)
    _check_channel("The ICLS channel", radios.icls_channel, ICLS_CHANNEL_RANGE)
    tacan = (
        TacanChannel(radios.tacan_channel, _tacan_band(radios.tacan_band))
        if radios.tacan_channel is not None
        else None
    )
    tacan_callsign = _callsign("TACAN", radios.tacan_callsign)
    icls_callsign = _callsign("ICLS", radios.icls_callsign)

    if isinstance(cp, RadioFrequencyContainer):
        cp.frequency = _frequency(radios.frequency_mhz)
    if isinstance(cp, TacanContainer):
        cp.tacan = tacan
        cp.tcn_name = tacan_callsign if tacan is not None else None
    if isinstance(cp, ICLSContainer):
        cp.icls_channel = radios.icls_channel
        cp.icls_name = icls_callsign if radios.icls_channel is not None else None
    if isinstance(cp, Link4Container):
        cp.link4 = _frequency(radios.link4_mhz)
    events.update_control_point(cp)


def _frequency(mhz: Optional[float]) -> Optional[RadioFrequency]:
    return RadioFrequency(hertz=round(mhz * 10**6)) if mhz is not None else None

"""The data cartridge settings of a flight's squadron (#221).

What the player sets in the Radios & TACAN tab of a flight: whether the jet loads the
cartridge at spawn, whether it adds the front lines and enemy air defenses, and the
CMDS programs. They are kept on the squadron, so every player flight of the squadron,
this turn and the next, gets the same cartridge; `apply_to_aircraft` copies them to
every squadron of the coalition that flies the same aircraft.
"""

from __future__ import annotations

from typing import Mapping, Optional, TYPE_CHECKING

from game.missiongenerator.dtc.cartridge import (
    cmds_schema,
    shows_threats,
    takes_cartridge,
)
from game.squadrons.dtcsettings import DtcSettings
from .errors import CommandError

if TYPE_CHECKING:
    from game.ato import Flight
    from game.missiongenerator.dtc.cmds import CmdsSchema
    from game.squadrons import Squadron

NO_CARTRIDGE = "This aircraft takes no data cartridge."


def unit_type_of(flight: Flight) -> str:
    return flight.squadron.aircraft.dcs_unit_type.id


def takes_settings(flight: Flight) -> bool:
    """Whether the flight's aircraft takes a cartridge the player can set."""
    return takes_cartridge(unit_type_of(flight))


def flight_cmds_schema(flight: Flight) -> Optional[CmdsSchema]:
    return cmds_schema(unit_type_of(flight))


def flight_shows_threats(flight: Flight) -> bool:
    return shows_threats(unit_type_of(flight))


def _settings(flight: Flight) -> DtcSettings:
    if not takes_settings(flight):
        raise CommandError(NO_CARTRIDGE)
    return flight.squadron.dtc


def set_cartridge_settings(
    flight: Flight,
    auto_load: Optional[bool] = None,
    threats: Optional[bool] = None,
    cmds: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> None:
    """Changes what is given; `cmds` replaces every program the player changed.

    The CMDS values are checked against the limits of the module's editor and only
    those that differ from its defaults are kept.
    """
    settings = _settings(flight)
    cleaned = None
    if cmds is not None:
        schema = flight_cmds_schema(flight)
        if schema is None:
            raise CommandError("This aircraft has no CMDS programs to set.")
        try:
            cleaned = schema.clean(cmds)
        except ValueError as error:
            raise CommandError(str(error)) from error
    if auto_load is not None:
        settings.auto_load = auto_load
    if threats is not None:
        settings.threats = threats
    if cleaned is not None:
        settings.cmds = cleaned


def reset_cartridge_settings(flight: Flight) -> None:
    """Back to the module's defaults, loaded at spawn."""
    _settings(flight)
    flight.squadron.dtc = DtcSettings()


def squadrons_flying_the_same(flight: Flight) -> list[Squadron]:
    """The other squadrons of the coalition that fly the aircraft of `flight`."""
    unit_type = unit_type_of(flight)
    own = flight.squadron
    return [
        squadron
        for squadron in own.coalition.air_wing.iter_squadrons()
        if squadron is not own and squadron.aircraft.dcs_unit_type.id == unit_type
    ]


def apply_to_aircraft(flight: Flight) -> int:
    """Copies the settings to the other squadrons of the aircraft; how many."""
    settings = _settings(flight)
    others = squadrons_flying_the_same(flight)
    for squadron in others:
        squadron.dtc = settings.copy()
    return len(others)

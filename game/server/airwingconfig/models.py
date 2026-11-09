"""DTOs of the air wing configuration (WEB-06), the Qt `AirWingConfigurationDialog`."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.ato.flighttype import FlightType
from game.commands.airwingconfig import (
    parking_at_base,
    player_names,
    player_names_refusal,
    possible_aircraft,
    possible_bases,
    presets_for,
    primary_tasks,
)
from game.commands.preferences import is_player_module
from ..airwing.models import AllowedTaskJs

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.dcs.aircrafttype import AircraftType
    from game.squadrons import Squadron


class ConfigBaseJs(BaseModel):
    id: UUID
    name: str

    class Config:
        title = "AirWingConfigBase"


class ConfigParkingJs(BaseModel):
    required: int
    total: int
    fitting: Optional[int]

    class Config:
        title = "AirWingConfigParking"


class ConfigSquadronJs(BaseModel):
    id: UUID
    name: str
    nickname: Optional[str]
    aircraft: str
    aircraft_id: str
    primary_task: str
    primary_tasks: list[str]
    #: Tasks the squadron can fly, with whether the autoplanner may use it for them.
    tasks: list[AllowedTaskJs]
    max_size: int
    base_id: UUID
    bases: list[ConfigBaseJs]
    parking: ConfigParkingJs
    player_names: list[str]
    #: Why it cannot have player pilots; null when it can.
    player_names_refusal: Optional[str]
    #: Unclaimed presets that could replace it.
    presets: list[str]

    class Config:
        title = "AirWingConfigSquadron"

    @staticmethod
    def for_squadron(game: Game, squadron: Squadron) -> ConfigSquadronJs:
        coalition = squadron.coalition
        parking = parking_at_base(game, squadron)
        return ConfigSquadronJs(
            id=squadron.id,
            name=squadron.name,
            nickname=squadron.nickname,
            aircraft=squadron.aircraft.display_name,
            aircraft_id=squadron.aircraft.variant_id,
            primary_task=squadron.primary_task.value,
            primary_tasks=[t.value for t in primary_tasks(squadron.aircraft)],
            tasks=[
                AllowedTaskJs(
                    task=task.value,
                    auto_assign=task in squadron.auto_assignable_mission_types,
                )
                for task in FlightType
                if task is not FlightType.FERRY and squadron.capable_of(task)
            ],
            max_size=squadron.max_size,
            base_id=squadron.location.id,
            bases=[
                ConfigBaseJs(id=base.id, name=base.name)
                for base in possible_bases(coalition, squadron.aircraft)
            ],
            parking=ConfigParkingJs(
                required=parking.required,
                total=parking.total,
                fitting=parking.fitting,
            ),
            player_names=player_names(squadron),
            player_names_refusal=player_names_refusal(squadron),
            presets=[d.name for d in presets_for(coalition, squadron.aircraft)],
        )


class ConfigAircraftOptionJs(BaseModel):
    """What a new squadron of this aircraft can be."""

    aircraft_id: str
    aircraft: str
    #: The player owns the module: listed first, on the player's side only.
    player_module: bool
    #: Squadrons of this aircraft the coalition already has.
    squadron_count: int
    primary_tasks: list[str]
    bases: list[ConfigBaseJs]
    presets: list[str]

    class Config:
        title = "AirWingConfigAircraftOption"


class ConfigSideJs(BaseModel):
    #: "blue" or "red".
    side: str
    faction: str
    squadrons: list[ConfigSquadronJs]
    aircraft_options: list[ConfigAircraftOptionJs]

    class Config:
        title = "AirWingConfigSide"

    @staticmethod
    def for_coalition(game: Game, side: str, coalition: Coalition) -> ConfigSideJs:
        def is_own(aircraft: AircraftType) -> bool:
            return coalition.player.is_blue and is_player_module(aircraft)

        return ConfigSideJs(
            side=side,
            faction=coalition.faction.name,
            squadrons=[
                ConfigSquadronJs.for_squadron(game, squadron)
                for squadron in sorted(
                    coalition.air_wing.iter_squadrons(),
                    key=lambda s: (s.aircraft.display_name, s.name),
                )
            ],
            aircraft_options=[
                ConfigAircraftOptionJs(
                    aircraft_id=aircraft.variant_id,
                    aircraft=aircraft.display_name,
                    player_module=is_own(aircraft),
                    squadron_count=len(coalition.air_wing.squadrons.get(aircraft, [])),
                    primary_tasks=[t.value for t in primary_tasks(aircraft)],
                    bases=[
                        ConfigBaseJs(id=base.id, name=base.name)
                        for base in possible_bases(coalition, aircraft)
                    ],
                    presets=[d.name for d in presets_for(coalition, aircraft)],
                )
                for aircraft in sorted(
                    possible_aircraft(coalition), key=lambda a: not is_own(a)
                )
            ],
        )


class AirWingConfigJs(BaseModel):
    #: A running campaign replans its turn when squadrons move, appear or leave.
    replans: bool
    sides: list[ConfigSideJs]

    class Config:
        title = "AirWingConfig"


class SquadronConfigUpdateJs(BaseModel):
    """What to change; the others stay."""

    name: Optional[str] = None
    nickname: Optional[str] = None
    max_size: Optional[int] = None
    primary_task: Optional[str] = None
    base_id: Optional[UUID] = None
    player_names: Optional[list[str]] = None

    class Config:
        title = "SquadronConfigUpdate"


class ConfigRemoveAircraftJs(BaseModel):
    """Every squadron of this aircraft goes (#206)."""

    aircraft_id: str

    class Config:
        title = "AirWingConfigRemoveAircraft"


class ConfigNewSquadronJs(BaseModel):
    aircraft_id: str
    base_id: UUID
    primary_task: str
    #: One of the presets of the option; null generates a squadron.
    preset: Optional[str] = None

    class Config:
        title = "AirWingConfigNewSquadron"


class ReplacePresetJs(BaseModel):
    preset: str

    class Config:
        title = "AirWingConfigReplacePreset"


class FactionUnitJs(BaseModel):
    group: str
    unit: str

    class Config:
        title = "AirWingConfigFactionUnit"


class FactionJtacJs(BaseModel):
    has_jtac: bool

    class Config:
        title = "AirWingConfigFactionJtac"


class FactionDoctrineJs(BaseModel):
    doctrine: str

    class Config:
        title = "AirWingConfigFactionDoctrine"


class AirWingFileResultJs(BaseModel):
    #: The file, or null when the player cancelled the dialog.
    path: Optional[str]

    class Config:
        title = "AirWingFileResult"

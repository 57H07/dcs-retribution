"""What the Payload tab of the package editor shows (WEB-04.3)."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from pydantic import BaseModel

from game.ato.flightmember import FlightMember
from game.ato.loadouts import Loadout
from game.commands.flightpayload import (
    PropertyControl,
    effective_loadout,
    max_fuel,
    member_livery_choices,
    named_loadouts,
    property_controls,
    property_value,
    property_value_ids,
    pylon_options,
    visible_weapon_settings,
    weapon_laser_code_choices,
    weapon_name,
)
from game.data.weapons import Weapon
from ..airwing.models import LiveryChoiceJs

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight


class PayloadWeaponJs(BaseModel):
    clsid: str
    name: str

    class Config:
        title = "PayloadWeapon"

    @staticmethod
    def for_weapon(weapon: Weapon) -> PayloadWeaponJs:
        return PayloadWeaponJs(clsid=weapon.clsid, name=weapon_name(weapon))


class PayloadPylonOptionsJs(BaseModel):
    number: int
    #: What the pylon accepts, within the date restriction if it is on.
    weapons: list[PayloadWeaponJs]

    class Config:
        title = "PayloadPylonOptions"


class PayloadOptionJs(BaseModel):
    id: bool | int | float | str | None
    label: str

    class Config:
        title = "PayloadOption"


class WeaponSettingJs(BaseModel):
    id: str
    label: str
    #: "comboList", "spinbox" or "doubleSpinbox".
    control: str
    value: bool | int | float | str | None
    read_only: bool
    minimum: float | None
    maximum: float | None
    unit: str | None
    options: list[PayloadOptionJs]

    class Config:
        title = "WeaponSetting"


class MemberPylonJs(BaseModel):
    number: int
    #: What the member flies: the stored weapon, or what the date restriction leaves.
    weapon: PayloadWeaponJs | None
    #: The stored weapon when the date restriction replaced it.
    replaced_weapon: str | None
    #: Empty unless the loadout is custom and the weapon has settings.
    settings: list[WeaponSettingJs]

    class Config:
        title = "MemberPylon"


class WeaponLaserCodeJs(BaseModel):
    code: int | None
    label: str

    class Config:
        title = "WeaponLaserCode"


class MemberPayloadJs(BaseModel):
    index: int
    pilot: str | None
    is_player: bool
    loadout: str
    custom: bool
    pylons: list[MemberPylonJs]
    tgp_laser_code: int | None
    weapon_laser_code: int | None
    #: Empty for an AI member: it does not use laser codes.
    weapon_laser_codes: list[WeaponLaserCodeJs]
    liveries: list[LiveryChoiceJs]
    #: Value of each mission option, by id.
    properties: dict[str, bool | int | float | str | None]

    class Config:
        title = "MemberPayload"


class PayloadPropertyJs(BaseModel):
    id: str
    label: str
    #: "checkbox", "comboList", "spinbox", "slider" or "editbox".
    control: str
    #: The group this option belongs to.
    section: str | None
    minimum: int | None
    maximum: int | None
    options: list[PayloadOptionJs]

    class Config:
        title = "PayloadProperty"


class FlightPayloadJs(BaseModel):
    aircraft: str
    #: Internal fuel, in kg.
    fuel: int
    fuel_max: int
    same_loadout: bool
    same_livery: bool
    restrict_weapons_by_date: bool
    #: Campaign date the restriction applies to.
    date: str
    #: Named loadouts of the aircraft.
    loadouts: list[str]
    pylons: list[PayloadPylonOptionsJs]
    properties: list[PayloadPropertyJs]
    members: list[MemberPayloadJs]

    class Config:
        title = "FlightPayload"

    @staticmethod
    def for_flight(game: Game, flight: Flight) -> FlightPayloadJs:
        options = pylon_options(game, flight)
        controls = property_controls(flight)
        return FlightPayloadJs(
            aircraft=str(flight.unit_type),
            fuel=min(round(flight.fuel), max_fuel(flight)),
            fuel_max=max_fuel(flight),
            same_loadout=flight.use_same_loadout_for_all_members,
            same_livery=flight.use_same_livery_for_all_members,
            restrict_weapons_by_date=game.settings.restrict_weapons_by_date,
            date=game.date.isoformat(),
            loadouts=list(named_loadouts(flight.unit_type)),
            pylons=[
                PayloadPylonOptionsJs(
                    number=number,
                    weapons=[PayloadWeaponJs.for_weapon(w) for w in weapons],
                )
                for number, weapons in options.items()
            ],
            properties=[_property(game, flight, control) for control in controls],
            members=[
                _member(game, flight, index, member, list(options), controls)
                for index, member in enumerate(flight.roster.members)
            ],
        )


def _property(
    game: Game, flight: Flight, control: PropertyControl
) -> PayloadPropertyJs:
    prop = control.prop
    values = prop.values or {}
    return PayloadPropertyJs(
        id=prop.identifier,
        label=prop.label or prop.identifier,
        control=prop.control,
        section=control.section,
        minimum=prop.minimum,
        maximum=prop.maximum,
        options=[
            PayloadOptionJs(id=value, label=values[value])
            for value in property_value_ids(game, flight, prop)
        ],
    )


def _setting_option(option: dict[str, Any]) -> PayloadOptionJs:
    return PayloadOptionJs(id=option["id"], label=option["dispName"])


def _member_pylon(member: FlightMember, shown: Loadout, number: int) -> MemberPylonJs:
    weapon = shown.pylons.get(number)
    stored = member.loadout.pylons.get(number)
    settings = []
    if member.loadout.is_custom and weapon is not None and weapon == stored:
        settings = [
            WeaponSettingJs(
                id=setting.id,
                label=setting.label,
                control=setting.control,
                value=setting.current_value,
                read_only=setting.read_only,
                minimum=setting.min_value,
                maximum=setting.max_value,
                unit=setting.dimension or None,
                options=[_setting_option(option) for option in setting.values],
            )
            for setting in visible_weapon_settings(
                weapon, member.loadout.pylon_settings.get(number)
            )
        ]
    return MemberPylonJs(
        number=number,
        weapon=None if weapon is None else PayloadWeaponJs.for_weapon(weapon),
        replaced_weapon=(
            weapon_name(stored) if stored is not None and stored != weapon else None
        ),
        settings=settings,
    )


def _laser_codes(game: Game, member: FlightMember) -> list[WeaponLaserCodeJs]:
    if not member.is_player:
        return []
    return [
        WeaponLaserCodeJs(
            code=None if choice.code is None else choice.code.code, label=choice.label
        )
        for choice in weapon_laser_code_choices(game, member)
    ]


def _member(
    game: Game,
    flight: Flight,
    index: int,
    member: FlightMember,
    pylon_numbers: list[int],
    controls: list[PropertyControl],
) -> MemberPayloadJs:
    shown = effective_loadout(game, flight, member)
    weapon_code = member.weapon_laser_code
    tgp_code = member.tgp_laser_code
    return MemberPayloadJs(
        index=index,
        pilot=None if member.pilot is None else member.pilot.name,
        is_player=member.is_player,
        loadout=member.loadout.name,
        custom=member.loadout.is_custom,
        pylons=[_member_pylon(member, shown, n) for n in pylon_numbers],
        tgp_laser_code=None if tgp_code is None else tgp_code.code,
        weapon_laser_code=None if weapon_code is None else weapon_code.code,
        weapon_laser_codes=_laser_codes(game, member),
        liveries=[
            LiveryChoiceJs.from_choice(choice)
            for choice in member_livery_choices(flight, member)
        ],
        properties={
            control.prop.identifier: property_value(game, flight, member, control.prop)
            for control in controls
        },
    )


class FlightFuelJs(BaseModel):
    fuel: int

    class Config:
        title = "FlightFuel"


class SameForAllJs(BaseModel):
    same: bool

    class Config:
        title = "SameForAll"


class MemberLoadoutNameJs(BaseModel):
    name: str

    class Config:
        title = "MemberLoadoutName"


class MemberCustomLoadoutJs(BaseModel):
    custom: bool

    class Config:
        title = "MemberCustomLoadout"


class MemberPylonWeaponJs(BaseModel):
    #: None empties the pylon.
    clsid: Optional[str] = None

    class Config:
        title = "MemberPylonWeapon"


class PayloadValueJs(BaseModel):
    id: str
    value: bool | int | float | str | None = None

    class Config:
        title = "PayloadValue"


class TgpLaserCodeJs(BaseModel):
    assigned: bool

    class Config:
        title = "TgpLaserCode"


class WeaponLaserCodeChoiceJs(BaseModel):
    #: None is the default code.
    code: Optional[int] = None

    class Config:
        title = "WeaponLaserCodeChoice"


class MemberLiveryJs(BaseModel):
    livery_id: Optional[str] = None
    use_livery_set: bool = False

    class Config:
        title = "MemberLivery"


class SavePayloadJs(BaseModel):
    name: str

    class Config:
        title = "SavePayload"


class PayloadFileJs(BaseModel):
    """Where the file went, for the player to find it. None: nothing to back up."""

    path: str | None

    class Config:
        title = "PayloadFile"

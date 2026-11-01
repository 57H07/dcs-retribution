"""Payload of a flight (WEB-04.3), shared by the web editor and Qt.

The rules of `qt_ui/windows/mission/flight/payload/`. A Qt widget could not offer what a
rule forbids; here the command refuses it, since the web editor has no save step.

Two facts the editor must keep straight:

* The stored loadout is not always what flies. With "restrict weapons by date" on, the
  mission generator degrades it (`Loadout.degrade_for_date`), so the editor shows
  `effective_loadout` and leaves the stored one alone until the player customizes it.
* Members of a flight with "same loadout for all" share one `Loadout` object: an edit
  of the first member is an edit of all (`FlightMembers.use_same_loadout_for_all_members`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from shutil import copyfile
from typing import Any, Optional, TYPE_CHECKING, Union

from dcs import lua
from dcs.unitpropertydescription import UnitPropertyDescription
from dcs.weapon_settings import WeaponSetting

from game.ato.flightmember import FlightMember
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon
from game.persistency import payloads_dir
from game.radio.datalink import (
    DataLinkKey,
    OWNSHIP_CALLSIGN,
    VOICE_CALLSIGN_LABEL,
    VOICE_CALLSIGN_NUMBER,
)
from .errors import CommandError
from .packageflights import default_loadout
from .squadrons import LiveryChoice, livery_choices

if TYPE_CHECKING:
    from game import Game
    from game.ato.flight import Flight
    from game.dcs.aircrafttype import AircraftType
    from game.lasercodes import LaserCode

CLEAN_CLSID = "<CLEAN>"

#: The form cannot show a range this wide (see `QWeaponSettingsDialog`).
MAX_WEAPON_SETTING_VALUE = 1000000000000

WEAPON_SETTING_CONTROLS = frozenset({"comboList", "spinbox", "doubleSpinbox"})

PropertyValue = Union[bool, float, int, str, None]

#: These options belong to the Radios tab and its rules (WEB-04.5).
DATALINK_PROPERTY_IDS = frozenset(
    {
        DataLinkKey.LINK16.value,
        DataLinkKey.SADL.value,
        DataLinkKey.IDM.value,
        OWNSHIP_CALLSIGN,
        VOICE_CALLSIGN_LABEL,
        VOICE_CALLSIGN_NUMBER,
    }
)


def require_member(flight: Flight, index: int) -> FlightMember:
    members = flight.roster.members
    if not 0 <= index < len(members):
        raise CommandError("This flight member no longer exists.", status_code=404)
    return members[index]


def weapon_name(weapon: Weapon) -> str:
    """Its name; a CLSID of `resources/weapons` that pydcs does not know has none."""
    try:
        return weapon.name
    except KeyError:
        return weapon.clsid


# --- what the editor shows ----------------------------------------------------------


def effective_loadout(game: Game, flight: Flight, member: FlightMember) -> Loadout:
    """What this member flies, as far as the player can see it.

    The mission generator also applies target overrides to weapon settings; they do not
    change the weapons, and they are computed again at each generation.
    """
    if not game.settings.restrict_weapons_by_date:
        return member.loadout
    return member.loadout.degrade_for_date(
        flight.unit_type, game.date, flight.squadron.coalition.faction
    )


def named_loadouts(aircraft: AircraftType) -> dict[str, Loadout]:
    """The loadouts of this aircraft by name, sorted. The objects are new at each call."""
    loadouts: dict[str, Loadout] = {}
    for loadout in Loadout.iter_for_aircraft(aircraft):
        loadouts.setdefault(loadout.name, loadout)
    return dict(sorted(loadouts.items(), key=lambda item: item[0].casefold()))


def pylon_options(game: Game, flight: Flight) -> dict[int, list[Weapon]]:
    """What each pylon of the aircraft can be given now, by pylon number.

    Only what pydcs lists for the pylon, within the date restriction. pydcs does not
    know "Clean" as a weapon, so it is offered on the pylons where a loadout uses it
    (see `Pylon.can_equip`).
    """
    faction = flight.squadron.coalition.faction
    clean = Weapon.with_clsid(CLEAN_CLSID)
    seen_clean: set[int] = set()
    known_loadouts = [
        *Loadout.iter_for_aircraft(flight.unit_type),
        *(member.loadout for member in flight.roster.members),
    ]
    for loadout in known_loadouts:
        seen_clean.update(
            number
            for number, weapon in loadout.pylons.items()
            if weapon is not None and weapon.clsid == CLEAN_CLSID
        )

    options: dict[int, list[Weapon]] = {}
    for pylon in Pylon.iter_pylons(flight.unit_type):
        weapons = list(
            pylon.available_on(game.date, faction)
            if game.settings.restrict_weapons_by_date
            else pylon.allowed
        )
        if pylon.number in seen_clean and clean is not None and clean not in weapons:
            weapons.append(clean)
        # Several CLSIDs can share a name: the order must not depend on set order.
        options[pylon.number] = sorted(weapons, key=lambda w: (weapon_name(w), w.clsid))
    return options


def visible_weapon_settings(
    weapon: Weapon, stored: Optional[dict[str, Any]]
) -> list[WeaponSetting]:
    """The settings the form shows for this weapon, given the stored values."""
    if not weapon.has_settings():
        return []
    settings = weapon.create_settings(stored)
    if settings is None:
        return []
    return [
        setting
        for setting in settings.get_visible_settings()
        if setting.control in WEAPON_SETTING_CONTROLS
        and not (
            setting.max_value is not None
            and setting.max_value >= MAX_WEAPON_SETTING_VALUE
        )
    ]


# --- loadouts -----------------------------------------------------------------------


def _require_loadout_editable(flight: Flight, member: FlightMember) -> None:
    if (
        flight.use_same_loadout_for_all_members
        and member is not flight.roster.members[0]
    ):
        raise CommandError(
            "All members share one loadout: edit the first member, or give each "
            "member its own."
        )


def _require_custom(flight: Flight, member: FlightMember) -> None:
    _require_loadout_editable(flight, member)
    if not member.loadout.is_custom:
        raise CommandError("Turn on the custom loadout to edit its pylons.")


def _share_loadout_if_needed(flight: Flight) -> None:
    """Members added by a resize hold a clone: an edit must reach them too."""
    if not flight.use_same_loadout_for_all_members:
        return
    flight.roster.use_same_loadout_for_all_members()
    for member in flight.roster.members:
        member.use_custom_loadout = member.loadout.is_custom


def assign_loadout(flight: Flight, member: FlightMember, loadout: Loadout) -> None:
    member.loadout = loadout
    _share_loadout_if_needed(flight)


def set_member_loadout(flight: Flight, member: FlightMember, name: str) -> None:
    """Picks one of the aircraft's named loadouts."""
    _require_loadout_editable(flight, member)
    if member.loadout.is_custom:
        raise CommandError("Turn off the custom loadout to choose a named one.")
    if member.loadout.name == name:
        return
    loadout = named_loadouts(flight.unit_type).get(name)
    if loadout is None:
        raise CommandError(f"{flight.unit_type} has no loadout named {name}.")
    assign_loadout(flight, member, loadout)


def set_member_custom(
    game: Game,
    flight: Flight,
    member: FlightMember,
    custom: bool,
    named: Optional[Loadout] = None,
) -> None:
    """Custom starts from what the member flies now. Leaving it goes back to `named`,
    by default the loadout a new flight of this task gets."""
    _require_loadout_editable(flight, member)
    if custom != member.loadout.is_custom:
        if custom:
            shown = effective_loadout(game, flight, member)
            # The date of the stored loadout, not the degraded one: a loadout dated
            # today would skip the target overrides at mission generation.
            member.loadout = Loadout(
                "Custom",
                shown.pylons,
                member.loadout.date,
                is_custom=True,
                pylon_settings=dict(shown.pylon_settings),
            )
        else:
            member.loadout = named or default_loadout(
                flight.unit_type, flight.flight_type
            )
    member.use_custom_loadout = custom
    _share_loadout_if_needed(flight)


def equip_pylon(loadout: Loadout, number: int, weapon: Optional[Weapon]) -> None:
    """Settings belong to the weapon they were set on. None empties the pylon."""
    loadout.pylons[number] = weapon
    loadout.pylon_settings.pop(number, None)


def set_member_pylon(
    game: Game,
    flight: Flight,
    member: FlightMember,
    number: int,
    clsid: Optional[str],
) -> None:
    _require_custom(flight, member)
    options = pylon_options(game, flight)
    if number not in options:
        raise CommandError(f"{flight.unit_type} has no pylon {number}.")
    weapon = None
    if clsid is not None:
        weapon = next((w for w in options[number] if w.clsid == clsid), None)
        if weapon is None:
            raise CommandError(f"Pylon {number} cannot carry this weapon now.")
    if member.loadout.pylons.get(number) != weapon:
        equip_pylon(member.loadout, number, weapon)
    _share_loadout_if_needed(flight)


def set_same_loadout(flight: Flight, same: bool) -> None:
    """Sharing again gives everyone the loadout of the first member."""
    flight.use_same_loadout_for_all_members = same
    if same:
        _share_loadout_if_needed(flight)
    else:
        flight.roster.use_distinct_loadouts_for_each_member()


# --- weapon settings ----------------------------------------------------------------


def _configurable_weapon(flight: Flight, member: FlightMember, number: int) -> Weapon:
    _require_custom(flight, member)
    weapon = member.loadout.pylons.get(number)
    if weapon is None or not weapon.has_settings():
        raise CommandError(f"The weapon on pylon {number} has no settings.")
    return weapon


def set_weapon_setting(
    flight: Flight, member: FlightMember, number: int, setting_id: str, value: Any
) -> None:
    weapon = _configurable_weapon(flight, member, number)
    stored = member.loadout.pylon_settings.get(number)
    setting = next(
        (s for s in visible_weapon_settings(weapon, stored) if s.id == setting_id),
        None,
    )
    if setting is None or setting.read_only:
        raise CommandError("This weapon setting cannot be changed.")
    settings = weapon.create_settings(stored)
    assert settings is not None
    try:
        settings.set_value(setting_id, value)
    except (TypeError, ValueError) as ex:
        raise CommandError(f"{setting.label}: invalid value.") from ex
    # A new dict: a derived loadout may still share the old one.
    member.loadout.pylon_settings[number] = settings.to_dict()
    _share_loadout_if_needed(flight)


def reset_weapon_settings(flight: Flight, member: FlightMember, number: int) -> None:
    weapon = _configurable_weapon(flight, member, number)
    settings = weapon.create_settings()
    assert settings is not None
    member.loadout.pylon_settings[number] = settings.to_dict()
    _share_loadout_if_needed(flight)


# --- fuel ---------------------------------------------------------------------------


def max_fuel(flight: Flight) -> int:
    return int(flight.unit_type.dcs_unit_type.fuel_max)


def set_flight_fuel(flight: Flight, fuel: int) -> None:
    if not 0 <= fuel <= max_fuel(flight):
        raise CommandError(f"Internal fuel is 0 to {max_fuel(flight)} kg.")
    flight.fuel = fuel


# --- liveries -----------------------------------------------------------------------


def member_livery_choices(flight: Flight, member: FlightMember) -> list[LiveryChoice]:
    """The liveries of the squadron, with the member's one selected.

    Without a choice of its own, a member shows the squadron's.
    """
    choices = livery_choices(flight.squadron)
    if not any(_is_member_livery(choice, member) for choice in choices):
        return choices
    return [
        replace(choice, selected=_is_member_livery(choice, member))
        for choice in choices
    ]


def _is_member_livery(choice: LiveryChoice, member: FlightMember) -> bool:
    return (
        choice.livery_id == member.livery
        and choice.use_livery_set == member.use_livery_set
    )


def apply_member_livery(
    flight: Flight,
    member: FlightMember,
    livery_id: Optional[str],
    use_livery_set: bool,
) -> None:
    members = (
        flight.roster.members if flight.use_same_livery_for_all_members else [member]
    )
    for target in members:
        target.livery = livery_id
        target.use_livery_set = use_livery_set


def set_member_livery(
    flight: Flight,
    member: FlightMember,
    livery_id: Optional[str],
    use_livery_set: bool,
) -> None:
    if (
        flight.use_same_livery_for_all_members
        and member is not flight.roster.members[0]
    ):
        raise CommandError(
            "All members share one livery: edit the first member, or give each "
            "member its own."
        )
    if not any(
        choice.livery_id == livery_id and choice.use_livery_set == use_livery_set
        for choice in livery_choices(flight.squadron)
    ):
        raise CommandError(f"{flight.squadron.name} cannot use this livery.")
    apply_member_livery(flight, member, livery_id, use_livery_set)


def set_same_livery(flight: Flight, same: bool) -> None:
    flight.use_same_livery_for_all_members = same
    if same:
        flight.roster.use_same_livery_for_all_members()


# --- laser codes --------------------------------------------------------------------


def set_tgp_laser_code(game: Game, member: FlightMember, assigned: bool) -> None:
    """Allocates the member's own code for its targeting pod, or releases it."""
    if assigned == (member.tgp_laser_code is not None):
        return
    if not assigned:
        member.release_tgp_laser_code()
        return
    if not member.is_player:
        raise CommandError("AI does not use laser codes.")
    member.assign_tgp_laser_code(game.laser_code_registry.alloc_laser_code())


@dataclass(frozen=True)
class WeaponLaserCodeChoice:
    label: str
    #: None is the default code.
    code: Optional[LaserCode]


def weapon_laser_code_choices(
    game: Game, member: FlightMember
) -> list[WeaponLaserCodeChoice]:
    choices = [WeaponLaserCodeChoice("Default (1688)", None)]
    if (own := member.tgp_laser_code) is not None:
        choices.append(WeaponLaserCodeChoice(f"Use own code ({own})", own))
    choices.extend(
        WeaponLaserCodeChoice(
            f"JTAC {front.name} ({front.laser_code})", front.laser_code
        )
        for front in game.theater.conflicts()
    )
    return choices


def set_weapon_laser_code(
    game: Game, member: FlightMember, code: Optional[int]
) -> None:
    """Weapons are preset to this code at mission start. None is the default."""
    if not member.is_player:
        raise CommandError("AI does not use laser codes.")
    for choice in weapon_laser_code_choices(game, member):
        if (None if choice.code is None else choice.code.code) == code:
            member.weapon_laser_code = choice.code
            return
    raise CommandError(f"Laser code {code} is not available.")


# --- aircraft options ("properties") ------------------------------------------------


@dataclass(frozen=True)
class PropertyControl:
    prop: UnitPropertyDescription
    #: The label heading the group this control belongs to.
    section: Optional[str]


def _has_control_data(prop: UnitPropertyDescription) -> bool:
    if prop.control == "editbox":
        return True
    if prop.default is None:
        return False
    if prop.control == "comboList":
        return prop.values is not None
    if prop.control in ("slider", "spinbox"):
        return prop.minimum is not None and prop.maximum is not None
    return prop.control == "checkbox"


def property_controls(flight: Flight) -> list[PropertyControl]:
    """The aircraft options the editor shows for this flight."""
    controls = []
    section = None
    for prop in flight.unit_type.iter_props():
        if prop.label is None:
            if prop.control != "label":
                logging.error("Found non-label aircraft property with no display name.")
            continue
        if prop.player_only and not flight.client_count:
            continue
        if not flight.unit_type.should_show_prop(prop.identifier):
            continue
        if prop.identifier in DATALINK_PROPERTY_IDS:
            continue
        if prop.control in ("groupbox", "label"):
            section = prop.label
        elif _has_control_data(prop):
            controls.append(PropertyControl(prop, section))
        else:
            logging.error(
                "Cannot create property control for property %s of %s",
                prop.identifier,
                flight.unit_type,
            )
    return controls


def property_value_ids(
    game: Game, flight: Flight, prop: UnitPropertyDescription
) -> list[Union[str, int, float, None]]:
    """The values a list property offers, within the date restriction."""
    if game.settings.restrict_props_by_date:
        return flight.unit_type.property_date_gate.available_value_ids(prop, game.date)
    return list(prop.values or {})


def property_value(
    game: Game, flight: Flight, member: FlightMember, prop: UnitPropertyDescription
) -> PropertyValue:
    """The value of this option for the member. A list value out of period shows what
    flies; storage is left alone, and the mission generator clamps it the same way."""
    value = member.properties.get(prop.identifier, prop.default)
    if prop.control == "comboList" and game.settings.restrict_props_by_date:
        return flight.unit_type.property_date_gate.period_correct_value(
            prop, value, game.date
        )
    return value


def set_member_property(
    game: Game,
    flight: Flight,
    member: FlightMember,
    prop_id: str,
    value: PropertyValue,
) -> None:
    prop = next(
        (c.prop for c in property_controls(flight) if c.prop.identifier == prop_id),
        None,
    )
    if prop is None:
        raise CommandError("This flight does not have this option.")
    invalid = CommandError(f"{prop.label}: invalid value.")
    if prop.control == "checkbox":
        if not isinstance(value, bool):
            raise invalid
    elif prop.control == "comboList":
        offered = property_value_ids(game, flight, prop)
        if value not in offered:
            raise invalid
        value = offered[offered.index(value)]
    elif prop.control == "editbox":
        if not isinstance(value, str):
            raise invalid
        if not value:
            member.properties.pop(prop_id, None)
            return
    else:
        assert prop.minimum is not None and prop.maximum is not None
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not prop.minimum <= value <= prop.maximum
        ):
            raise invalid
    assert value is not None
    member.properties[prop_id] = value


# --- payload files ------------------------------------------------------------------


def _payload_table(member: FlightMember, name: str) -> dict[str, Any]:
    """The table of a payload in a DCS `UnitPayloads` file."""
    pylons: dict[int, dict[str, Any]] = {}
    for index, (number, weapon) in enumerate(member.loadout.pylons.items(), 1):
        pylon: dict[str, Any] = {
            "CLSID": weapon.clsid if weapon else CLEAN_CLSID,
            "num": number,
        }
        if settings := member.loadout.pylon_settings.get(number):
            pylon["settings"] = settings
        pylons[index] = pylon
    return {"displayName": name, "name": name, "pylons": pylons, "tasks": {1: 31}}


def _write_payload_file(path: Path, table: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        file.write("local unitPayloads = ")
        file.write(lua.dumps(table, indent=1))
        file.write("\nreturn unitPayloads")


def backup_payload_file(flight: Flight) -> Optional[Path]:
    """Copies the aircraft's payload file to the backups. None if it has no file yet."""
    aircraft_id = flight.unit_type.dcs_unit_type.id
    payload_file = payloads_dir() / f"{aircraft_id}.lua"
    if not payload_file.exists():
        return None
    backup_file = payloads_dir(backup=True) / f"{aircraft_id}.lua"
    try:
        copyfile(payload_file, backup_file)
    except OSError as ex:
        raise CommandError(f"Could not back up: {ex}", status_code=500) from ex
    return backup_file


def save_member_payload(flight: Flight, member: FlightMember, name: str) -> Path:
    """Saves the custom loadout as a named payload, in the DCS user folder.

    It joins the named loadouts of the aircraft. A payload of this name is replaced; the
    file is backed up once before its first change.
    """
    _require_custom(flight, member)
    name = name.strip()
    if not name:
        raise CommandError("Give the payload a name.")
    aircraft = flight.unit_type.dcs_unit_type
    aircraft_id = aircraft.id
    payload_file = payloads_dir() / f"{aircraft_id}.lua"
    aircraft.load_payloads()
    table = _payload_table(member, name)
    try:
        existing = None
        if payload_file.exists():
            if not (payloads_dir(backup=True) / f"{aircraft_id}.lua").exists():
                backup_payload_file(flight)
            with payload_file.open("r", encoding="utf-8") as file:
                existing = lua.loads(file.read())
        if existing:
            payloads = existing["unitPayloads"]
            tables = payloads["payloads"]
            key = next((k for k in tables if tables[k]["name"] == name), None)
            tables[len(tables) + 1 if key is None else key] = table
            _write_payload_file(payload_file, payloads)
        else:
            new_file = not payload_file.exists()
            _write_payload_file(
                payload_file,
                {"name": aircraft_id, "payloads": {1: table}, "unitType": aircraft_id},
            )
            if new_file:
                aircraft.add_to_payload_cache(payload_file)
    except (OSError, KeyError, SyntaxError) as ex:
        raise CommandError(f"Could not save the payload: {ex}", status_code=500) from ex
    assert aircraft.payloads is not None
    aircraft.payloads[name] = table
    return payload_file

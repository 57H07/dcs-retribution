"""Creating a new campaign (WEB-06).

The one path from "these parameters" to a playable `Game`, shared by the CLI
(`new-game`), the Qt wizard and the web wizard. It is split in two because the player
configures the air wing in between:

* `generate_new_game` loads the campaign and places everything on the map;
* `finish_new_game` starts turn 0.

`create_game` chains both for the CLI. `NewGameGeneration` runs them on a thread for
the web UI: generation takes long and works on a `Game` no other thread can see, so
it never holds the game lock.
"""

from __future__ import annotations

import json
import logging
import random
import threading
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional, TYPE_CHECKING

from dcs.mapping import LatLng

from game import objectives, persistency
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.armedforces.forcegroup import ForceGroup

    from game.campaignloader.campaign import Campaign
    from game.dcs.unittype import UnitType
    from game.factions.faction import Faction
    from game.settings import Settings
    from game.theater.start_generator import ModSettings

#: The player's choices for the start date: a name, then the date.
TIME_PERIODS: dict[str, datetime] = {
    "WW2 - Winter [1944]": datetime(1944, 1, 1),
    "WW2 - Spring [1944]": datetime(1944, 4, 1),
    "WW2 - Summer [1944]": datetime(1944, 6, 1),
    "WW2 - Fall [1944]": datetime(1944, 10, 1),
    "Early Cold War - Winter [1952]": datetime(1952, 1, 1),
    "Early Cold War - Spring [1952]": datetime(1952, 4, 1),
    "Early Cold War - Summer [1952]": datetime(1952, 6, 1),
    "Early Cold War - Fall [1952]": datetime(1952, 10, 1),
    "Cold War - Winter [1970]": datetime(1970, 1, 1),
    "Cold War - Spring [1970]": datetime(1970, 4, 1),
    "Cold War - Summer [1970]": datetime(1970, 6, 1),
    "Cold War - Fall [1970]": datetime(1970, 10, 1),
    "Late Cold War - Winter [1985]": datetime(1985, 1, 1),
    "Late Cold War - Spring [1985]": datetime(1985, 4, 1),
    "Late Cold War - Summer [1985]": datetime(1985, 6, 1),
    "Late Cold War - Fall [1985]": datetime(1985, 10, 1),
    "Gulf War - Winter [1990]": datetime(1990, 1, 1),
    "Gulf War - Spring [1990]": datetime(1990, 4, 1),
    "Gulf War - Summer [1990]": datetime(1990, 6, 1),
    "Mid-90s - Winter [1995]": datetime(1995, 1, 1),
    "Mid-90s - Spring [1995]": datetime(1995, 4, 1),
    "Mid-90s - Summer [1995]": datetime(1995, 6, 1),
    "Mid-90s - Fall [1995]": datetime(1995, 10, 1),
    "Gulf War - Fall [1990]": datetime(1990, 10, 1),
    "Modern - Winter [2010]": datetime(2010, 1, 1),
    "Modern - Spring [2010]": datetime(2010, 4, 1),
    "Modern - Summer [2010]": datetime(2010, 6, 1),
    "Modern - Fall [2010]": datetime(2010, 10, 1),
    "Georgian War [2008]": datetime(2008, 8, 7),
    "Syrian War [2011]": datetime(2011, 3, 15),
    "6 days war [1967]": datetime(1967, 6, 5),
    "Yom Kippour War [1973]": datetime(1973, 10, 6),
    "First Lebanon War [1982]": datetime(1982, 6, 6),
    "Arab-Israeli War [1948]": datetime(1948, 5, 15),
}
#: "Mid-90s - Summer [1995]": the wizard's choice when a campaign recommends no date.
DEFAULT_TIME_PERIOD = list(TIME_PERIODS)[21]

#: `ModSettings` field and label of each mod the player may say is installed.
MOD_CHOICES: tuple[tuple[str, str], ...] = (
    ("a4_skyhawk", "A-4E Skyhawk (v2.3.0)"),
    ("a6a_intruder", "A-6A Intruder (v2.7.5.01)"),
    ("a7e_corsair2", "A-7E Corsair II"),
    ("hercules", "C-130J-30 Super Hercules (v6.8.2)"),
    ("coldwarassets", "Cold War Assets mod (v1.2)"),
    ("chinesemilitaryassetspack", "CurrentHill Chinese Military Assets pack (1.1.4)"),
    ("iranmilitaryassetspack", "CurrentHill Iran Military Assets pack (2.1.0)"),
    ("russianmilitaryassetspack", "CurrentHill Russian Military Assets pack (2.0.0)"),
    ("swedishmilitaryassetspack", "CurrentHill Swedish Military Assets pack (1.10)"),
    ("usamilitaryassetspack", "CurrentHill USA Military Assets pack (1.5.0)"),
    ("ukmilitaryassetspack", "CurrentHill UK Military Assets pack (1.1.2)"),
    ("ukrainemilitaryassetspack", "CurrentHill Ukraine Military Assets pack (1.1.1)"),
    ("ea6b_prowler", "EA-6B Prowler (v2.9.4.102)"),
    ("e7a_wedgetail", "E-7A Wedgetail (AI Only, EW Capable)"),
    ("f100_supersabre", "F-100 Super Sabre (v2.7.18.30765 patch 20.10.22)"),
    ("f104_starfighter", "F-104 Starfighter (v2.7.11.222.01)"),
    ("f105_thunderchief", "F-105 Thunderchief (v2.7.12.23x)"),
    ("f106_deltadart", "F-106 Delta Dart (v2.9.4.101)"),
    ("f15d_baz", "F-15D Baz (v1.0)"),
    ("f_15_idf", "F-15I Ra'am (v1.0 by IDF Mods Project)"),
    ("f_16_idf", "F-16I Sufa & F-16D (v3.6 by IDF Mods Project)"),
    ("f22_raptor", "F-22A Raptor (v2.0.0 released May 2025)"),
    ("VSN_F35", "F-35A/B/C Lightning II (v2.9.2.103 FC3 EFM)"),
    ("f4bc_phantom", "F-4B/C Phantom II (2.8.7.204)"),
    ("f4e_expanded_weapons", "F-4E Expanded Weapons (v1.0.11)"),
    ("f84g_thunderjet", "F-84G Thunderjet (v2.5.7.01)"),
    ("f111c", "F-111C Aardvark (Warpig Production v2.260208)"),
    ("f9f_panther", "F9F Panther (v2.8.7.101)"),
    ("fa_18efg", "F/A-18E/F/G Super Hornet (version 2.4.5.260501.RC1)"),
    ("fa18ef_tanker", "F/A-18E/F Super Hornet AI Tanker (version 2.4.5.260501.RC1)"),
    ("frenchpack", "Frenchpack (v4.9.1)"),
    ("high_digit_sams", "High Digit SAMs (v1.4.0)"),
    ("irondome", "IDF Assets Pack (v1.1 by IDF Mods Project)"),
    ("jas39_gripen", "JAS 39 Gripen (v1.8.5-beta)"),
    ("mig31bm_foxhound", "MiG-31BM (v2.62)"),
    ("mam", "Military Aircraft Mod (v1.7.2 - AI Only)"),
    ("mirage_3", "Mirage III (v2.5.7.01)"),
    ("oh_6", "OH-6 Cayuse (v1.7)"),
    ("oh_6_vietnamassetpack", "OH-6 Vietnam Asset Pack (v1.0)"),
    ("ov10a_bronco", "OV-10A Bronco"),
    ("sk_60", "Saab 105/SK-60B (v1.2.1)"),
    ("spanishnavypack", "Spanish Naval Assets pack (desdemicabina 3.2.0)"),
    ("SWPack", "Star Wars Modpack 2.54+"),
    ("su15_flagon", "Su-15 Flagon (v1.0)"),
    ("su30_flanker_h", "Su-30 Flanker-H (v2.8.04b + CWS 3.72)"),
    ("su35s_flanker_m", "Su-35S Flanker-M (v2.0.27b)"),
    ("su57_felon", "Su-57 Felon (build-04)"),
    ("super_etendard", "Super Étendard (v2.5.5)"),
    ("tornado_adv", "Tornado F3 ADV (1.0)"),
    ("uh_60l", "UH-60L Black Hawk (v2.1.5)"),
    ("vietnamwarvessels", "Vietnam War Vessels (v3.0.0 by TeTeT)"),
)

#: Text of `Campaign.performance` (0 to 3), in the words of the Qt wizard.
PERFORMANCE_TEXTS = (
    "This scenario is rather performance friendly.",
    "This scenario requires a very good computer to run.",
    "This scenario is not performance friendly. The usage of the culling settings "
    "is recommended for most users.",
    "This theater is huge, and will generate very complex DCS missions with hundreds "
    "of units, pushing the limits of DCS engine. An insanely powerful computer will "
    "be necessary to run it. Usage of culling settings will probably be mandatory "
    "for decent FPS.",
)
PERFORMANCE_LABELS = ("Friendly", "Medium", "Hard", "Extreme")

HERCULES = "C-130J-30 Super Hercules"

#: Called with the name of each step as it starts.
ProgressCallback = Callable[[str], None]


def _no_progress(_: str) -> None:
    pass


# --- Campaigns -----------------------------------------------------------------


def campaign_id(campaign: Campaign) -> str:
    """Stable id of a campaign: its file name, without the extension."""
    return campaign.path.stem


def load_campaigns() -> list[Campaign]:
    """Every campaign by name. A user campaign hides a shipped one of the same file."""
    from game.campaignloader.campaign import Campaign

    by_id: dict[str, Campaign] = {}
    for campaign in Campaign.load_each():
        by_id.setdefault(campaign_id(campaign), campaign)
    return sorted(by_id.values(), key=lambda c: c.name.lower())


def find_campaign(identifier: str) -> Campaign:
    """The campaign with this id.

    Raises:
        CommandError: 404, no such campaign.
    """
    from game.campaignloader.campaign import Campaign

    for path in Campaign.iter_campaign_defs():
        if path.stem == identifier:
            try:
                return Campaign.from_file(path)
            except RuntimeError as error:
                raise CommandError(f"Cannot read {identifier}: {error}")
    raise CommandError(f"Unknown campaign {identifier}.", status_code=404)


def campaign_era(campaign: Campaign) -> Optional[str]:
    """The era of the campaign's recommended date; None when it recommends none."""
    start = campaign.recommended_start_date
    if start is None:
        return None
    if start.year < 1950:
        return "WW2"
    if start.year < 1991:
        return "Cold War"
    return "Modern"


@dataclass(frozen=True)
class PreviewBase:
    name: str
    position: LatLng
    side: str
    kind: str


@dataclass(frozen=True)
class PreviewLink:
    from_index: int
    to_index: int
    front_line: bool


@dataclass(frozen=True)
class CampaignPreview:
    #: Corners around `bases`; None without a base on the map.
    south_west: Optional[LatLng]
    north_east: Optional[LatLng]
    bases: list[PreviewBase]
    links: list[PreviewLink]
    blue_bases: int
    red_bases: int
    front_lines: int


def _side(player: Any) -> str:
    if player.is_blue:
        return "blue"
    if player.is_red:
        return "red"
    return "neutral"


@lru_cache(maxsize=16)
def _preview_of_file(path: Path) -> CampaignPreview:
    from game.campaignloader.campaign import Campaign
    from game.theater.controlpoint import OffMapSpawn

    theater = Campaign.from_file(path).load_theater(advanced_iads=False)
    points = list(theater.controlpoints)
    on_map = [cp for cp in points if not isinstance(cp, OffMapSpawn)]
    bounds = theater.campaign_bounds()
    if bounds is None:
        return CampaignPreview(None, None, [], [], 0, 0, 0)
    index = {cp: i for i, cp in enumerate(on_map)}
    bases = [
        PreviewBase(
            cp.name,
            cp.position.latlng(),
            _side(cp.starting_coalition),
            cp.cptype.name,
        )
        for cp in on_map
    ]
    links: list[PreviewLink] = []
    for cp in on_map:
        for other in cp.connected_points:
            if other in index and index[cp] < index[other]:
                front = (
                    _side(cp.starting_coalition),
                    _side(other.starting_coalition),
                ) in (("blue", "red"), ("red", "blue"))
                links.append(PreviewLink(index[cp], index[other], front))
    return CampaignPreview(
        bounds[0],
        bounds[1],
        bases,
        links,
        sum(base.side == "blue" for base in bases),
        sum(base.side == "red" for base in bases),
        sum(link.front_line for link in links),
    )


def campaign_preview(campaign: Campaign) -> CampaignPreview:
    """What the map preview shows. Reads the campaign's miz: slow the first time."""
    return _preview_of_file(campaign.path)


# --- Settings ------------------------------------------------------------------


def default_settings() -> Settings:
    """The player's default settings: `Default.zip`, or the engine's defaults."""
    from game.settings import Settings

    settings = Settings()
    path = persistency.settings_dir() / "Default.zip"
    if not path.exists():
        return settings
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = [n for n in archive.namelist() if n.lower() == "default.json"]
            if names:
                state = json.loads(
                    archive.read(names[0]).decode("utf-8"),
                    object_hook=settings.obj_hook,
                )
                settings.__setstate__(state)
    except (OSError, ValueError, zipfile.BadZipFile):
        logging.exception("Could not read the default settings at %s", path)
        return Settings()
    return settings


def starting_settings(campaign: Campaign) -> Settings:
    """What a campaign starts with before the player changes anything."""
    from game.settings import Settings

    settings = default_settings()
    # deserialize_state_dict changes the dict it is given.
    from_campaign = Settings.deserialize_state_dict(dict(campaign.settings))
    if from_campaign.get("plugins"):
        from_campaign["plugins"] = {
            **settings.__dict__["plugins"],
            **from_campaign["plugins"],
        }
    settings.__dict__.update(from_campaign)
    settings.player_income_multiplier = campaign.recommended_player_income_multiplier
    settings.enemy_income_multiplier = campaign.recommended_enemy_income_multiplier
    return settings


def apply_setting_values(settings: Settings, values: dict[str, Any]) -> None:
    """Sets the given settings, by the key of the settings screen.

    Raises:
        CommandError: 404 for an unknown key, 422 for a wrong or out of bounds value.
    """
    from .settings import find_setting, validate_value

    for key, value in values.items():
        entry = find_setting(key)
        entry.write(settings, validate_value(entry, value))


def mod_settings_from(enabled: Iterable[str]) -> ModSettings:
    """`ModSettings` with these mods on.

    Raises:
        CommandError: not a mod.
    """
    from game.theater.start_generator import ModSettings

    known = {f.name for f in fields(ModSettings)}
    names = set(enabled)
    if unknown := names - known:
        raise CommandError(f"Unknown mod: {', '.join(sorted(unknown))}.")
    return ModSettings(**{name: True for name in names})


@dataclass(frozen=True)
class CampaignDefaults:
    """What the wizard proposes for a campaign."""

    settings: Settings
    blue_faction: str
    red_faction: str
    start_date: Optional[date]
    time_period: Optional[str]
    player_budget: int
    enemy_budget: int
    advanced_iads_available: bool
    no_carrier: bool
    no_lha: bool
    no_player_navy: bool
    no_enemy_navy: bool
    squadrons_start_full: bool
    mods: list[str]


def campaign_defaults(campaign: Campaign) -> CampaignDefaults:
    wanted = campaign.settings
    recommended = campaign.recommended_start_date
    return CampaignDefaults(
        settings=starting_settings(campaign),
        blue_faction=campaign.recommended_player_faction,
        red_faction=campaign.recommended_enemy_faction,
        start_date=recommended,
        time_period=None if recommended is not None else DEFAULT_TIME_PERIOD,
        player_budget=campaign.recommended_player_money,
        enemy_budget=campaign.recommended_enemy_money,
        advanced_iads_available=campaign.advanced_iads,
        no_carrier=wanted.get("no_carrier", False),
        no_lha=wanted.get("no_lha", False),
        no_player_navy=wanted.get("no_player_navy", False),
        no_enemy_navy=wanted.get("no_enemy_navy", False),
        # The key the shipped campaigns use, without the "s".
        squadrons_start_full=wanted.get("squadron_start_full", False),
        mods=[name for name, _ in MOD_CHOICES if wanted.get(name, False)],
    )


# --- Factions ------------------------------------------------------------------


@dataclass(frozen=True)
class UnitGroup:
    """One list of units of a faction."""

    key: str
    label: str
    #: `Faction` attribute.
    attribute: str


UNIT_GROUPS = (
    UnitGroup("aircraft", "Aircraft", "aircraft"),
    UnitGroup("awacs", "AWACS", "awacs"),
    UnitGroup("tankers", "Tankers", "tankers"),
    UnitGroup("frontline", "Frontline vehicles", "frontline_units"),
    UnitGroup("artillery", "Artillery units", "artillery_units"),
    UnitGroup("logistics", "Logistics units", "logistics_units"),
    UnitGroup("infantry", "Infantry units", "infantry_units"),
    UnitGroup("preset_groups", "Preset groups", "preset_groups"),
    UnitGroup("air_defense", "Air defenses", "air_defense_units"),
    UnitGroup("naval", "Naval units", "naval_units"),
    UnitGroup("missiles", "Missile units", "missiles"),
)


def _unit_group(key: str) -> UnitGroup:
    for group in UNIT_GROUPS:
        if group.key == key:
            return group
    raise CommandError(f"Unknown unit group {key}.", status_code=404)


def _addable_aircraft(faction: Faction, group: str) -> list[Any]:
    from game.ato.flighttype import FlightType
    from game.dcs.aircrafttype import AircraftType

    addable = []
    for dcs_type in sorted(AircraftType.each_dcs_type(), key=lambda x: x.id):
        for aircraft in AircraftType.for_dcs_type(dcs_type):
            if (
                aircraft in faction.aircraft
                or aircraft in faction.awacs
                or aircraft in faction.tankers
            ):
                continue
            awacs = FlightType.AEWC in aircraft.task_priorities
            tanker = FlightType.REFUELING in aircraft.task_priorities
            if (
                (group == "awacs" and awacs)
                or (group == "tankers" and tanker)
                or (group == "aircraft" and not awacs and not tanker)
            ):
                addable.append(aircraft)
    return addable


def _addable_ground_units(
    faction: Faction, units: Iterable[Any], classes: Optional[set[str]]
) -> list[Any]:
    from game.dcs.groundunittype import GroundUnitType

    addable = []
    for dcs_type in sorted(GroundUnitType.each_dcs_type(), key=lambda x: x.id):
        if dcs_type not in faction.country.vehicles:
            continue
        for unit in GroundUnitType.for_dcs_type(dcs_type):
            if unit not in units and (
                classes is None or unit.unit_class.value in classes
            ):
                addable.append(unit)
    return addable


def addable_units(faction: Faction, group: UnitGroup) -> list[Any]:
    """What may join this list of the faction (Qt: the combo boxes of QFactionUnits)."""
    from game.armedforces.forcegroup import ForceGroup
    from game.dcs.shipunittype import ShipUnitType

    units = getattr(faction, group.attribute)
    if group.key in ("aircraft", "awacs", "tankers"):
        return _addable_aircraft(faction, group.key)
    if group.key == "preset_groups":
        ForceGroup._load_all()
        names = {preset.name for preset in faction.preset_groups}
        return [
            preset for name, preset in ForceGroup._by_name.items() if name not in names
        ]
    if group.key == "naval":
        return [
            ship
            for dcs_type in sorted(ShipUnitType.each_dcs_type(), key=lambda x: x.id)
            for ship in ShipUnitType.for_dcs_type(dcs_type)
            if ship not in units
        ]
    classes: Optional[set[str]] = {
        "frontline": None,
        "artillery": {"Artillery"},
        "logistics": {"Logistics"},
        "infantry": {"Infantry"},
        "air_defense": {"EarlyWarningRadar", "AAA", "SHORAD"},
        "missiles": {"Missile"},
    }[group.key]
    return _addable_ground_units(faction, units, classes)


def _invalidate_unit_caches(faction: Faction) -> None:
    faction.__dict__.pop("accessible_units", None)
    faction.__dict__.pop("all_aircrafts", None)


def add_unit_to_faction(
    faction: Faction, group_key: str, unit_name: str
) -> UnitType[Any] | ForceGroup:
    """Adds a unit of `addable_units` to the faction, by its name.

    Raises:
        CommandError: 404 for an unknown group, otherwise not a unit it can add.
    """
    group = _unit_group(group_key)
    unit = next((u for u in addable_units(faction, group) if str(u) == unit_name), None)
    if unit is None:
        raise CommandError(f"{unit_name} cannot join {group.label.lower()}.")
    units = getattr(faction, group.attribute)
    if isinstance(units, list):
        units.append(unit)
    else:
        units.add(unit)
    _invalidate_unit_caches(faction)
    return unit


def doctrine_named(faction: Faction, name: str) -> Any:
    """The doctrine with this name, among those `doctrine_choices` lists.

    Raises:
        CommandError: no such doctrine.
    """
    for doctrine in doctrine_choices(faction):
        if doctrine.name == name:
            return doctrine
    raise CommandError(f"Unknown doctrine {name}.")


def doctrine_choices(faction: Faction) -> list[Any]:
    from game.data.doctrine import ALL_DOCTRINES

    choices = list(ALL_DOCTRINES)
    if faction.doctrine not in choices:
        choices.insert(0, faction.doctrine)
    return choices


@dataclass(frozen=True)
class FactionChoice:
    """A faction of the wizard, with what the player changed in its units."""

    name: str
    #: Names of units to take out, per `UnitGroup.key`.
    removed: dict[str, list[str]] = field(default_factory=dict)
    #: Names of units to add, per `UnitGroup.key`.
    added: dict[str, list[str]] = field(default_factory=dict)
    has_jtac: Optional[bool] = None
    doctrine: Optional[str] = None


def find_faction(name: str) -> Faction:
    """The faction with this name.

    Raises:
        CommandError: 404, no such faction.
    """
    from game.factions import FACTIONS

    if name not in FACTIONS.factions:
        raise CommandError(f"Unknown faction {name}.", status_code=404)
    return FACTIONS[name]


def customized_faction(choice: FactionChoice) -> Faction:
    """A copy of the chosen faction with the player's changes; the original is kept.

    Raises:
        CommandError: an unknown faction, group, unit or doctrine.
    """
    from copy import deepcopy

    faction = deepcopy(find_faction(choice.name))
    for key, names in choice.removed.items():
        group = _unit_group(key)
        units = getattr(faction, group.attribute)
        for unit in [u for u in units if str(u) in set(names)]:
            units.remove(unit)
    for key, names in choice.added.items():
        for name in names:
            add_unit_to_faction(faction, key, name)
    if choice.has_jtac is not None:
        faction.has_jtac = choice.has_jtac
    if choice.doctrine is not None:
        faction.doctrine = doctrine_named(faction, choice.doctrine)
    _invalidate_unit_caches(faction)
    return faction


def save_faction(
    choice: FactionChoice, name: str, description: str, authors: str
) -> None:
    """Saves the customized faction under a new name, in the user's factions folder.

    Raises:
        CommandError: an empty, unusable or already taken name.
    """
    from game.factions import FACTIONS

    name = name.strip()
    if not name:
        raise CommandError("A faction needs a name.")
    if any(c in name for c in '<>:"/\\|?*') or name.endswith("."):
        raise CommandError(f"{name} cannot be used as a file name.")
    if name in FACTIONS.factions:
        raise CommandError(f"A faction named {name} already exists.")
    faction = customized_faction(choice)
    faction.name = name
    faction.description = f"<p>{description}</p>"
    faction.authors = authors
    path = persistency.factions_dir() / f"{name}.json"
    try:
        with path.open("w", encoding="utf-8") as file:
            json.dump(faction.to_dict(), file, indent=2)
    except OSError as error:
        raise CommandError(f"Could not write {path}: {error}", status_code=500)
    FACTIONS.factions[name] = faction


# --- Generation ----------------------------------------------------------------


@dataclass
class NewGameParameters:
    """Everything a new campaign is made from."""

    campaign: Campaign
    #: Copies (`customized_faction`): the generator writes the mod settings on them.
    blue_faction: Faction
    red_faction: Faction
    settings: Settings
    mod_settings: ModSettings
    start_date: datetime
    player_budget: int
    enemy_budget: int
    inverted: bool = False
    advanced_iads: bool = False
    no_carrier: bool = False
    no_lha: bool = False
    no_player_navy: bool = False
    no_enemy_navy: bool = False
    squadrons_start_full: bool = False
    #: Same parameters and seed, same campaign. None draws from the current RNG state.
    seed: Optional[int] = None


GENERATION_STEPS = ("Loading the theater", "Generating the campaign")
TURN_0_STEPS = ("Starting turn 0",)


def _seed_rngs(seed: int) -> None:
    from faker import Faker

    random.seed(seed)
    Faker.seed(seed)


def generate_new_game(
    parameters: NewGameParameters, progress: ProgressCallback = _no_progress
) -> Game:
    """Creates the game, up to the air wing configuration: no turn has started.

    Raises nothing of its own: a broken campaign file raises what its loader raises.
    """
    from game.theater.start_generator import GameGenerator, GeneratorSettings

    if parameters.seed is not None:
        _seed_rngs(parameters.seed)
    campaign = parameters.campaign
    progress(GENERATION_STEPS[0])
    theater = campaign.load_theater(parameters.advanced_iads)
    # The generation renames some bases (carriers): objectives use the .miz names.
    miz_names = {cp.id: cp.name for cp in theater.controlpoints}
    progress(GENERATION_STEPS[1])
    generator = GameGenerator(
        parameters.blue_faction,
        parameters.red_faction,
        theater,
        campaign.load_air_wing_config(theater),
        parameters.settings,
        GeneratorSettings(
            start_date=parameters.start_date,
            start_time=campaign.recommended_start_time,
            player_budget=parameters.player_budget,
            enemy_budget=parameters.enemy_budget,
            inverted=parameters.inverted,
            advanced_iads=theater.iads_network.advanced_iads,
            no_carrier=parameters.no_carrier,
            no_lha=parameters.no_lha,
            no_player_navy=parameters.no_player_navy,
            no_enemy_navy=parameters.no_enemy_navy,
            tgo_config=campaign.load_ground_forces_config(),
            carrier_config=campaign.load_carrier_config(),
            squadrons_start_full=parameters.squadrons_start_full,
        ),
        parameters.mod_settings,
        campaign_name=campaign.name,
    )
    game = generator.generate()
    # #194: kept on the game, a save goes on without its campaign file. They are
    # written for the blue side: an inverted campaign has none.
    if parameters.inverted:
        if campaign.data.get("objectives"):
            logging.info("Inverted campaign: its objectives are ignored")
    else:
        game.objectives = objectives.load(
            campaign.data.get("objectives"), game, miz_names
        )
    return game


def finish_new_game(
    game: Game,
    squadrons_start_full: bool,
    seed: Optional[int] = None,
    progress: ProgressCallback = _no_progress,
) -> None:
    """Starts turn 0, once the air wing is configured."""
    if seed is not None:
        # Faker draws from the shared RNG when it builds a locale: build them first, or
        # the result would depend on which locales this process has already used.
        for coalition in game.coalitions:
            for squadron in coalition.air_wing.iter_squadrons():
                squadron.faker
        # What ran since generation (the air wing screen) must not change the result.
        _seed_rngs(seed + 1)
    progress(TURN_0_STEPS[0])
    if any(
        aircraft.variant_id == HERCULES
        for coalition in game.coalitions
        for aircraft in coalition.air_wing.squadrons
    ):
        game.settings.set_plugin_option("herculescargo", True)
    game.begin_turn_0(squadrons_start_full=squadrons_start_full)


def cli_parameters(
    campaign_path: Path,
    blue: str,
    red: str,
    supercarrier: bool,
    auto_procurement: bool,
    inverted: bool,
    cheats: bool,
    start_date: datetime,
    restrict_weapons_by_date: bool,
    advanced_iads: bool,
    use_new_squadron_rules: bool,
    squadrons_start_full: bool,
    seed: Optional[int] = None,
) -> NewGameParameters:
    """The parameters of the CLI `new-game`: its flags are settings of the campaign."""
    from game.campaignloader.campaign import Campaign, DEFAULT_BUDGET
    from game.theater.start_generator import ModSettings

    campaign = Campaign.from_file(campaign_path)
    settings = starting_settings(campaign)
    settings.supercarrier = supercarrier
    settings.automate_runway_repair = auto_procurement
    settings.automate_front_line_reinforcements = auto_procurement
    settings.automate_aircraft_reinforcements = auto_procurement
    settings.automate_building_repairs = auto_procurement
    settings.automate_ground_object_repairs = auto_procurement
    settings.enable_frontline_cheats = cheats
    settings.enable_base_capture_cheat = cheats
    settings.enable_transfer_cheat = cheats
    settings.restrict_weapons_by_date = restrict_weapons_by_date
    settings.enable_squadron_aircraft_limits = use_new_squadron_rules
    return NewGameParameters(
        campaign=campaign,
        blue_faction=customized_faction(FactionChoice(blue)),
        red_faction=customized_faction(FactionChoice(red)),
        settings=settings,
        mod_settings=ModSettings(),
        start_date=start_date,
        player_budget=DEFAULT_BUDGET,
        enemy_budget=DEFAULT_BUDGET,
        inverted=inverted,
        advanced_iads=advanced_iads,
        squadrons_start_full=squadrons_start_full,
        seed=seed,
    )


def create_game(parameters: NewGameParameters) -> Game:
    """A whole new campaign in one go, with the air wing of the campaign file."""
    game = generate_new_game(parameters)
    finish_new_game(game, parameters.squadrons_start_full, parameters.seed)
    return game


class GenerationStatus(Enum):
    IDLE = "idle"
    #: On its thread: the campaign is being generated.
    GENERATING = "generating"
    #: Generated: waits for the player to configure the air wing.
    CONFIGURING = "configuring"
    #: On its thread: turn 0 is starting.
    STARTING = "starting"
    #: Handed to the shell, which makes it the current campaign.
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class GenerationSnapshot:
    status: GenerationStatus
    step: Optional[str]
    #: Steps finished, out of `step_count`.
    step_index: int
    step_count: int
    error: Optional[str]


_NAME_COUNTERS = (
    "number",
    "infantry_number",
    "aircraft_number",
    "convoy_number",
    "cargo_ship_number",
    "jtac_number",
    "animals",
    "existing_alphas",
)


def _save_names() -> dict[str, Any]:
    from game.naming import NameGenerator

    saved = {}
    for name in _NAME_COUNTERS:
        value = getattr(NameGenerator, name)
        saved[name] = list(value) if isinstance(value, list) else value
    return saved


def _restore_names(saved: dict[str, Any]) -> None:
    from game.naming import NameGenerator

    for name, value in saved.items():
        setattr(NameGenerator, name, value)


class NewGameGeneration:
    """The new campaign in the making: a status, a thread, and the draft game.

    The status has its own small lock: reading it never waits for the game lock. The
    draft `Game` is reachable by no other thread until the shell installs it, except
    the air wing commands, which the status only allows while no thread runs and
    which hold the game lock like any command.
    """

    def __init__(self, on_change: Callable[[], None] = lambda: None) -> None:
        self._lock = threading.Lock()
        self._on_change = on_change
        self._status = GenerationStatus.IDLE
        self._step: Optional[str] = None
        self._step_index = 0
        self._step_count = 0
        self._error: Optional[str] = None
        self._draft: Optional[Game] = None
        self._parameters: Optional[NewGameParameters] = None
        self._names_of_previous_game: Optional[dict[str, Any]] = None
        self._thread: Optional[threading.Thread] = None

    def snapshot(self) -> GenerationSnapshot:
        with self._lock:
            return GenerationSnapshot(
                self._status,
                self._step,
                self._step_index,
                self._step_count,
                self._error,
            )

    def draft(self) -> Optional[Game]:
        """The game waiting for its air wing configuration, if any."""
        with self._lock:
            if self._status is GenerationStatus.CONFIGURING:
                return self._draft
            return None

    def _set(self, status: GenerationStatus, step_count: int) -> None:
        with self._lock:
            self._status = status
            self._step = None
            self._step_index = 0
            self._step_count = step_count
            self._error = None
        self._on_change()

    def _progress(self, step: str) -> None:
        with self._lock:
            if self._step is not None:
                self._step_index += 1
            self._step = step
        self._on_change()

    def _fail(self, error: Exception, message: str) -> None:
        logging.exception(message, exc_info=error)
        with self._lock:
            self._status = GenerationStatus.FAILED
            self._step = None
            self._error = f"{message}: {error}"
            self._draft = None
        self._on_change()

    def _run(self, work: Callable[[], None]) -> None:
        self._thread = threading.Thread(target=work, name="NewGame", daemon=True)
        self._thread.start()

    def start(self, parameters: NewGameParameters) -> None:
        """Starts generating on a thread; `snapshot` tells when it is over.

        Raises:
            CommandError: a generation is already under way or waits for its air wing.
        """
        with self._lock:
            if self._status not in (
                GenerationStatus.IDLE,
                GenerationStatus.DONE,
                GenerationStatus.FAILED,
            ):
                raise CommandError("A new campaign is already being created.")
            self._status = GenerationStatus.GENERATING
            self._parameters = parameters
            self._draft = None
        self._set(GenerationStatus.GENERATING, len(GENERATION_STEPS))
        self._names_of_previous_game = _save_names()
        self._run(lambda: self._generate(parameters))

    def _generate(self, parameters: NewGameParameters) -> None:
        try:
            game = generate_new_game(parameters, self._progress)
        except Exception as error:
            self._forget_draft_names()
            self._fail(error, "The campaign could not be generated")
            return
        with self._lock:
            self._draft = game
        self._set(GenerationStatus.CONFIGURING, 0)

    def begin_campaign(self, hand_over: Callable[[Game], None]) -> None:
        """Starts turn 0 of the draft on a thread, then gives it to `hand_over`.

        Raises:
            CommandError: no draft is waiting.
        """
        with self._lock:
            if self._status is not GenerationStatus.CONFIGURING:
                raise CommandError("No new campaign is waiting to start.")
            game = self._draft
            parameters = self._parameters
            self._status = GenerationStatus.STARTING
        assert game is not None and parameters is not None
        self._set(GenerationStatus.STARTING, len(TURN_0_STEPS))
        self._run(lambda: self._begin(game, parameters, hand_over))

    def _begin(
        self,
        game: Game,
        parameters: NewGameParameters,
        hand_over: Callable[[Game], None],
    ) -> None:
        try:
            finish_new_game(
                game,
                parameters.squadrons_start_full,
                parameters.seed,
                self._progress,
            )
            hand_over(game)
        except Exception as error:
            self._forget_draft_names()
            self._fail(error, "The campaign could not be started")
            return
        with self._lock:
            self._draft = None
            self._parameters = None
            self._names_of_previous_game = None
        self._set(GenerationStatus.DONE, 0)

    def _forget_draft_names(self) -> None:
        """The campaign in play goes on: it gets its generated names back."""
        if self._names_of_previous_game is not None:
            _restore_names(self._names_of_previous_game)
            self._names_of_previous_game = None

    def cancel(self) -> None:
        """Drops the draft and goes back to idle.

        Raises:
            CommandError: a thread is working on it: wait for it.
        """
        with self._lock:
            if self._status in (
                GenerationStatus.GENERATING,
                GenerationStatus.STARTING,
            ):
                raise CommandError("Wait for the current step to finish.")
            self._draft = None
            self._parameters = None
        self._forget_draft_names()
        self._set(GenerationStatus.IDLE, 0)

    def join(self, timeout: Optional[float] = None) -> None:
        """Waits for the thread, if any (tests)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

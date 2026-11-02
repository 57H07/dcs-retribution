"""DTOs of the new campaign wizard (WEB-06), from `game.commands.newgame`."""

from __future__ import annotations

from datetime import date
from typing import Optional, TYPE_CHECKING

from dcs.mapping import LatLng
from pydantic import BaseModel, Field

from game.commands.newgame import (
    CampaignDefaults,
    CampaignPreview,
    FactionChoice,
    GenerationSnapshot,
    PERFORMANCE_LABELS,
    PERFORMANCE_TEXTS,
    UNIT_GROUPS,
    addable_units,
    campaign_era,
    campaign_id,
    doctrine_choices,
)
from game.commands.preferences import is_player_module
from game.commands.settings import settings_pages
from game.dcs.aircrafttype import AircraftType
from ..gamesettings.models import SettingValueJs, SettingsPageJs
from ..leaflet import LeafletPoint

if TYPE_CHECKING:
    from game.campaignloader.campaign import Campaign
    from game.factions.faction import Faction


class CampaignJs(BaseModel):
    id: str
    name: str
    theater: str
    authors: str
    #: Text of the YAML file: may hold simple HTML.
    description: str
    #: Format of the campaign, as "major.minor".
    version: str
    compatible: bool
    #: Why it may not work, when it is not compatible.
    warning: Optional[str]
    #: "WW2", "Cold War", "Modern"; null when it recommends no date.
    era: Optional[str]
    start_date: Optional[date]
    #: Impact of the campaign on the computer, 0 to 3.
    performance: int
    performance_label: str
    performance_text: str
    recommended_blue_faction: str
    recommended_red_faction: str

    class Config:
        title = "NewGameCampaign"

    @staticmethod
    def for_campaign(campaign: Campaign) -> CampaignJs:
        warning = None
        if not campaign.is_compatible:
            warning = (
                "This campaign was created for another version of DCS Retribution. "
                "You can still attempt to play it, but there may be game breaking "
                "bugs."
            )
        performance = max(0, min(campaign.performance, len(PERFORMANCE_TEXTS) - 1))
        return CampaignJs(
            id=campaign_id(campaign),
            name=campaign.name,
            theater=campaign.data.get("theater", ""),
            authors=campaign.authors,
            description=campaign.description,
            version=f"{campaign.version[0]}.{campaign.version[1]}",
            compatible=campaign.is_compatible,
            warning=warning,
            era=campaign_era(campaign),
            start_date=campaign.recommended_start_date,
            performance=performance,
            performance_label=PERFORMANCE_LABELS[performance],
            performance_text=PERFORMANCE_TEXTS[performance],
            recommended_blue_faction=campaign.recommended_player_faction,
            recommended_red_faction=campaign.recommended_enemy_faction,
        )


class TimePeriodJs(BaseModel):
    name: str
    start_date: date

    class Config:
        title = "NewGameTimePeriod"


class ModChoiceJs(BaseModel):
    #: Name to send in `NewGameRequestJs.mods`.
    key: str
    label: str

    class Config:
        title = "NewGameModChoice"


class NewGameOptionsJs(BaseModel):
    """What the wizard offers whatever the campaign."""

    campaigns: list[CampaignJs]
    factions: list[str]
    time_periods: list[TimePeriodJs]
    default_time_period: str
    mods: list[ModChoiceJs]

    class Config:
        title = "NewGameOptions"


def _point(position: LatLng | None) -> LeafletPoint | None:
    return None if position is None else LeafletPoint.from_latlng(position)


class PreviewBaseJs(BaseModel):
    name: str
    position: LeafletPoint
    side: str
    kind: str

    class Config:
        title = "CampaignPreviewBase"


class PreviewLinkJs(BaseModel):
    from_index: int
    to_index: int
    front_line: bool

    class Config:
        title = "CampaignPreviewLink"


class CampaignPreviewJs(BaseModel):
    #: Corners around `bases`; None without a base on the map.
    south_west: LeafletPoint | None
    north_east: LeafletPoint | None
    bases: list[PreviewBaseJs]
    links: list[PreviewLinkJs]
    blue_bases: int
    red_bases: int
    front_lines: int

    class Config:
        title = "CampaignPreview"

    @staticmethod
    def from_preview(preview: CampaignPreview) -> CampaignPreviewJs:
        return CampaignPreviewJs(
            south_west=_point(preview.south_west),
            north_east=_point(preview.north_east),
            bases=[
                PreviewBaseJs(
                    name=base.name,
                    position=LeafletPoint.from_latlng(base.position),
                    side=base.side,
                    kind=base.kind,
                )
                for base in preview.bases
            ],
            links=[
                PreviewLinkJs(
                    from_index=link.from_index,
                    to_index=link.to_index,
                    front_line=link.front_line,
                )
                for link in preview.links
            ],
            blue_bases=preview.blue_bases,
            red_bases=preview.red_bases,
            front_lines=preview.front_lines,
        )


class CampaignDefaultsJs(BaseModel):
    """What the wizard proposes when this campaign is chosen."""

    settings_pages: list[SettingsPageJs]
    blue_faction: str
    red_faction: str
    #: The recommended date; otherwise `time_period` names the proposed one.
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

    class Config:
        title = "CampaignDefaults"

    @staticmethod
    def from_defaults(defaults: CampaignDefaults) -> CampaignDefaultsJs:
        return CampaignDefaultsJs(
            settings_pages=[
                SettingsPageJs.from_page(page, defaults.settings)
                for page in settings_pages()
            ],
            blue_faction=defaults.blue_faction,
            red_faction=defaults.red_faction,
            start_date=defaults.start_date,
            time_period=defaults.time_period,
            player_budget=defaults.player_budget,
            enemy_budget=defaults.enemy_budget,
            advanced_iads_available=defaults.advanced_iads_available,
            no_carrier=defaults.no_carrier,
            no_lha=defaults.no_lha,
            no_player_navy=defaults.no_player_navy,
            no_enemy_navy=defaults.no_enemy_navy,
            squadrons_start_full=defaults.squadrons_start_full,
            mods=defaults.mods,
        )


class FactionUnitGroupJs(BaseModel):
    key: str
    label: str
    #: Names of the units of the faction.
    units: list[str]
    #: Names of the units that can join.
    addable: list[str]
    #: Those of `units` and `addable` the player owns the module of.
    player_modules: list[str]

    class Config:
        title = "FactionUnitGroup"


class FactionSheetJs(BaseModel):
    name: str
    #: Text of the faction file: may hold simple HTML.
    description: str
    authors: str
    requirements: dict[str, str]
    has_jtac: bool
    doctrine: str
    doctrines: list[str]
    groups: list[FactionUnitGroupJs]

    class Config:
        title = "FactionSheet"

    @staticmethod
    def for_faction(faction: Faction) -> FactionSheetJs:
        return FactionSheetJs(
            name=faction.name,
            description=faction.description,
            authors=faction.authors,
            requirements=faction.requirements,
            has_jtac=faction.has_jtac,
            doctrine=faction.doctrine.name,
            doctrines=[doctrine.name for doctrine in doctrine_choices(faction)],
            groups=[
                FactionUnitGroupJs(
                    key=group.key,
                    label=group.label,
                    units=sorted(str(u) for u in getattr(faction, group.attribute)),
                    addable=sorted(str(u) for u in addable_units(faction, group)),
                    player_modules=sorted(
                        str(u)
                        for u in (
                            *getattr(faction, group.attribute),
                            *addable_units(faction, group),
                        )
                        if isinstance(u, AircraftType) and is_player_module(u)
                    ),
                )
                for group in UNIT_GROUPS
            ],
        )


class FactionChoiceJs(BaseModel):
    name: str
    #: Names of units to take out, per group key.
    removed: dict[str, list[str]] = {}
    #: Names of units to add, per group key.
    added: dict[str, list[str]] = {}
    has_jtac: Optional[bool] = None
    doctrine: Optional[str] = None

    class Config:
        title = "NewGameFactionChoice"

    def to_choice(self) -> FactionChoice:
        return FactionChoice(
            self.name, self.removed, self.added, self.has_jtac, self.doctrine
        )


class SaveFactionJs(BaseModel):
    faction: FactionChoiceJs
    name: str
    description: str = ""
    authors: str = ""

    class Config:
        title = "SaveFaction"


class NewGameRequestJs(BaseModel):
    """The full parameters of a new campaign."""

    campaign_id: str
    blue: FactionChoiceJs
    red: FactionChoiceJs
    start_date: date
    player_budget: int = Field(ge=0)
    enemy_budget: int = Field(ge=0)
    inverted: bool = False
    advanced_iads: bool = False
    no_carrier: bool = False
    no_lha: bool = False
    no_player_navy: bool = False
    no_enemy_navy: bool = False
    squadrons_start_full: bool = False
    #: Keys of `NewGameOptionsJs.mods` that are installed.
    mods: list[str] = []
    #: Settings that differ from what `CampaignDefaultsJs` proposed, by key.
    settings: dict[str, SettingValueJs] = {}
    #: Same parameters and seed, same campaign.
    seed: Optional[int] = None

    class Config:
        title = "NewGameRequest"


class GenerationJs(BaseModel):
    #: "idle", "generating", "configuring", "starting", "done" or "failed".
    status: str
    step: Optional[str]
    step_index: int
    step_count: int
    error: Optional[str]

    class Config:
        title = "NewGameGeneration"

    @staticmethod
    def from_snapshot(snapshot: GenerationSnapshot) -> GenerationJs:
        return GenerationJs(
            status=snapshot.status.value,
            step=snapshot.step,
            step_index=snapshot.step_index,
            step_count=snapshot.step_count,
            error=snapshot.error,
        )

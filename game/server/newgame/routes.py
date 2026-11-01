"""New campaign wizard (WEB-06).

None of these routes touches the campaign in play, so none takes the game lock: they
read campaign files, which may take seconds, and the generation runs on its own
thread. `GET /new-game/generation` follows it, and the changes are published on the
event stream (`new_game_updated`). The air wing of the draft is configured through
`/air-wing-config/draft` before `POST /new-game/generation/begin` starts turn 0.
"""

from __future__ import annotations

from datetime import datetime, time

from fastapi import APIRouter, Depends, Query, Response, status

from game.commands.newgame import (
    DEFAULT_TIME_PERIOD,
    MOD_CHOICES,
    NewGameGeneration,
    NewGameParameters,
    TIME_PERIODS,
    apply_setting_values,
    campaign_defaults,
    campaign_preview,
    customized_faction,
    find_campaign,
    find_faction,
    load_campaigns,
    mod_settings_from,
    save_faction,
    starting_settings,
)
from game.factions import FACTIONS
from game.gamelock import locks_game_itself
from game.native import NativeBridge
from game.sim import GameUpdateEvents
from .models import (
    CampaignDefaultsJs,
    CampaignJs,
    CampaignPreviewJs,
    FactionSheetJs,
    GenerationJs,
    ModChoiceJs,
    NewGameOptionsJs,
    NewGameRequestJs,
    SaveFactionJs,
    TimePeriodJs,
)
from ..commanderrors import command_error_responses
from ..eventstream import EventStream
from ..native.routes import require_bridge

router: APIRouter = APIRouter(prefix="/new-game")


def _publish() -> None:
    EventStream.put_nowait(GameUpdateEvents().update_new_game())


class NewGameContext:
    """One generation per application: the wizard makes one campaign at a time."""

    _generation: NewGameGeneration | None = None

    @classmethod
    def get(cls) -> NewGameGeneration:
        if cls._generation is None:
            cls._generation = NewGameGeneration(_publish)
        return cls._generation

    @classmethod
    def set(cls, generation: NewGameGeneration | None) -> None:
        """Replace the generation (tests)."""
        cls._generation = generation


@router.get("/options", operation_id="get_new_game_options")
@locks_game_itself
def get_options() -> NewGameOptionsJs:
    """The campaigns, factions, time periods and mods the wizard offers."""
    # Reading the campaigns first: a campaign file can bring its own factions.
    campaigns = [CampaignJs.for_campaign(c) for c in load_campaigns()]
    return NewGameOptionsJs(
        campaigns=campaigns,
        factions=sorted(FACTIONS),
        time_periods=[
            TimePeriodJs(name=name, start_date=when.date())
            for name, when in TIME_PERIODS.items()
        ],
        default_time_period=DEFAULT_TIME_PERIOD,
        mods=[ModChoiceJs(key=key, label=label) for key, label in MOD_CHOICES],
    )


@router.get(
    "/campaigns/{campaign_id}/preview",
    operation_id="get_campaign_preview",
    responses={404: {"description": "Unknown campaign."}},
)
@locks_game_itself
def get_preview(campaign_id: str) -> CampaignPreviewJs:
    """The bases and front lines of a campaign, for its map preview."""
    return CampaignPreviewJs.from_preview(campaign_preview(find_campaign(campaign_id)))


@router.get(
    "/campaigns/{campaign_id}/defaults",
    operation_id="get_campaign_defaults",
    responses={404: {"description": "Unknown campaign."}},
)
@locks_game_itself
def get_defaults(campaign_id: str) -> CampaignDefaultsJs:
    """What the wizard proposes for this campaign: factions, date, settings..."""
    return CampaignDefaultsJs.from_defaults(
        campaign_defaults(find_campaign(campaign_id))
    )


@router.get(
    "/faction",
    operation_id="get_new_game_faction",
    responses={404: {"description": "Unknown faction."}},
)
@locks_game_itself
def get_faction(name: str = Query()) -> FactionSheetJs:
    """Description and units of a faction. Its name may hold any character."""
    return FactionSheetJs.for_faction(find_faction(name))


@router.post(
    "/factions",
    operation_id="save_new_game_faction",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("when the name is empty, unusable or taken"),
)
@locks_game_itself
def post_faction(body: SaveFactionJs) -> None:
    """Saves a customized faction under a new name, in the user's factions folder."""
    save_faction(body.faction.to_choice(), body.name, body.description, body.authors)


def _parameters(body: NewGameRequestJs) -> NewGameParameters:
    campaign = find_campaign(body.campaign_id)
    settings = starting_settings(campaign)
    apply_setting_values(settings, dict(body.settings))
    return NewGameParameters(
        campaign=campaign,
        blue_faction=customized_faction(body.blue.to_choice()),
        red_faction=customized_faction(body.red.to_choice()),
        settings=settings,
        mod_settings=mod_settings_from(body.mods),
        start_date=datetime.combine(body.start_date, time()),
        player_budget=body.player_budget,
        enemy_budget=body.enemy_budget,
        inverted=body.inverted,
        advanced_iads=body.advanced_iads,
        no_carrier=body.no_carrier,
        no_lha=body.no_lha,
        no_player_navy=body.no_player_navy,
        no_enemy_navy=body.no_enemy_navy,
        squadrons_start_full=body.squadrons_start_full,
        seed=body.seed,
    )


@router.get("/generation", operation_id="get_new_game_generation")
@locks_game_itself
def get_generation() -> GenerationJs:
    return GenerationJs.from_snapshot(NewGameContext.get().snapshot())


@router.post(
    "/generation",
    operation_id="start_new_game_generation",
    responses={
        **command_error_responses(
            "when a new campaign is already being created, or a parameter is refused"
        ),
        404: {"description": "Unknown campaign, faction or setting."},
    },
)
@locks_game_itself
def post_generation(body: NewGameRequestJs) -> GenerationJs:
    """Generates the campaign on a thread: answers at once. The campaign in play stays
    until `POST /new-game/generation/begin`."""
    generation = NewGameContext.get()
    generation.start(_parameters(body))
    return GenerationJs.from_snapshot(generation.snapshot())


@router.post(
    "/generation/begin",
    operation_id="begin_new_game",
    responses={
        **command_error_responses("when no new campaign is waiting to start"),
        503: {"description": "The native shell is not available."},
    },
)
@locks_game_itself
def post_begin(bridge: NativeBridge = Depends(require_bridge)) -> GenerationJs:
    """Starts turn 0 on a thread, then makes it the campaign in play."""
    generation = NewGameContext.get()
    generation.begin_campaign(bridge.game_created)
    return GenerationJs.from_snapshot(generation.snapshot())


@router.delete(
    "/generation",
    operation_id="cancel_new_game_generation",
    responses=command_error_responses("while a step is running"),
)
@locks_game_itself
def delete_generation() -> GenerationJs:
    """Drops the generated campaign; the campaign in play goes on."""
    generation = NewGameContext.get()
    generation.cancel()
    return GenerationJs.from_snapshot(generation.snapshot())

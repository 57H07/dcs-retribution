"""Air wing configuration (WEB-06), on the draft of a new campaign or the one in play.

`target` says which: `draft` is the campaign the wizard just generated, before its
turn 0; `campaign` is the campaign in play, when the "Enable Air Wing adjustments"
cheat is on. Each command applies at once and answers 204: the screen refetches.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from game import Game, persistency
from game.commands import (
    CommandError,
    find_squadron,
    flight_type_named,
    livery_choices,
    set_auto_assignable,
    set_primary_task,
    set_squadron_livery,
)
from game.commands.airwingconfig import (
    add_faction_unit,
    add_squadron,
    load_air_wing,
    move_to_base,
    remove_squadron,
    rename_squadron,
    replace_with_preset,
    reroll_nickname,
    save_air_wing,
    set_max_size,
    set_nickname,
    set_player_names,
)
from game.commands.newgame import doctrine_named
from game.coalition import Coalition
from game.dcs.aircrafttype import AircraftType
from game.gamelock import game_lock, locked, locks_game_itself
from game.native import NativeBridge, one_dialog
from game.squadrons import Squadron
from game.theater import ControlPoint
from game.theater.player import Player
from .models import (
    AirWingConfigJs,
    AirWingFileResultJs,
    ConfigSideJs,
    FactionDoctrineJs,
    FactionJtacJs,
    FactionUnitJs,
    ConfigNewSquadronJs,
    ReplacePresetJs,
    SquadronConfigUpdateJs,
)
from ..airwing.models import AutoAssignJs, LiveryChoiceJs, SetLiveryJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext
from ..native.routes import require_bridge
from ..newgame.models import FactionSheetJs
from ..newgame.routes import NewGameContext

router: APIRouter = APIRouter(prefix="/air-wing-config/{target}")

AIR_WING_FILE_FILTER = "YAML (*.yaml *.yml)"
_ERRORS = command_error_responses(
    "when no campaign can be configured, or the change is refused"
)


class ConfigTarget(str, Enum):
    DRAFT = "draft"
    CAMPAIGN = "campaign"


class ConfigSide(str, Enum):
    BLUE = "blue"
    RED = "red"


def _game(target: ConfigTarget, game: Game | None = Depends(GameContext.get)) -> Game:
    if target is ConfigTarget.DRAFT:
        draft = NewGameContext.get().draft()
        if draft is None:
            raise CommandError("No new campaign is waiting for its air wing.")
        return draft
    if game is None:
        raise CommandError("No campaign is loaded.")
    if not game.settings.enable_air_wing_adjustments:
        raise CommandError("Enable Air Wing adjustments in the cheats first.")
    return game


def _coalition(game: Game, side: ConfigSide) -> Coalition:
    return game.coalition_for(Player.BLUE if side is ConfigSide.BLUE else Player.RED)


def _squadron(game: Game, squadron_id: UUID) -> Squadron:
    squadron = find_squadron(game, squadron_id)
    if squadron is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no squadron with ID {squadron_id}",
        )
    return squadron


def _base(coalition: Coalition, base_id: UUID) -> ControlPoint:
    for base in coalition.game.theater.control_points_for(coalition.player):
        if base.id == base_id:
            return base
    raise CommandError(f"The coalition has no base with ID {base_id}.")


def _reload_sim(target: ConfigTarget) -> None:
    if target is ConfigTarget.CAMPAIGN:
        GameContext.reload_sim()


@router.get(
    "",
    operation_id="get_air_wing_config",
    responses=_ERRORS,
)
@locked
def get_config(game: Game = Depends(_game)) -> AirWingConfigJs:
    """Squadrons of both coalitions, with everything they can change into."""
    return AirWingConfigJs(
        replans=game.turn != 0,
        sides=[
            ConfigSideJs.for_coalition(game, side.value, _coalition(game, side))
            for side in ConfigSide
        ],
    )


@router.patch(
    "/squadrons/{squadron_id}",
    operation_id="update_config_squadron",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def patch_squadron(
    target: ConfigTarget,
    squadron_id: UUID,
    body: SquadronConfigUpdateJs,
    game: Game = Depends(_game),
) -> None:
    squadron = _squadron(game, squadron_id)
    if body.name is not None:
        rename_squadron(squadron, body.name)
    if body.nickname is not None:
        set_nickname(squadron, body.nickname)
    if body.max_size is not None:
        set_max_size(squadron, body.max_size)
    if body.primary_task is not None:
        set_primary_task(squadron, flight_type_named(body.primary_task))
    if body.player_names is not None:
        set_player_names(squadron, body.player_names)
    if body.base_id is not None:
        move_to_base(game, squadron, _base(squadron.coalition, body.base_id))
    _reload_sim(target)


@router.put(
    "/squadrons/{squadron_id}/auto-assign",
    operation_id="set_config_squadron_auto_assign",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def put_auto_assign(
    squadron_id: UUID, body: AutoAssignJs, game: Game = Depends(_game)
) -> None:
    set_auto_assignable(
        _squadron(game, squadron_id), flight_type_named(body.task), body.enabled
    )


@router.get(
    "/squadrons/{squadron_id}/liveries",
    operation_id="get_config_squadron_liveries",
    responses=_ERRORS,
)
@locked
def get_liveries(
    squadron_id: UUID, game: Game = Depends(_game)
) -> list[LiveryChoiceJs]:
    choices = livery_choices(_squadron(game, squadron_id))
    return [LiveryChoiceJs.from_choice(choice) for choice in choices]


@router.put(
    "/squadrons/{squadron_id}/livery",
    operation_id="set_config_squadron_livery",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def put_livery(
    squadron_id: UUID, body: SetLiveryJs, game: Game = Depends(_game)
) -> None:
    set_squadron_livery(
        _squadron(game, squadron_id), body.livery_id, body.use_livery_set
    )


@router.post(
    "/squadrons/{squadron_id}/reroll-nickname",
    operation_id="reroll_config_squadron_nickname",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def post_reroll(squadron_id: UUID, game: Game = Depends(_game)) -> None:
    reroll_nickname(_squadron(game, squadron_id))


@router.post(
    "/squadrons/{squadron_id}/preset",
    operation_id="replace_config_squadron",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def post_preset(
    target: ConfigTarget,
    squadron_id: UUID,
    body: ReplacePresetJs,
    game: Game = Depends(_game),
) -> None:
    """Replaces the squadron with a preset of the same aircraft."""
    replace_with_preset(game, _squadron(game, squadron_id), body.preset)
    _reload_sim(target)


@router.delete(
    "/squadrons/{squadron_id}",
    operation_id="remove_config_squadron",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def delete_squadron(
    target: ConfigTarget,
    squadron_id: UUID,
    game: Game = Depends(_game),
) -> None:
    remove_squadron(game, _squadron(game, squadron_id))
    _reload_sim(target)


@router.post(
    "/sides/{side}/squadrons",
    operation_id="add_config_squadron",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def post_squadron(
    target: ConfigTarget,
    side: ConfigSide,
    body: ConfigNewSquadronJs,
    game: Game = Depends(_game),
) -> None:
    coalition = _coalition(game, side)
    try:
        aircraft = AircraftType.named(body.aircraft_id)
    except KeyError:
        raise CommandError(f"Unknown aircraft {body.aircraft_id}.")
    add_squadron(
        game,
        coalition,
        aircraft,
        _base(coalition, body.base_id),
        flight_type_named(body.primary_task),
        body.preset,
    )
    _reload_sim(target)


@router.post(
    "/sides/{side}/file/save",
    operation_id="save_air_wing_file",
    responses=_ERRORS,
)
@locks_game_itself
def post_save_file(
    side: ConfigSide,
    game: Game = Depends(_game),
    bridge: NativeBridge = Depends(require_bridge),
) -> AirWingFileResultJs:
    """Asks where to save the coalition's squadrons, then writes them."""
    with one_dialog():
        path = bridge.choose_save_file(
            "Save Air Wing", str(persistency.airwing_dir()), AIR_WING_FILE_FILTER
        )
    if path:
        with game_lock():
            save_air_wing(_coalition(game, side), Path(path))
    return AirWingFileResultJs(path=path)


@router.post(
    "/sides/{side}/file/load",
    operation_id="load_air_wing_file",
    responses=_ERRORS,
)
@locks_game_itself
def post_load_file(
    target: ConfigTarget,
    side: ConfigSide,
    game: Game = Depends(_game),
    bridge: NativeBridge = Depends(require_bridge),
) -> AirWingFileResultJs:
    """Asks for an air wing file, then replaces the coalition's squadrons with it."""
    with one_dialog():
        path = bridge.choose_file(
            "Load Air Wing", str(persistency.airwing_dir()), AIR_WING_FILE_FILTER
        )
    if path:
        with game_lock():
            load_air_wing(game, _coalition(game, side), Path(path))
            _reload_sim(target)
    return AirWingFileResultJs(path=path)


@router.get(
    "/sides/{side}/faction",
    operation_id="get_config_faction",
    responses=_ERRORS,
)
@locked
def get_faction(side: ConfigSide, game: Game = Depends(_game)) -> FactionSheetJs:
    return FactionSheetJs.for_faction(_coalition(game, side).faction)


@router.post(
    "/sides/{side}/faction/units",
    operation_id="add_config_faction_unit",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def post_faction_unit(
    side: ConfigSide, body: FactionUnitJs, game: Game = Depends(_game)
) -> None:
    """Adds a unit to the faction; it stays there for the rest of the campaign."""
    add_faction_unit(_coalition(game, side), body.group, body.unit)


@router.put(
    "/sides/{side}/faction/jtac",
    operation_id="set_config_faction_jtac",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def put_faction_jtac(
    side: ConfigSide, body: FactionJtacJs, game: Game = Depends(_game)
) -> None:
    _coalition(game, side).faction.has_jtac = body.has_jtac


@router.put(
    "/sides/{side}/faction/doctrine",
    operation_id="set_config_faction_doctrine",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_ERRORS,
)
@locked
def put_faction_doctrine(
    side: ConfigSide, body: FactionDoctrineJs, game: Game = Depends(_game)
) -> None:
    faction = _coalition(game, side).faction
    faction.doctrine = doctrine_named(faction, body.doctrine)

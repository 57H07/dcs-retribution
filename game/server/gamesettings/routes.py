"""Settings screen of the web UI (WEB-07.1): read the schema, change a setting."""

from fastapi import APIRouter, Depends

from game import Game
from game.commands import CommandError
from game.commands.settings import (
    needs_full_refresh,
    reset_settings_page,
    settings_pages,
    update_setting,
)
from game.gamelock import locked
from .models import SettingJs, SettingValueUpdateJs, SettingsJs, SettingsPageJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext, QtCallbacks, QtContext

router: APIRouter = APIRouter(prefix="/settings")


def _require_game(game: Game | None) -> Game:
    if game is None:
        raise CommandError("No campaign is loaded.")
    return game


def _refresh_qt(qt: QtCallbacks | None) -> None:
    if qt is not None and qt.game_changed is not None:
        qt.game_changed()


@router.get(
    "/",
    operation_id="get_settings",
    response_model=SettingsJs,
    responses=command_error_responses("No campaign is loaded."),
)
@locked
def get_settings(game: Game | None = Depends(GameContext.get)) -> SettingsJs:
    """Every settings page of the campaign: sections, controls, values, defaults.

    Generated from the metadata of `game/settings/settings.py`, plus the cheats and
    the Lua plugins, so a new setting needs no client code.
    """
    settings = _require_game(game).settings
    return SettingsJs(
        pages=[SettingsPageJs.from_page(page, settings) for page in settings_pages()]
    )


@router.put(
    "/values/{key}",
    operation_id="set_setting",
    response_model=SettingJs,
    responses={
        **command_error_responses("No campaign is loaded."),
        404: {"description": "Unknown setting."},
        422: {"description": "The value has the wrong type or is out of bounds."},
    },
)
@locked
def set_setting(
    key: str,
    update: SettingValueUpdateJs,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> SettingJs:
    """Changes one setting, with the side effects of the Qt settings window."""
    loaded = _require_game(game)
    entry = update_setting(loaded, key, update.value)
    if needs_full_refresh([entry]):
        _refresh_qt(qt)
    return SettingJs.from_entry(entry, loaded.settings)


@router.post(
    "/pages/{page_id}/reset",
    operation_id="reset_settings_page",
    response_model=SettingsPageJs,
    responses={
        **command_error_responses("No campaign is loaded."),
        404: {"description": "Unknown settings page."},
    },
)
@locked
def reset_page(
    page_id: str,
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> SettingsPageJs:
    """Puts every setting of a page back to its default value."""
    loaded = _require_game(game)
    page = reset_settings_page(loaded, page_id)
    if needs_full_refresh(list(page.entries())):
        _refresh_qt(qt)
    return SettingsPageJs.from_page(page, loaded.settings)

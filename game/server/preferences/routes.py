"""Install preferences and first start of the web UI (WEB-07.2).

Not tied to a campaign: these routes work with no game loaded.
"""

from fastapi import APIRouter

from game.commands.preferences import (
    apply_preferences,
    current_preferences,
    module_choices,
    set_owned_modules,
)
from game.gamelock import locked
from .models import (
    InstallPreferencesStateJs,
    InstallPreferencesUpdateJs,
    ModuleJs,
    OwnedModulesJs,
)
from ..commanderrors import command_error_responses

router: APIRouter = APIRouter(prefix="/preferences")


@router.get(
    "/",
    operation_id="get_install_preferences",
    response_model=InstallPreferencesStateJs,
)
@locked
def get_preferences() -> InstallPreferencesStateJs:
    """DCS folders and the other install preferences, what is wrong with them, and
    whether the first start setup must be shown."""
    return InstallPreferencesStateJs.from_preferences(current_preferences())


@router.put(
    "/",
    operation_id="set_install_preferences",
    response_model=InstallPreferencesStateJs,
    responses=command_error_responses(
        "when a folder is invalid, or the DCS installation folder is left empty "
        "without confirmation"
    ),
)
@locked
def set_preferences(update: InstallPreferencesUpdateJs) -> InstallPreferencesStateJs:
    """Validates and saves the preferences, like the Qt preferences window.

    Completing the first start also replaces MissionScripting.lua in the DCS
    installation. Port and web interface changes need a restart.
    """
    warning = apply_preferences(update.to_preferences(), update.allow_empty_install_dir)
    return InstallPreferencesStateJs.from_preferences(current_preferences(), warning)


@router.get(
    "/modules",
    operation_id="get_player_modules",
    response_model=list[ModuleJs],
)
@locked
def get_modules() -> list[ModuleJs]:
    """The aircraft the player can declare owning, and those already declared."""
    return [ModuleJs.from_choice(choice) for choice in module_choices()]


@router.put(
    "/modules",
    operation_id="set_player_modules",
    response_model=list[ModuleJs],
    responses=command_error_responses("when a module is not a flyable aircraft"),
)
@locked
def set_modules(update: OwnedModulesJs) -> list[ModuleJs]:
    """Saves the modules the player owns, which come first in the aircraft lists."""
    set_owned_modules(update.owned)
    return [ModuleJs.from_choice(choice) for choice in module_choices()]

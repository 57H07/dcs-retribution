"""Install preferences and first start (WEB-07.2): read, validate, apply.

Same checks as the Qt preferences window (`QLiberationPreferences.apply`): the Saved
Games folder must exist; the DCS installation folder must be a DCS installation, or
be left empty on purpose (Retribution then cannot replace MissionScripting.lua).
Preferences do not need a campaign: they work before any game is loaded.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from game import liberation_install
from .errors import CommandError

MAX_PORT = 2**16 - 1


@dataclass(frozen=True)
class InstallPreferences:
    saved_game_dir: str
    dcs_install_dir: str
    prefer_liberation_payloads: bool
    setup_preferences_on_every_start: bool
    server_port: int
    web_ui: bool


def current_preferences() -> InstallPreferences:
    return InstallPreferences(
        saved_game_dir=liberation_install.get_saved_game_dir(),
        dcs_install_dir=liberation_install.get_dcs_install_directory(),
        prefer_liberation_payloads=liberation_install.prefer_liberation_payloads(),
        setup_preferences_on_every_start=(
            liberation_install.setup_preferences_on_every_start()
        ),
        server_port=liberation_install.server_port(),
        web_ui=liberation_install.web_ui_preference(),
    )


def saved_games_problem(path: str) -> str | None:
    """Why `path` cannot be the DCS Saved Games folder, or None when it can."""
    if not path.strip():
        return "Choose your DCS Saved Games folder."
    if not os.path.isdir(path):
        return f"{path} is not a valid directory."
    return None


def install_dir_problem(path: str) -> str | None:
    """Why `path` cannot be the DCS installation folder, or None when it can.

    An empty path is not a problem here: it needs an explicit confirmation instead
    (see `apply_preferences`).
    """
    if not path.strip():
        return None
    if not os.path.isdir(path):
        return (
            f"{path} is not a valid directory. Retribution needs the DCS "
            "installation folder to replace Scripts/MissionScripting.lua."
        )
    if not os.path.isdir(os.path.join(path, "Scripts")):
        return f"{path} is not a DCS installation folder (it has no Scripts folder)."
    return None


EMPTY_INSTALL_DIR = (
    "The DCS installation folder is empty: Retribution cannot replace "
    "Scripts/MissionScripting.lua and will not work properly until you replace it "
    "yourself with resources/scripts/MissionScripting.lua. Confirm to leave it empty."
)


def needs_first_start() -> bool:
    """True when the first start setup must be shown: first launch, preferences
    file missing or unreadable, "setup on every start", or no valid Saved Games."""
    return (
        liberation_install.first_start_pending()
        or saved_games_problem(liberation_install.get_saved_game_dir()) is not None
    )


def validate(preferences: InstallPreferences, allow_empty_install_dir: bool) -> None:
    problem = saved_games_problem(preferences.saved_game_dir)
    if problem is None:
        problem = install_dir_problem(preferences.dcs_install_dir)
    if problem is None and not preferences.dcs_install_dir.strip():
        if not allow_empty_install_dir:
            problem = EMPTY_INSTALL_DIR
    if problem is None and not 1 <= preferences.server_port <= MAX_PORT:
        problem = f"The server port must be between 1 and {MAX_PORT}."
    if problem is not None:
        raise CommandError(problem)


def apply_preferences(
    preferences: InstallPreferences, allow_empty_install_dir: bool = False
) -> str | None:
    """Validate, apply and save the preferences.

    Completing the first start also replaces MissionScripting.lua in the DCS
    installation, as accepting the Qt first start window does. Returns a warning to
    show when that replacement failed (the preferences are saved anyway).
    """
    validate(preferences, allow_empty_install_dir)
    completes_first_start = needs_first_start()
    liberation_install.setup(
        preferences.saved_game_dir,
        preferences.dcs_install_dir,
        preferences.prefer_liberation_payloads,
        preferences.setup_preferences_on_every_start,
        preferences.server_port,
    )
    liberation_install.set_web_ui_preference(preferences.web_ui)
    liberation_install.save_config()
    if not completes_first_start:
        return None
    try:
        liberation_install.replace_mission_scripting_file()
    except Exception:
        logging.exception("Could not replace MissionScripting.lua")
        return (
            "Unable to modify the MissionScripting file, possibly for lack of "
            "rights. Run Retribution as administrator or replace the file yourself."
        )
    return None

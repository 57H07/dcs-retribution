"""Install preferences: DCS folders, payloads, server port, web UI (WEB-07.2).

Saved in `retribution_preferences.json` in the user data folder. They do not belong
to a campaign: they are read at startup, before any game is loaded. Shared by the
Qt preferences window and the `/preferences` API routes, so nothing here imports Qt.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from shutil import copyfile
from typing import Any

import dcs

from game import persistency

DEFAULT_SERVER_PORT = 16880


def _user_data_path() -> Path:
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "DCSRetribution"
        return Path.home() / "AppData" / "Local" / "DCSRetribution"

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "DCSRetribution"
    return Path.home() / ".local" / "share" / "DCSRetribution"


USER_PATH = _user_data_path()

PREFERENCES_PATH = USER_PATH / "retribution_preferences.json"

# Overrides the "web_ui" preference for one launch: 1/true/yes/on or 0/false/no/off.
WEB_UI_ENV_VAR = "RETRIBUTION_WEB_UI"

__dcs_saved_game_directory = ""
__dcs_installation_directory = ""
__last_save_file = ""
__ignore_empty_install_directory = False
__prefer_liberation_payloads = False
__setup_preferences_on_every_start = False
__server_port = DEFAULT_SERVER_PORT
__web_ui = False
# True from a startup that needs the first start setup until preferences are applied.
__first_start_pending = False


def _detect_saved_games_directory() -> str:
    try:
        saved_games: str = dcs.installation.get_dcs_saved_games_directory()
        if os.path.exists(saved_games + ".openbeta"):
            return saved_games + ".openbeta"
        return saved_games
    except Exception:
        return ""


def _detect_install_directory() -> str:
    try:
        return str(dcs.installation.get_dcs_install_directory())
    except Exception:
        return ""


def init() -> bool:
    """Load the preferences file. True when the first start setup must be shown."""
    global __dcs_saved_game_directory
    global __dcs_installation_directory
    global __last_save_file
    global __ignore_empty_install_directory
    global __prefer_liberation_payloads
    global __setup_preferences_on_every_start
    global __server_port
    global __web_ui
    global __first_start_pending

    __web_ui = False
    __last_save_file = ""
    __ignore_empty_install_directory = False
    __prefer_liberation_payloads = False
    __setup_preferences_on_every_start = False
    __server_port = DEFAULT_SERVER_PORT
    if PREFERENCES_PATH.exists():
        try:
            logging.debug("Loading Retribution preferences from %s", PREFERENCES_PATH)
            with PREFERENCES_PATH.open() as prefs:
                pref_data: dict[str, Any] = json.load(prefs)
            __dcs_saved_game_directory = pref_data["saved_game_dir"]
            __dcs_installation_directory = pref_data["dcs_install_dir"]
            __last_save_file = pref_data.get("last_save_file", "")
            __ignore_empty_install_directory = pref_data.get(
                "ignore_empty_install_directory", False
            )
            __prefer_liberation_payloads = pref_data.get(
                "prefer_liberation_payloads", False
            )
            __setup_preferences_on_every_start = pref_data.get(
                "setup_preferences_on_every_start", False
            )
            __server_port = pref_data.get("server_port", DEFAULT_SERVER_PORT)
            __web_ui = bool(pref_data.get("web_ui", False))
            is_first_start = bool(__setup_preferences_on_every_start)
        except (KeyError, TypeError, AttributeError, json.JSONDecodeError):
            __dcs_saved_game_directory = ""
            __dcs_installation_directory = ""
            is_first_start = True
    else:
        __dcs_saved_game_directory = _detect_saved_games_directory()
        __dcs_installation_directory = _detect_install_directory()
        is_first_start = True
    __first_start_pending = is_first_start
    persistency.setup(
        __dcs_saved_game_directory, __prefer_liberation_payloads, __server_port
    )
    return is_first_start


def setup(
    saved_game_dir: str,
    install_dir: str,
    prefer_liberation_payloads: bool,
    setup_preferences_on_every_start: bool,
    port: int,
) -> None:
    global __dcs_saved_game_directory
    global __dcs_installation_directory
    global __prefer_liberation_payloads
    global __setup_preferences_on_every_start
    global __server_port
    global __first_start_pending
    __dcs_saved_game_directory = saved_game_dir
    __dcs_installation_directory = install_dir
    __prefer_liberation_payloads = prefer_liberation_payloads
    __setup_preferences_on_every_start = setup_preferences_on_every_start
    __server_port = port
    __first_start_pending = False
    persistency.setup(saved_game_dir, prefer_liberation_payloads, port)


def first_start_pending() -> bool:
    """True when this launch needed the first start setup and it is not done yet."""
    return __first_start_pending


def setup_last_save_file(last_save_file: str) -> None:
    global __last_save_file
    __last_save_file = last_save_file


def save_config() -> None:
    pref_data = {
        "saved_game_dir": __dcs_saved_game_directory,
        "dcs_install_dir": __dcs_installation_directory,
        "last_save_file": __last_save_file,
        "ignore_empty_install_directory": __ignore_empty_install_directory,
        "prefer_liberation_payloads": __prefer_liberation_payloads,
        "setup_preferences_on_every_start": __setup_preferences_on_every_start,
        "server_port": __server_port,
        "web_ui": __web_ui,
    }
    PREFERENCES_PATH.parent.mkdir(exist_ok=True, parents=True)
    with PREFERENCES_PATH.open("w") as prefs:
        json.dump(pref_data, prefs, indent="  ")


def get_dcs_install_directory() -> str:
    return __dcs_installation_directory


def get_saved_game_dir() -> str:
    return __dcs_saved_game_directory


def prefer_liberation_payloads() -> bool:
    return __prefer_liberation_payloads


def setup_preferences_on_every_start() -> bool:
    return __setup_preferences_on_every_start


def server_port() -> int:
    return __server_port


def web_ui_preference() -> bool:
    """The saved "web_ui" preference, ignoring the environment override."""
    return __web_ui


def set_web_ui_preference(value: bool) -> None:
    global __web_ui
    __web_ui = value


def web_ui_enabled() -> bool:
    """True when the web UI fills the main window (WEB-00.3, off by default: W10).

    The RETRIBUTION_WEB_UI environment variable, when set to a known value, wins
    over the saved preference. Read at startup: changing it needs a restart.
    """
    override = os.environ.get(WEB_UI_ENV_VAR, "").strip().lower()
    if override in ("1", "true", "yes", "on"):
        return True
    if override in ("0", "false", "no", "off"):
        return False
    return web_ui_preference()


def ignore_empty_install_directory() -> bool:
    return __ignore_empty_install_directory


def set_ignore_empty_install_directory(value: bool) -> None:
    global __ignore_empty_install_directory
    __ignore_empty_install_directory = value


def get_last_save_file() -> str | None:
    if os.path.exists(__last_save_file):
        return __last_save_file
    return None


def replace_mission_scripting_file() -> None:
    install_dir = get_dcs_install_directory()
    mission_scripting_path = os.path.join(
        install_dir, "Scripts", "MissionScripting.lua"
    )
    liberation_scripting_path = "./resources/scripts/MissionScripting.lua"
    backup_scripting_path = "./resources/scripts/MissionScripting.original.lua"
    if install_dir != "" and os.path.isfile(mission_scripting_path):
        with open(mission_scripting_path, "r") as ms:
            current_file_content = ms.read()
        with open(liberation_scripting_path, "r") as libe_ms:
            liberation_file_content = libe_ms.read()

        # Save original file
        if current_file_content != liberation_file_content:
            copyfile(mission_scripting_path, backup_scripting_path)

        # Replace DCS file
        copyfile(liberation_scripting_path, mission_scripting_path)


def restore_original_mission_scripting() -> None:
    install_dir = get_dcs_install_directory()
    mission_scripting_path = os.path.join(
        install_dir, "Scripts", "MissionScripting.lua"
    )
    backup_scripting_path = "./resources/scripts/MissionScripting.original.lua"

    if (
        install_dir != ""
        and os.path.isfile(backup_scripting_path)
        and os.path.isfile(mission_scripting_path)
    ):
        copyfile(backup_scripting_path, mission_scripting_path)

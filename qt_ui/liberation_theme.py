import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from qt_ui.design_tokens import (
    GENERATED_QSS_DIR,
    TOKENS_PATH,
    DesignTokens,
    load_tokens,
    qss_file_name,
    widgets_qss_file_name,
)

global __theme_index

THEME_PREFERENCES_FILE_PATH = "liberation_theme.json"

STYLESHEETS_DIR = Path("resources/stylesheets")

# Theme of installs that predate the design tokens and never saved a theme.
LEGACY_DEFAULT_THEME_INDEX = 1

# Theme of fresh installs (GFX-01: dark by default).
DEFAULT_THEME_INDEX = 2


# New themes can be added here. Indices are persisted in
# liberation_theme.json, so never renumber an existing theme.
# - themeFile: stylesheet, relative to resources/stylesheets.
# - themeIcons: icon sub-folder of resources/ui/misc and resources/ui/conditions.
# - tokenVariant: design token variant (resources/design/tokens.json) used by
#   the map client and by widgets that need a token value outside the QSS.
THEMES: Dict[int, Dict[str, str]] = {
    0: {
        "themeName": "Vanilla",
        "themeFile": "windows-style.css",
        "themeIcons": "medium",
        "tokenVariant": "light",
    },
    1: {
        "themeName": "DCS World",
        "themeFile": "style-dcs.css",
        "themeIcons": "light",
        "tokenVariant": "dark",
    },
    2: {
        "themeName": "Dark",
        "themeFile": (GENERATED_QSS_DIR / qss_file_name("dark"))
        .relative_to(STYLESHEETS_DIR)
        .as_posix(),
        "themeIcons": "light",
        "tokenVariant": "dark",
    },
    3: {
        "themeName": "Light",
        "themeFile": (GENERATED_QSS_DIR / qss_file_name("light"))
        .relative_to(STYLESHEETS_DIR)
        .as_posix(),
        "themeIcons": "medium",
        "tokenVariant": "light",
    },
}


def default_theme_index(existing_install: bool) -> int:
    """Theme used when no theme was ever saved.

    Existing installs keep the theme they had (the old default, "DCS World");
    fresh installs start in the dark theme.
    """
    return LEGACY_DEFAULT_THEME_INDEX if existing_install else DEFAULT_THEME_INDEX


def init(preferences_path: Optional[Path] = None):
    """Loads the saved theme.

    preferences_path is the Retribution preferences file: if it exists while no
    theme was saved, this is an existing install that keeps its theme.
    """
    global __theme_index

    if preferences_path is None:
        from game.liberation_install import PREFERENCES_PATH

        preferences_path = PREFERENCES_PATH

    __theme_index = DEFAULT_THEME_INDEX

    if os.path.isfile(THEME_PREFERENCES_FILE_PATH):
        try:
            with open(THEME_PREFERENCES_FILE_PATH) as prefs:
                pref_data = json.loads(prefs.read())
                __theme_index = pref_data["theme_index"]
                if __theme_index not in THEMES:
                    raise ValueError(f"Unknown theme index {__theme_index}")
                set_theme_index(__theme_index)
                save_theme_config()
        except:
            # is this necessary?
            set_theme_index(DEFAULT_THEME_INDEX)
            logging.exception("Unable to change theme")
    else:
        existing_install = preferences_path.exists()
        set_theme_index(default_theme_index(existing_install))
        logging.info(
            "No %s: using the %s theme (%s install)",
            THEME_PREFERENCES_FILE_PATH,
            get_theme_name(),
            "existing" if existing_install else "new",
        )
        if existing_install:
            # Pin the theme the user has always had so it survives later
            # default changes.
            save_theme_config()


# set theme index then use save_theme_config to save to file
def set_theme_index(x):
    global __theme_index
    __theme_index = x


# get theme index to reference other theme properties(themeName, themeFile, themeIcons)
def get_theme_index():
    global __theme_index
    return __theme_index


# get theme name based on current index
def get_theme_name():
    theme_name = THEMES[get_theme_index()]["themeName"]
    return theme_name


# get theme icon sub-folder name based on current index
def get_theme_icons():
    theme_icons = THEMES[get_theme_index()]["themeIcons"]
    return str(theme_icons)


# get theme stylesheet css based on current index
def get_theme_css_file():
    theme_file = THEMES[get_theme_index()]["themeFile"]
    return str(theme_file)


def get_token_variant() -> str:
    """Design token variant ("dark" or "light") matching the current theme."""
    return THEMES[get_theme_index()]["tokenVariant"]


@lru_cache(maxsize=1)
def _design_tokens() -> DesignTokens:
    # Relative to the working directory, like every other resource, so that
    # the packaged release finds it too.
    return load_tokens(TOKENS_PATH)


def get_token(name: str) -> str:
    """Value of a design token for the current theme, e.g. "color-text-accent".

    For colours the stylesheet cannot reach (painted widgets, charts, palette).
    Read it when painting or on theme_manager's theme_changed signal so that
    it follows a theme switch.
    """
    return _design_tokens().variant(get_token_variant())[name]


def load_stylesheet() -> str:
    """Returns the Qt stylesheet of the current theme.

    That is the theme's own stylesheet followed by the semantic widget states
    rendered with its token variant (generated/widgets-<variant>.qss). Apply it
    with QApplication.setStyleSheet(); see qt_ui.theme_manager.
    """
    paths = [
        STYLESHEETS_DIR / get_theme_css_file(),
        GENERATED_QSS_DIR / widgets_qss_file_name(get_token_variant()),
    ]
    logging.info("Loading stylesheets: %s", ", ".join(str(p) for p in paths))
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


# save current theme index to json file
def save_theme_config():
    pref_data = {"theme_index": get_theme_index()}
    with open(THEME_PREFERENCES_FILE_PATH, "w") as prefs:
        prefs.write(json.dumps(pref_data))

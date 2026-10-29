"""Campaign settings commands (WEB-07.1): the settings screen read and written.

The screen is generated from metadata, so a setting added to `game/settings/settings.py`
shows up in the web UI with no client code:

* every `Settings` field declared with an option helper (`boolean_option`,
  `choices_option`, `bounded_int_option`, `bounded_float_option`, `minutes_option`),
  on its page and section, in declaration order (as `QSettingsWindow` lays them out);
* the cheat toggles of the Qt "Cheat Menu" page (plain fields, see `_CHEATS`);
* the Lua plugins (enable toggles) and their options (`game/plugins`).

Each entry has a key (the field name, `plugin.<id>` or `plugin-option.<id>.<option>`)
and exchanges JSON values with the client: a bool, the text of a choice, a number, or
a number of minutes. Writes apply the same side effects as the Qt window.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, fields
from datetime import timedelta
from http import HTTPStatus
from typing import Any, TYPE_CHECKING, Union

from game.settings import (
    BooleanOption,
    BoundedFloatOption,
    BoundedIntOption,
    ChoicesOption,
    MinutesOption,
    OptionDescription,
    Settings,
)
from game.settings.optiondescription import SETTING_DESCRIPTION_KEY
from .errors import CommandError

if TYPE_CHECKING:
    from game.game import Game
    from game.plugins.luaplugin import LuaPlugin, LuaPluginOption

SettingValue = Union[bool, int, float, str]

CHEATS_PAGE = "Cheat Menu"
PLUGINS_PAGE = "LUA Plugins"
PLUGIN_OPTIONS_PAGE = "LUA Plugins Options"

# The cheat toggles are plain fields (their Qt page also has money buttons, which
# are not settings), so their labels live here, copied from CheatSettingsBox.
_CHEATS_SECTION = "Cheat Settings"
_CHEATS: tuple[tuple[str, str], ...] = (
    ("enable_frontline_cheats", "Enable Frontline Cheats"),
    ("enable_base_capture_cheat", "Enable Base Capture Cheat"),
    ("enable_runway_state_cheat", "Enable Runway State Cheat"),
    ("enable_transfer_cheat", "Enable Instant Squadron Transfer Cheat"),
    ("enable_air_wing_adjustments", "Enable Air Wing adjustments"),
    ("enable_enemy_buy_sell", "Enable OPFOR Buy/Sell actions Cheat"),
)

# Settings fields that are not shown by any settings screen.
HIDDEN_FIELDS = frozenset({"version", "plugins", "only_player_takeoff"})

_DEFAULTS = Settings()


@dataclass(frozen=True)
class SettingEntry:
    """One control of the settings screen, with its accessors on `Settings`."""

    key: str
    label: str
    kind: str  # "bool" | "choice" | "int" | "float" | "minutes"
    default: SettingValue
    read: Callable[[Settings], SettingValue] = field(repr=False)
    write: Callable[[Settings, SettingValue], None] = field(repr=False)
    detail: str | None = None
    tooltip: str | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    choices: tuple[str, ...] | None = None
    # Changing it recomputes derived game state (Qt: `QSettingsWidget.applySettings`).
    refreshes_game: bool = False

    def value(self, settings: Settings) -> SettingValue:
        return self.read(settings)

    def is_modified(self, settings: Settings) -> bool:
        value = self.read(settings)
        if isinstance(value, float) or isinstance(self.default, float):
            return not math.isclose(float(value), float(self.default), abs_tol=1e-9)
        return value != self.default


@dataclass(frozen=True)
class SettingsSection:
    name: str
    description: str | None
    entries: list[SettingEntry]


@dataclass(frozen=True)
class SettingsPage:
    id: str
    name: str
    sections: list[SettingsSection]

    def entries(self) -> Iterator[SettingEntry]:
        for section in self.sections:
            yield from section.entries


def page_id(name: str) -> str:
    """URL-safe id of a page: "Campaign Management" -> "campaign-management"."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# --- entries from metadata ----------------------------------------------------


def _field_entry(name: str, description: OptionDescription) -> SettingEntry:
    common: dict[str, Any] = dict(
        key=name,
        label=description.text,
        detail=description.detail,
        tooltip=description.tooltip,
        refreshes_game=description.causes_expensive_game_update,
    )
    if isinstance(description, BooleanOption):
        invert = description.invert

        def read_bool(s: Settings) -> SettingValue:
            return bool(getattr(s, name)) != invert

        def write_bool(s: Settings, value: SettingValue) -> None:
            setattr(s, name, bool(value) != invert)

        return SettingEntry(
            kind="bool",
            default=read_bool(_DEFAULTS),
            read=read_bool,
            write=write_bool,
            **common,
        )
    if isinstance(description, ChoicesOption):
        choices = description.choices

        def read_choice(s: Settings) -> SettingValue:
            value = getattr(s, name)
            for text, choice in choices.items():
                if choice == value:
                    return text
            # A value no choice stands for: show it as the default (Qt would fail).
            return description.text_for_value(getattr(_DEFAULTS, name))

        def write_choice(s: Settings, value: SettingValue) -> None:
            setattr(s, name, choices[str(value)])

        return SettingEntry(
            kind="choice",
            default=read_choice(_DEFAULTS),
            read=read_choice,
            write=write_choice,
            choices=tuple(choices),
            **common,
        )
    if isinstance(description, BoundedFloatOption):
        divisor = description.divisor

        def write_float(s: Settings, value: SettingValue) -> None:
            # Same precision as the Qt spin slider (an integer spinner / divisor).
            setattr(s, name, round(float(value) * divisor) / divisor)

        return SettingEntry(
            kind="float",
            default=float(getattr(_DEFAULTS, name)),
            read=lambda s: float(getattr(s, name)),
            write=write_float,
            min=description.min,
            max=description.max,
            step=1 / divisor,
            **common,
        )
    if isinstance(description, BoundedIntOption):
        return SettingEntry(
            kind="int",
            default=int(getattr(_DEFAULTS, name)),
            read=lambda s: int(getattr(s, name)),
            write=lambda s, value: setattr(s, name, int(value)),
            min=description.min,
            max=description.max,
            step=1,
            **common,
        )
    if isinstance(description, MinutesOption):

        def read_minutes(s: Settings) -> SettingValue:
            return int(getattr(s, name).total_seconds() // 60)

        return SettingEntry(
            kind="minutes",
            default=read_minutes(_DEFAULTS),
            read=read_minutes,
            write=lambda s, value: setattr(s, name, timedelta(minutes=int(value))),
            min=description.min,
            max=description.max,
            step=1,
            **common,
        )
    raise TypeError(f"Unhandled option type: {description}")


def _metadata_pages() -> Iterator[SettingsPage]:
    for page in Settings.pages():
        sections = [
            SettingsSection(
                section,
                None,
                [
                    _field_entry(name, description)
                    for name, description in Settings.fields(page, section)
                ],
            )
            for section in Settings.sections(page)
        ]
        yield SettingsPage(page_id(page), page, sections)


def _cheats_page() -> SettingsPage:
    def entry(name: str, label: str) -> SettingEntry:
        return SettingEntry(
            key=name,
            label=label,
            kind="bool",
            default=bool(getattr(_DEFAULTS, name)),
            read=lambda s: bool(getattr(s, name)),
            write=lambda s, value: setattr(s, name, bool(value)),
            refreshes_game=True,
        )

    section = SettingsSection(
        _CHEATS_SECTION, None, [entry(name, label) for name, label in _CHEATS]
    )
    return SettingsPage(page_id(CHEATS_PAGE), CHEATS_PAGE, [section])


def _plugin_value_accessors(
    identifier: str, default: Any
) -> tuple[
    Callable[[Settings], SettingValue], Callable[[Settings, SettingValue], None]
]:
    def read(s: Settings) -> SettingValue:
        return s.plugins.get(s.plugin_settings_key(identifier), default)

    def write(s: Settings, value: SettingValue) -> None:
        s.set_plugin_option(identifier, value)

    return read, write


def _plugin_pages() -> list[SettingsPage]:
    from game.plugins import LuaPluginManager

    plugins = LuaPluginManager.plugins()

    toggles = [_plugin_toggle(plugin) for plugin in plugins if plugin.show_in_ui]

    option_sections = []
    for plugin in plugins:
        if not plugin.options:
            continue
        entries = []
        for option in plugin.options:
            entry = _plugin_option_entry(option.identifier, option)
            if entry is not None:
                entries.append(entry)
        option_sections.append(
            SettingsSection(plugin.name, plugin.description or None, entries)
        )

    return [
        SettingsPage(
            page_id(PLUGINS_PAGE),
            PLUGINS_PAGE,
            [SettingsSection("Plugins", None, toggles)],
        ),
        SettingsPage(
            page_id(PLUGIN_OPTIONS_PAGE), PLUGIN_OPTIONS_PAGE, option_sections
        ),
    ]


def _plugin_toggle(plugin: LuaPlugin) -> SettingEntry:
    default = bool(plugin.definition.enabled_by_default)
    read, write = _plugin_value_accessors(plugin.identifier, default)
    return SettingEntry(
        key=f"plugin.{plugin.identifier}",
        label=plugin.name,
        kind="bool",
        default=default,
        read=read,
        write=lambda s, v: write(s, bool(v)),
    )


def _plugin_option_entry(
    identifier: str, option: LuaPluginOption
) -> SettingEntry | None:
    default = option.value
    read, write = _plugin_value_accessors(identifier, default)
    common: dict[str, Any] = dict(
        key=f"plugin-option.{identifier}", label=option.name, read=read
    )
    # Same widgets as PluginOptionsBox: decided by the type of the default value.
    if type(default) is bool:
        return SettingEntry(
            kind="bool",
            default=default,
            write=lambda s, v: write(s, bool(v)),
            **common,
        )
    if type(default) is int:
        return SettingEntry(
            kind="int",
            default=default,
            write=lambda s, v: write(s, int(v)),
            min=option.min,
            max=option.max,
            step=1,
            **common,
        )
    if type(default) is float:
        return SettingEntry(
            kind="float",
            default=default,
            write=lambda s, v: write(s, float(v)),
            min=option.min,
            max=option.max,
            step=0.01,
            **common,
        )
    return None  # Qt shows no control for other types either.


def settings_pages() -> list[SettingsPage]:
    """Every page of the settings screen, in the order of the Qt window."""
    return [*_metadata_pages(), _cheats_page(), *_plugin_pages()]


def described_fields() -> Iterator[str]:
    """Names of the `Settings` fields that carry option metadata."""
    for settings_field in fields(Settings):
        if SETTING_DESCRIPTION_KEY in settings_field.metadata:
            yield settings_field.name


# --- commands -------------------------------------------------------------------


def _invalid(message: str) -> CommandError:
    return CommandError(message, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)


def validate_value(entry: SettingEntry, value: SettingValue) -> SettingValue:
    """The value to store for `entry`, or CommandError (422) when it is not valid."""
    if entry.kind == "bool":
        if not isinstance(value, bool):
            raise _invalid(f"{entry.label}: expected on or off.")
        return value
    if entry.kind == "choice":
        assert entry.choices is not None
        if not isinstance(value, str) or value not in entry.choices:
            raise _invalid(
                f"{entry.label}: {value!r} is not one of " + ", ".join(entry.choices)
            )
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _invalid(f"{entry.label}: expected a number.")
    if entry.kind in ("int", "minutes"):
        if not float(value).is_integer():
            raise _invalid(f"{entry.label}: expected a whole number.")
        value = int(value)
    elif not math.isfinite(value):
        raise _invalid(f"{entry.label}: expected a number.")
    if (entry.min is not None and value < entry.min) or (
        entry.max is not None and value > entry.max
    ):
        raise _invalid(
            f"{entry.label}: must be between {_number(entry.min)} and "
            f"{_number(entry.max)}."
        )
    return value


def _number(value: float | None) -> str:
    if value is None:
        return "?"
    return str(int(value)) if float(value).is_integer() else str(value)


def find_setting(key: str) -> SettingEntry:
    for page in settings_pages():
        for entry in page.entries():
            if entry.key == key:
                return entry
    raise CommandError(f"Unknown setting {key}.", status_code=HTTPStatus.NOT_FOUND)


def find_page(identifier: str) -> SettingsPage:
    for page in settings_pages():
        if page.id == identifier:
            return page
    raise CommandError(
        f"Unknown settings page {identifier}.", status_code=HTTPStatus.NOT_FOUND
    )


def update_setting(game: Game, key: str, value: SettingValue) -> SettingEntry:
    """Changes one setting of the campaign, as the Qt settings window does.

    Returns the entry changed. Raises CommandError: 404 for an unknown key, 422 for
    a value of the wrong type or out of bounds.
    """
    entry = find_setting(key)
    entry.write(game.settings, validate_value(entry, value))
    apply_settings_side_effects(game, [entry])
    return entry


def reset_settings_page(game: Game, identifier: str) -> SettingsPage:
    """Puts every setting of a page back to its default value."""
    page = find_page(identifier)
    entries = list(page.entries())
    for entry in entries:
        entry.write(game.settings, entry.default)
    apply_settings_side_effects(game, entries)
    return page


def apply_settings_side_effects(game: Game, entries: list[SettingEntry]) -> None:
    """What the Qt window does after a change, beyond storing the value."""
    keys = {entry.key for entry in entries}
    if "use_bandit_clouds" in keys:
        apply_mod_settings(game.settings)
    if any(entry.refreshes_game for entry in entries):
        refresh_after_settings_change(game)


def needs_full_refresh(entries: list[SettingEntry]) -> bool:
    """True when the Qt widgets must reload the game (Qt: `updateGame`)."""
    return any(entry.refreshes_game for entry in entries)


def refresh_after_settings_change(game: Game) -> None:
    """Recomputes what expensive settings and cheats change, and publishes it.

    Shared with `QSettingsWidget.applySettings`, which also reloads the Qt widgets.
    """
    from game.server import EventStream
    from game.sim import GameUpdateEvents

    events = GameUpdateEvents()
    game.compute_unculled_zones(events)
    EventStream.put_nowait(events)


def apply_mod_settings(settings: Settings) -> None:
    """Loads or unloads the cloud presets of the Bandit clouds mod."""
    from pydcs_extensions import BanditClouds

    if settings.use_bandit_clouds:
        BanditClouds.activate()
    else:
        BanditClouds.deactivate()

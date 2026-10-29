"""WEB-07.1: settings screen generated from metadata (schema, update, reset)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import MutableMapping
from dataclasses import fields
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from game.commands import CommandError
from game.commands.settings import (
    CHEATS_PAGE,
    HIDDEN_FIELDS,
    PLUGIN_OPTIONS_PAGE,
    PLUGINS_PAGE,
    _field_entry,
    described_fields,
    page_id,
    settings_pages,
    update_setting,
)
from game.plugins import LuaPluginManager
from game.server import GameContext
from game.server.app import app
from game.server.dependencies import QtCallbacks, QtContext
from game.server.eventstream import EventStream
from game.server.security import ApiKeyManager
from game.settings import BooleanOption, NightMissions, Settings
from game.sim import GameUpdateEvents


class _FakeGame:
    """Stands in for Game: real Settings, records the derived-state recomputations."""

    def __init__(self) -> None:
        self.settings = Settings()
        self.unculled_recomputed = 0

    def compute_unculled_zones(self, events: GameUpdateEvents) -> None:
        self.unculled_recomputed += 1


@pytest.fixture
def game(monkeypatch: pytest.MonkeyPatch) -> _FakeGame:
    fake = _FakeGame()
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=fake), raising=False
    )
    monkeypatch.setattr(QtContext, "_callbacks", None)
    return fake


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[GameUpdateEvents]:
    events: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", events.append)
    return events


def _request(method: str, path: str, body: Any = None) -> tuple[int, Any]:
    """One request through the whole ASGI app (routing, lock, errors, JSON)."""
    messages: list[MutableMapping[str, Any]] = []
    payload = b"" if body is None else json.dumps(body).encode()

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"x-api-key", ApiKeyManager.key().encode()),
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    raw = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(raw) if raw else None


def _put(key: str, value: Any) -> tuple[int, Any]:
    return _request("PUT", f"/settings/values/{key}", {"value": value})


def _schema_keys(schema: dict[str, Any]) -> list[str]:
    return [
        setting["key"]
        for page in schema["pages"]
        for section in page["sections"]
        for setting in section["settings"]
    ]


# --- schema: every setting the Qt window shows ---------------------------------


def test_schema_lists_every_qt_page_in_qt_order() -> None:
    names = [page.name for page in settings_pages()]
    assert names == [*Settings.pages(), CHEATS_PAGE, PLUGINS_PAGE, PLUGIN_OPTIONS_PAGE]
    assert len({page.id for page in settings_pages()}) == len(names)


def test_schema_has_every_described_setting_once_in_its_page_and_section() -> None:
    by_key = {}
    for page in settings_pages():
        for section in page.sections:
            for entry in section.entries:
                assert entry.key not in by_key, entry.key
                by_key[entry.key] = (page.name, section.name, entry)
    for page_name in Settings.pages():
        for section_name in Settings.sections(page_name):
            for name, description in Settings.fields(page_name, section_name):
                shown_page, shown_section, shown = by_key[name]
                assert (shown_page, shown_section) == (page_name, section_name)
                assert shown.label == description.text
                assert shown.detail == description.detail


def test_every_settings_field_is_shown_or_explicitly_hidden() -> None:
    """A new field must either use an option helper or be listed as hidden."""
    shown = {entry.key for page in settings_pages() for entry in page.entries()}
    for settings_field in fields(Settings):
        assert (
            settings_field.name in shown or settings_field.name in HIDDEN_FIELDS
        ), f"{settings_field.name} is neither on a settings page nor hidden"
    assert set(described_fields()) <= shown


def test_schema_has_every_visible_plugin_and_plugin_option() -> None:
    shown = {entry.key for page in settings_pages() for entry in page.entries()}
    for plugin in LuaPluginManager.plugins():
        assert (f"plugin.{plugin.identifier}" in shown) == plugin.show_in_ui
        for option in plugin.options:
            if type(option.value) in (bool, int, float):
                assert f"plugin-option.{option.identifier}" in shown


def test_controls_are_typed_from_the_metadata() -> None:
    entries = {
        entry.key: entry for page in settings_pages() for entry in page.entries()
    }

    skill = entries["player_skill"]
    assert skill.kind == "choice"
    assert skill.choices == ("Average", "Good", "High", "Excellent")
    assert skill.default == "High"

    income = entries["player_income_multiplier"]
    assert (income.kind, income.min, income.max, income.step) == ("float", 0, 5, 0.1)

    culling = entries["perf_culling_distance"]
    assert (culling.kind, culling.min, culling.max) == ("int", 10, 10000)
    assert culling.refreshes_game

    barcap = entries["desired_barcap_mission_duration"]
    assert (barcap.kind, barcap.default, barcap.min, barcap.max) == (
        "minutes",
        60,
        30,
        150,
    )

    assert entries["manpads"].kind == "bool"
    assert entries["enable_frontline_cheats"].refreshes_game


def test_inverted_boolean_shows_and_stores_the_opposite() -> None:
    entry = _field_entry(
        "manpads", BooleanOption("p", "s", "No manpads", None, None, False, True)
    )
    settings = Settings()
    assert settings.manpads is True
    assert entry.value(settings) is False
    entry.write(settings, True)
    assert settings.manpads is False


# --- GET /settings ------------------------------------------------------------


def test_get_settings_returns_values_defaults_and_modified(game: _FakeGame) -> None:
    game.settings.night_day_missions = NightMissions.OnlyNight
    status, body = _request("GET", "/settings/")
    assert status == 200
    keys = _schema_keys(body)
    assert set(described_fields()) <= set(keys)
    setting = next(
        s
        for page in body["pages"]
        for section in page["sections"]
        for s in section["settings"]
        if s["key"] == "night_day_missions"
    )
    assert setting["value"] == "Only generate night missions"
    assert setting["default"] == "Generate night and day missions"
    assert setting["modified"] is True
    assert setting["kind"] == "choice"


def test_get_settings_without_a_campaign_is_a_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    assert _request("GET", "/settings/") == (409, {"detail": "No campaign is loaded."})


# --- PUT /settings/values/{key} -----------------------------------------------


def test_set_boolean(game: _FakeGame) -> None:
    status, body = _put("manpads", False)
    assert status == 200
    assert (body["value"], body["modified"]) == (False, True)
    assert game.settings.manpads is False


def test_set_choice_stores_the_choice_value(game: _FakeGame) -> None:
    assert _put("night_day_missions", "Only generate day missions")[0] == 200
    assert game.settings.night_day_missions is NightMissions.OnlyDay
    assert _put("easy_communication", "Enforced off")[0] == 200
    assert game.settings.easy_communication is False


def test_set_float_is_rounded_like_the_qt_spin_slider(game: _FakeGame) -> None:
    status, body = _put("player_income_multiplier", 1.234)
    assert status == 200
    assert game.settings.player_income_multiplier == 1.2
    assert body["value"] == 1.2


def test_set_minutes(game: _FakeGame) -> None:
    assert _put("desired_barcap_mission_duration", 90)[0] == 200
    assert game.settings.desired_barcap_mission_duration == timedelta(minutes=90)


@pytest.mark.parametrize(
    "key,value",
    [
        ("perf_culling_distance", 5),
        ("perf_culling_distance", 10001),
        ("perf_culling_distance", 12.5),
        ("perf_culling_distance", "100"),
        ("perf_culling_distance", True),
        ("manpads", 1),
        ("player_skill", "Godlike"),
        ("player_income_multiplier", 5.5),
        ("desired_barcap_mission_duration", 10),
    ],
)
def test_invalid_values_are_a_422_and_change_nothing(
    game: _FakeGame, key: str, value: Any
) -> None:
    before = dict(game.settings.__dict__)
    status, body = _put(key, value)
    assert status == 422
    assert isinstance(body["detail"], str)
    assert game.settings.__dict__ == before


def test_unknown_setting_is_a_404(game: _FakeGame) -> None:
    assert _put("no_such_setting", True) == (
        404,
        {"detail": "Unknown setting no_such_setting."},
    )


def test_hidden_fields_cannot_be_written(game: _FakeGame) -> None:
    assert _put("only_player_takeoff", False)[0] == 404


def test_expensive_setting_recomputes_publishes_and_refreshes_qt(
    game: _FakeGame,
    published: list[GameUpdateEvents],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refreshed: list[bool] = []

    def ignore(_: Any) -> None:
        pass

    monkeypatch.setattr(
        QtContext,
        "_callbacks",
        QtCallbacks(
            ignore, ignore, ignore, ignore, game_changed=lambda: refreshed.append(True)
        ),
    )
    assert _put("perf_culling_distance", 200)[0] == 200
    assert game.unculled_recomputed == 1
    assert len(published) == 1
    assert refreshed == [True]

    assert _put("enable_frontline_cheats", True)[0] == 200
    assert game.settings.enable_frontline_cheats is True
    assert game.unculled_recomputed == 2
    assert refreshed == [True, True]

    assert _put("manpads", False)[0] == 200
    assert game.unculled_recomputed == 2
    assert refreshed == [True, True]


def test_bandit_clouds_are_loaded_and_unloaded(
    game: _FakeGame, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pydcs_extensions import BanditClouds

    calls: list[str] = []
    monkeypatch.setattr(BanditClouds, "activate", lambda: calls.append("on"))
    monkeypatch.setattr(BanditClouds, "deactivate", lambda: calls.append("off"))
    _put("use_bandit_clouds", True)
    _put("use_bandit_clouds", False)
    assert calls == ["on", "off"]


# --- plugins ----------------------------------------------------------------------


def _first_plugin_with(kind: type) -> tuple[str, Any]:
    for plugin in LuaPluginManager.plugins():
        for option in plugin.options:
            if type(option.value) is kind:
                return option.identifier, option
    raise AssertionError(f"no plugin option of type {kind}")


def test_plugin_toggle(game: _FakeGame) -> None:
    plugin = next(p for p in LuaPluginManager.plugins() if p.show_in_ui)
    value = not plugin.definition.enabled_by_default
    status, body = _put(f"plugin.{plugin.identifier}", value)
    assert status == 200
    assert body["modified"] is True
    assert game.settings.plugin_option(plugin.identifier) is value


def test_plugin_options_are_validated_against_their_bounds(game: _FakeGame) -> None:
    identifier, option = _first_plugin_with(int)
    assert _put(f"plugin-option.{identifier}", option.max + 1)[0] == 422
    assert _put(f"plugin-option.{identifier}", option.min)[0] == 200
    assert game.settings.plugin_option(identifier) == option.min


# --- POST /settings/pages/{id}/reset ------------------------------------------


def test_reset_page_puts_its_settings_back_to_default(game: _FakeGame) -> None:
    _put("manpads", False)
    _put("player_skill", "Average")
    _put("perf_culling_distance", 300)  # another page: untouched
    status, body = _request("POST", f"/settings/pages/{page_id('Difficulty')}/reset")
    assert status == 200
    assert body["name"] == "Difficulty"
    assert not any(s["modified"] for sec in body["sections"] for s in sec["settings"])
    assert game.settings.manpads is True
    assert game.settings.player_skill == "High"
    assert game.settings.perf_culling_distance == 300


def test_reset_plugin_options_page(game: _FakeGame) -> None:
    identifier, option = _first_plugin_with(int)
    _put(f"plugin-option.{identifier}", option.min)
    status, _ = _request(
        "POST", f"/settings/pages/{page_id(PLUGIN_OPTIONS_PAGE)}/reset"
    )
    assert status == 200
    assert game.settings.plugin_option(identifier) == option.value


def test_reset_unknown_page_is_a_404(game: _FakeGame) -> None:
    assert _request("POST", "/settings/pages/nowhere/reset")[0] == 404


def test_update_setting_command_refuses_unknown_keys() -> None:
    with pytest.raises(CommandError) as exc:
        update_setting(_FakeGame(), "nope", True)  # type: ignore[arg-type]
    assert exc.value.status_code == 404

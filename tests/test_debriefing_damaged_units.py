from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from game.debriefing import Debriefing, StateData
from game.settings import Settings
from game.unitmap import UnitMap


def _unit_map() -> UnitMap:
    unit_map = MagicMock()
    unit_map.flight.return_value = None
    return cast(UnitMap, unit_map)


def _parse(data: dict[str, Any]) -> StateData:
    return StateData.from_json(data, _unit_map())


def test_damaged_units_parsed() -> None:
    state = _parse(
        {
            "mission_ended": True,
            "damaged_units": [
                {"name": "Blue F-16 #1", "life": 0.65},
                {"name": "SA-11 TELAR", "life": 0.1},
            ],
        }
    )
    assert state.damaged_units == {"Blue F-16 #1": 0.65, "SA-11 TELAR": 0.1}


def test_old_state_without_damaged_units_is_valid() -> None:
    state = _parse(
        {
            "mission_ended": True,
            "crash_events": [],
            "dead_events": ["tank"],
            "base_capture_events": [],
            "unit_lost_events": [],
            "kill_events": [],
            "destroyed_objects_positions": [],
        }
    )
    assert state.damaged_units == {}
    assert state.killed_ground_units == ["tank"]


def test_empty_lua_table_encoded_as_object_is_accepted() -> None:
    # json.lua may encode an empty table as {} rather than [].
    assert _parse({"damaged_units": {}}).damaged_units == {}


def test_killed_units_are_not_reported_damaged() -> None:
    state = _parse(
        {
            "dead_events": ["tank"],
            "damaged_units": [
                {"name": "tank", "life": 0.2},
                {"name": "truck", "life": 0.5},
            ],
        }
    )
    assert state.damaged_units == {"truck": 0.5}


@pytest.mark.parametrize(
    "entry",
    [
        "not a dict",
        {"life": 0.5},
        {"name": "x"},
        {"name": "x", "life": "abc"},
        {"name": "x", "life": None},
        {"name": "x", "life": True},
        {"name": "x", "life": float("nan")},
        {"name": "x", "life": 1.0},
        {"name": "x", "life": 1.5},
    ],
)
def test_malformed_or_undamaged_entries_are_skipped(entry: Any) -> None:
    assert _parse({"damaged_units": [entry]}).damaged_units == {}


def test_ratio_is_clamped_and_lowest_life_wins() -> None:
    state = _parse(
        {
            "damaged_units": [
                {"name": 42, "life": -0.3},
                {"name": "ship", "life": 0.8},
                {"name": "ship", "life": 0.4},
                {"name": "ship", "life": 0.6},
            ]
        }
    )
    assert state.damaged_units == {"42": 0.0, "ship": 0.4}


def test_persistent_damage_setting_off_by_default() -> None:
    assert Settings().persistent_damage is False


def test_old_settings_load_with_persistent_damage_off() -> None:
    state = Settings().__dict__.copy()
    del state["persistent_damage"]
    settings = Settings.__new__(Settings)
    settings.__setstate__(state)
    assert settings.persistent_damage is False


def test_damaged_units_ignored_when_setting_off() -> None:
    state = _parse({"damaged_units": [{"name": "truck", "life": 0.5}]})
    assert Debriefing.persistent_damaged_units(state, False) == {}
    assert Debriefing.persistent_damaged_units(state, True) == {"truck": 0.5}

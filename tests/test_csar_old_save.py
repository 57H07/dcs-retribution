"""A save made before CSAR existed must load, with CSAR off (spec rules 1 and 2)."""

import pickle
from typing import Any

from game.coalition import Coalition
from game.db.gamedb import GameDb
from game.settings import Settings
from game.squadrons.pilot import Pilot, PilotStatus


def _pre_csar_settings_state() -> dict[str, Any]:
    state = dict(Settings().__dict__)
    for key in list(state):
        if "csar" in key:
            del state[key]
    return state


def _load_settings(state: dict[str, Any]) -> Settings:
    restored = Settings.__new__(Settings)
    restored.__setstate__(state)
    return restored


def test_new_settings_have_csar_disabled_for_both_sides() -> None:
    settings = Settings()
    assert settings.csar_enabled is False
    assert settings.csar_enabled_red is False


def test_old_settings_load_with_csar_disabled() -> None:
    state = _pre_csar_settings_state()
    assert "csar_enabled" not in state

    settings = _load_settings(state)

    assert settings.csar_enabled is False
    assert settings.csar_enabled_red is False
    # Every other CSAR option is readable, so nothing downstream raises.
    for key, value in Settings().__dict__.items():
        if "csar" in key:
            assert getattr(settings, key) == value


def test_old_settings_survive_a_pickle_round_trip() -> None:
    settings = _load_settings(_pre_csar_settings_state())
    restored = pickle.loads(pickle.dumps(settings))
    assert restored.csar_enabled is False
    assert restored.max_csar_flights == settings.max_csar_flights


def test_old_coalition_gets_an_empty_downed_pilot_list() -> None:
    coalition = Coalition.__new__(Coalition)
    coalition.__setstate__({"player": True})
    assert coalition.downed_pilots == []


def test_old_game_db_gets_a_downed_pilot_database() -> None:
    db = GameDb()
    state = dict(db.__dict__)
    del state["downed_pilots"]
    restored = GameDb.__new__(GameDb)
    restored.__setstate__(state)
    assert restored.downed_pilots is not None
    assert restored.flights is db.flights


def test_old_pilot_loads_as_an_active_pilot() -> None:
    pilot = Pilot("Old")
    state = dict(pilot.__dict__)
    del state["turns_until_available"]
    del state["held_at"]
    restored = Pilot.__new__(Pilot)
    restored.__setstate__(state)
    assert restored.status is PilotStatus.Active
    assert restored.turns_until_available == 0
    assert restored.held_at is None

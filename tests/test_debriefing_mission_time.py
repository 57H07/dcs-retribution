"""The DCS clock in state.json, origin of the live package timeline."""

from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from game.debriefing import Debriefing, StateData
from game.unitmap import UnitMap


def _parse(data: dict[str, Any]) -> StateData:
    unit_map = MagicMock()
    unit_map.flight.return_value = None
    return StateData.from_json(data, cast(UnitMap, unit_map))


def test_mission_time_parsed() -> None:
    assert _parse({"mission_time": 30600.25}).mission_time == 30600.25
    assert _parse({"mission_time": 30600}).mission_time == 30600.0


@pytest.mark.parametrize("value", [None, "08:30", True, -1, float("nan"), [1]])
def test_missing_or_malformed_mission_time_is_unknown(value: Any) -> None:
    data = {} if value is None else {"mission_time": value}
    assert _parse(data).mission_time is None


def _elapsed(mission_time: float | None, start: datetime) -> float | None:
    # mission_elapsed only reads the state data and the mission start time.
    debriefing = SimpleNamespace(
        state_data=SimpleNamespace(mission_time=mission_time),
        game=SimpleNamespace(conditions=SimpleNamespace(start_time=start)),
    )
    return cast(float | None, Debriefing.mission_elapsed.fget(debriefing))  # type: ignore[attr-defined]


def test_mission_elapsed_counts_from_the_mission_start() -> None:
    start = datetime(2026, 6, 1, 8, 30, 0)
    assert _elapsed(8 * 3600 + 30 * 60 + 125.5, start) == 125.5


def test_mission_elapsed_keeps_counting_past_midnight() -> None:
    # timer.getAbsTime() goes on past 86400 on the next day.
    start = datetime(2026, 6, 1, 23, 50, 0)
    assert _elapsed(86400 + 5 * 60, start) == 15 * 60


def test_mission_elapsed_unknown_without_clock() -> None:
    assert _elapsed(None, datetime(2026, 6, 1, 8, 0, 0)) is None

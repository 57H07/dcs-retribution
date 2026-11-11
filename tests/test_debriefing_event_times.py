"""The times of the mission events in state.json, shown by the after-action report."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from game.debriefing import AirLosses, BaseCaptureEvent, Debriefing, StateData
from game.debriefingreport import ReportEvent, Tone, mission_clock, mission_events
from game.missiongenerator.triggergenerator import capture_event_script
from game.squadrons.pilot import KillCategory
from game.theater import ControlPoint, Player
from game.unitmap import UnitMap
from tests.test_lua_damaged_units import DCS_STUBS, PLUGIN_DIR


def _parse(data: dict[str, Any]) -> StateData:
    unit_map = MagicMock()
    unit_map.flight.return_value = None
    return StateData.from_json(data, cast(UnitMap, unit_map))


def test_event_times_parsed() -> None:
    state = _parse(
        {
            "unit_death_times": [
                {"name": "tank", "t": 30700.5},
                # A map object, reported with a numeric name.
                {"name": 1234, "t": 30800},
                # Listed twice: the first report dates the death.
                {"name": "tank", "t": 30900},
            ],
            "base_capture_times": [
                {"event": "id||2||Krymsk", "t": 31000},
                # Taken again later: the last capture is the one that counts.
                {"event": "id||2||Krymsk", "t": 32000},
            ],
        }
    )
    assert state.death_times == {"tank": 30700.5, "1234": 30800.0}
    assert state.capture_times == {"id||2||Krymsk": 32000.0}


@pytest.mark.parametrize(
    "entries",
    [
        None,
        {},  # an empty Lua table
        "nope",
        [None, "tank", {"name": "tank"}, {"t": 5}, {"name": "tank", "t": "08:30"}],
        [{"name": "tank", "t": True}, {"name": "tank", "t": -1}],
    ],
)
def test_missing_or_malformed_event_times_are_ignored(entries: Any) -> None:
    data = {} if entries is None else {"unit_death_times": entries}
    assert _parse(data).death_times == {}


def test_mission_clock() -> None:
    assert mission_clock(None) is None
    assert mission_clock(8 * 3600 + 30 * 60 + 5.9) == "08:30:05"
    # timer.getAbsTime() goes on past 86400 on the next day.
    assert mission_clock(86400 + 65) == "00:01:05"


def test_air_losses_and_kills_get_the_time_of_the_death() -> None:
    blue = SimpleNamespace(player=Player.BLUE)
    red = SimpleNamespace(player=Player.RED)
    viper = SimpleNamespace(
        flight=SimpleNamespace(
            squadron=blue, departure=SimpleNamespace(captured=Player.BLUE)
        ),
        pilot=SimpleNamespace(name="Lt. Moroz"),
    )
    mig = SimpleNamespace(
        flight=SimpleNamespace(
            squadron=red, departure=SimpleNamespace(captured=Player.RED)
        ),
        pilot=None,
    )
    undated = SimpleNamespace(
        flight=SimpleNamespace(
            squadron=red, departure=SimpleNamespace(captured=Player.RED)
        ),
        pilot=None,
    )
    units = {"viper": viper, "mig": mig, "undated": undated}
    unit_map = MagicMock()
    unit_map.flight.side_effect = units.get

    debriefing = Debriefing.__new__(Debriefing)
    debriefing.unit_map = unit_map
    debriefing.state_data = StateData.from_json(
        {
            "crash_events": ["mig", "undated"],
            "kill_attributions": [{"initiator": "viper", "target": "mig"}],
            "unit_death_times": [{"name": "mig", "t": 31000}],
        },
        unit_map,
    )

    losses = debriefing.dead_aircraft()
    assert sorted(losses.enemy, key=id) == sorted([mig, undated], key=id)
    assert debriefing.air_loss_times == {id(mig): 31000.0}

    [kill] = debriefing.attribute_kills()
    assert (kill.pilot, kill.category, kill.time) == (
        viper.pilot,
        KillCategory.Air,
        31000.0,
    )


def test_mission_events_are_dated_and_in_order() -> None:
    blue = SimpleNamespace(name="VF-11", player=Player.BLUE)
    red = SimpleNamespace(name="Red 1", player=Player.RED)

    def flight(squadron: Any, unit_type: str) -> Any:
        return SimpleNamespace(
            squadron=squadron, unit_type=unit_type, count=2, custom_name="Viper 1"
        )

    pilot = SimpleNamespace(name="Lt. Moroz")
    hornet = SimpleNamespace(flight=flight(blue, "F/A-18C"), pilot=pilot)
    mig = SimpleNamespace(flight=flight(red, "MiG-29A"), pilot=None)
    undated = SimpleNamespace(flight=flight(red, "Su-27"), pilot=None)
    cp = cast(ControlPoint, SimpleNamespace(name="Krymsk"))

    debriefing = Debriefing.__new__(Debriefing)
    debriefing.base_captures = [BaseCaptureEvent(cp, Player.BLUE, 33000.0)]
    debriefing.pilot_kills = [
        cast(
            Any,
            SimpleNamespace(
                pilot=pilot,
                flight=flight(blue, "F-16CM"),
                category=KillCategory.Air,
                time=31000.0,
            ),
        )
    ]
    debriefing.air_losses = AirLosses(
        player=[cast(Any, hornet)], enemy=[cast(Any, undated), cast(Any, mig)]
    )
    debriefing.air_loss_times = {id(hornet): 32000.0, id(mig): 31000.0}

    assert mission_events(debriefing) == [
        ReportEvent("08:36:40", "Lt. Moroz (Viper 1) scored an air kill", Tone.GOOD),
        ReportEvent("08:36:40", "Enemy MiG-29A shot down", Tone.GOOD),
        ReportEvent("08:53:20", "F/A-18C of VF-11 lost · Lt. Moroz", Tone.BAD),
        ReportEvent("09:10:00", "Krymsk captured", Tone.GOOD),
        ReportEvent(None, "Enemy Su-27 shot down", Tone.GOOD),
    ]


def test_event_times_written_to_state_json(tmp_path: Path) -> None:
    lupa = pytest.importorskip("lupa")
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(DCS_STUBS)
    lua.globals().dcsRetribution = lua.table(installPath=str(tmp_path))
    for script in ("json.lua", "dcs_retribution.lua"):
        lua.execute((PLUGIN_DIR / script).read_text(encoding="utf-8"))
    lua.execute("""
        local ev = world.event
        local mig = make_unit("mig", 0, 10)
        timer.now = 100
        fire(ev.S_EVENT_KILL, "target", mig)
        -- DCS reports the same death again, later, through other events.
        timer.now = 130
        fire(ev.S_EVENT_CRASH, "initiator", mig)
        fire(ev.S_EVENT_DEAD, "initiator", mig)
        timer.now = 200
        fire(ev.S_EVENT_UNIT_LOST, "initiator", make_unit("tank", 0, 10))
        timer.now = 300
    """)
    lua.execute(capture_event_script("id||2||Krymsk"))
    lua.execute('fire(world.event.S_EVENT_MISSION_END, "initiator", nil)')
    state_path = Path(lua.globals().debriefing_file_location)
    data = json.loads(state_path.read_text(encoding="utf-8"))

    assert data["base_capture_events"] == ["id||2||Krymsk"]
    state = _parse(data)
    assert state.death_times == {"mig": 30700.0, "tank": 30800.0}
    assert state.capture_times == {"id||2||Krymsk": 30900.0}


def test_no_event_times_without_events(tmp_path: Path) -> None:
    lupa = pytest.importorskip("lupa")
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(DCS_STUBS)
    lua.globals().dcsRetribution = lua.table(installPath=str(tmp_path))
    for script in ("json.lua", "dcs_retribution.lua"):
        lua.execute((PLUGIN_DIR / script).read_text(encoding="utf-8"))
    lua.execute('fire(world.event.S_EVENT_MISSION_END, "initiator", nil)')
    state_path = Path(lua.globals().debriefing_file_location)
    state = _parse(json.loads(state_path.read_text(encoding="utf-8")))
    assert state.death_times == {}
    assert state.capture_times == {}

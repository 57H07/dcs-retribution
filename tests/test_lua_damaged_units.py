"""Runs the base mission script under lupa with a stubbed DCS API to check that
damaged units end up in state.json in the shape StateData expects."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from game.debriefing import StateData

lupa = pytest.importorskip("lupa")

PLUGIN_DIR = Path(__file__).parent.parent / "resources" / "plugins" / "base"

DCS_STUBS = """
local function noop() end
mist = {
    Logger = { new = function() return { info = noop, error = noop } end },
    scheduleFunction = noop,
    addEventHandler = function(handler) test_event_handler = handler end,
    message = { add = noop },
    getHeading = function() return 0 end,
    DBs = {},
}
timer = { now = 0, scheduled = {} }
function timer.getTime() return timer.now end
function timer.scheduleFunction(f, arg, t)
    timer.scheduled[#timer.scheduled + 1] = { f = f, arg = arg }
end
function run_hit_refreshes()
    local pending = timer.scheduled
    timer.scheduled = {}
    for _, s in ipairs(pending) do
        if type(s.arg) == "string" then s.f(s.arg, timer.now) end
    end
end
world = { event = {
    S_EVENT_HIT = 2, S_EVENT_CRASH = 5, S_EVENT_DEAD = 8, S_EVENT_MISSION_END = 12,
    S_EVENT_KILL = 28, S_EVENT_UNIT_LOST = 30,
} }
Object = { Category = { UNIT = 1, WEAPON = 2, STATIC = 3, SCENERY = 5 } }
function Object.getCategory(o) return o.category end
units_by_name = {}
statics_by_name = {}
Unit = { getByName = function(name) return units_by_name[name] end }
StaticObject = { getByName = function(name) return statics_by_name[name] end }

local function base_object(name, category, life)
    local o = { name = name, category = category, life = life, exists = true }
    function o:getName() return self.name end
    function o:isExist() return self.exists end
    function o:getLife() return self.life end
    function o:getTypeName() return "stub" end
    function o:getPosition() return { p = { x = 0, y = 0, z = 0 } } end
    return o
end
function make_unit(name, life, life0)
    local o = base_object(name, Object.Category.UNIT, life)
    o.life0 = life0
    function o:getLife0() return self.life0 end
    function o:getDesc() return {} end
    units_by_name[name] = o
    return o
end
function make_static(name, life, desc_life)
    local o = base_object(name, Object.Category.STATIC, life)
    function o:getDesc() return { life = desc_life } end
    statics_by_name[name] = o
    return o
end
function make_scenery(name)
    return base_object(name, Object.Category.SCENERY, 1)
end
function fire(id, field, object)
    test_event_handler({ id = id, [field] = object })
end
"""


def _run_mission(tmp_path: Path) -> dict[str, Any]:
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(DCS_STUBS)
    lua.globals().dcsRetribution = lua.table(installPath=str(tmp_path))
    for script in ("json.lua", "dcs_retribution.lua"):
        lua.execute((PLUGIN_DIR / script).read_text(encoding="utf-8"))
    lua.execute("""
        local ev = world.event
        -- vehicle hit, damage applied a moment later
        local tank = make_unit("tank", 10, 10)
        fire(ev.S_EVENT_HIT, "target", tank)
        tank.life = 4
        run_hit_refreshes()
        -- static: initial life only available from getDesc()
        local depot = make_static("depot", 30, 100)
        fire(ev.S_EVENT_HIT, "target", depot)
        run_hit_refreshes()
        -- aircraft damaged, then despawned after landing: last ratio is kept
        local viper = make_unit("viper", 7, 10)
        fire(ev.S_EVENT_HIT, "target", viper)
        run_hit_refreshes()
        viper.exists = false
        units_by_name["viper"] = nil
        -- hit without damage is not reported
        fire(ev.S_EVENT_HIT, "target", make_unit("untouched", 10, 10))
        -- damaged then killed is not reported
        local sam = make_unit("sam", 2, 10)
        fire(ev.S_EVENT_HIT, "target", sam)
        fire(ev.S_EVENT_DEAD, "initiator", sam)
        -- scenery is ignored
        fire(ev.S_EVENT_HIT, "target", make_scenery("bridge"))
        fire(ev.S_EVENT_MISSION_END, "initiator", nil)
    """)
    state_path = Path(lua.globals().debriefing_file_location)
    return json.loads(state_path.read_text(encoding="utf-8"))


def test_damaged_units_written_to_state_json(tmp_path: Path) -> None:
    data = _run_mission(tmp_path)
    assert data["mission_ended"] is True
    by_name = {entry["name"]: entry["life"] for entry in data["damaged_units"]}
    assert by_name == pytest.approx({"tank": 0.4, "depot": 0.3, "viper": 0.7})

    unit_map = MagicMock()
    unit_map.flight.return_value = None
    state = StateData.from_json(data, unit_map)
    assert state.damaged_units == pytest.approx(
        {"tank": 0.4, "depot": 0.3, "viper": 0.7}
    )
    assert "sam" in state.killed_ground_units

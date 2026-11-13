"""Missions that scan the ground height of a DCS map with land.getHeight.

See `resources/heightmaps/README.md`: the scans become the height maps Retribution
ships. To add a map, add its pydcs terrain to `main` (with sane bounds: pydcs has
wrong ones for MarianaIslands).

Each mission runs a script at start that walks a grid over the map and writes, in
`Saved Games/DCS/Retribution/Heightmaps/`:

- `<name>.bin`: the heights, row after row (rows go north along x, each row east
  along y), as little-endian uint16 `round(height_m * 4) + 32768` (quarter metres);
- `<name>.json`: the grid (origin, step, size), written last: its presence means the
  scan finished.
- `<name>_points.json`: the exact height at a few check points.

Run with Retribution open: it unlocks io/lfs/os in DCS (MissionScripting.lua).
Usage: python make_scan_missions.py [step_m]   (default 100)
"""

from __future__ import annotations

import sys
from pathlib import Path

import dcs.terrain as terrains
from dcs import Mission
from dcs.action import DoScript
from dcs.translation import String
from dcs.triggers import TriggerStart

MISSIONS = Path.home() / "Saved Games" / "DCS" / "Missions"

# The JDAM targets of F14_Tuto_JDAM.miz: the DTC editor gave them 10 m.
CAUCASUS_CHECKS = [
    ("Tgt1", -328643.15585044, 631003.42266938),
    ("Tgt2", -328733.16352422, 631364.85975003),
    ("Tgt3", -327955.06648731, 631424.4580551),
    ("Tgt4", -327960.68439561, 631116.77584406),
]

LUA = r"""
local CFG = {
  name = "%(name)s", x0 = %(x0)d, y0 = %(y0)d, step = %(step)d,
  nx = %(nx)d, ny = %(ny)d, rows_per_call = %(rows)d,
}
local CHECKS = { %(checks)s }

local dir = lfs.writedir() .. [[Retribution\]]
lfs.mkdir(dir)
dir = dir .. [[Heightmaps\]]
lfs.mkdir(dir)
local base = dir .. CFG.name

local getHeight = land.getHeight
local floor, char, concat = math.floor, string.char, table.concat

local function say(text, seconds)
  trigger.action.outText("Height scan " .. CFG.name .. ": " .. text, seconds or 10)
  env.info("[heightscan] " .. CFG.name .. ": " .. text)
end

-- Exact heights at the check points, first.
do
  local parts = {}
  for _, c in ipairs(CHECKS) do
    local h = getHeight({ x = c[2], y = c[3] })
    parts[#parts + 1] = string.format('{"name": "%%s", "x": %%.3f, "y": %%.3f, "h": %%.3f}', c[1], c[2], c[3], h)
  end
  local f = io.open(base .. "_points.json", "w")
  f:write("[" .. concat(parts, ", ") .. "]")
  f:close()
end

os.remove(base .. ".json")
local out = io.open(base .. ".bin", "wb")
local row = 0
local started = os.clock()
local lastPercent = -1

local function scanRows()
  local last = math.min(row + CFG.rows_per_call, CFG.nx)
  local p = { x = 0, y = 0 }
  while row < last do
    p.x = CFG.x0 + row * CFG.step
    local parts = {}
    for j = 0, CFG.ny - 1 do
      p.y = CFG.y0 + j * CFG.step
      local v = floor(getHeight(p) * 4 + 0.5) + 32768
      if v < 0 then v = 0 elseif v > 65535 then v = 65535 end
      parts[j + 1] = char(v %% 256, floor(v / 256))
    end
    out:write(concat(parts))
    row = row + 1
  end
end

local function step(_, time)
  scanRows()
  local percent = floor(row * 100 / CFG.nx)
  if percent >= lastPercent + 5 then
    lastPercent = percent - percent %% 5
    say(string.format("%%d%%%% (%%.0f s)", percent, os.clock() - started), 5)
  end
  if row < CFG.nx then
    return time + 0.01
  end
  out:close()
  local header = io.open(base .. ".json", "w")
  header:write(string.format(
    '{"terrain": "%%s", "x0": %%d, "y0": %%d, "step": %%d, "nx": %%d, "ny": %%d, ' ..
    '"encoding": "uint16le, height_m * 4 + 32768", "seconds": %%.1f}',
    CFG.name, CFG.x0, CFG.y0, CFG.step, CFG.nx, CFG.ny, os.clock() - started))
  header:close()
  say("done, " .. base .. ".bin", 60)
  return nil
end

say(string.format("%%d x %%d points every %%d m", CFG.nx, CFG.ny, CFG.step))
timer.scheduleFunction(step, nil, timer.getTime() + 1)
"""


def lua(
    name: str,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    step: int,
    checks: list[tuple[str, float, float]],
) -> str:
    nx = int((x1 - x0) // step) + 1
    ny = int((y1 - y0) // step) + 1
    # About 200 000 heights per call keeps each frame short.
    rows = max(1, 200_000 // ny)
    return LUA % {
        "name": name,
        "x0": x0,
        "y0": y0,
        "step": step,
        "nx": nx,
        "ny": ny,
        "rows": rows,
        "checks": ", ".join(f'{{"{n}", {x}, {y}}}' for n, x, y in checks),
    }


def mission(terrain: terrains.Terrain, name: str, script: str) -> Path:
    m = Mission(terrain)
    trigger = TriggerStart(comment="Height scan")
    trigger.add_action(DoScript(String(script)))
    m.triggerrules.triggers.append(trigger)
    path = MISSIONS / f"Retribution_heightscan_{name}.miz"
    m.save(str(path))
    return path


def main() -> None:
    step = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    MISSIONS.mkdir(parents=True, exist_ok=True)

    # Quick test: 20 x 20 km around the JDAM targets near Batumi, every 10 m.
    tx, ty = CAUCASUS_CHECKS[0][1], CAUCASUS_CHECKS[0][2]
    print(
        mission(
            terrains.Caucasus(),
            "Caucasus_test",
            lua(
                "Caucasus_test",
                tx - 10000,
                tx + 10000,
                ty - 10000,
                ty + 10000,
                10,
                CAUCASUS_CHECKS,
            ),
        )
    )

    # The maps of the DCS install (Mods/terrains), whole.
    for cls in (terrains.Caucasus, terrains.PersianGulf, terrains.Syria):
        terrain = cls()
        b = terrain.bounds
        x0, x1 = sorted((b.bottom, b.top))
        y0, y1 = sorted((b.left, b.right))
        checks = CAUCASUS_CHECKS if cls is terrains.Caucasus else []
        name = f"{terrain.name}_{step}m"
        nx = int((x1 - x0) // step) + 1
        ny = int((y1 - y0) // step) + 1
        print(
            mission(terrain, name, lua(name, x0, x1, y0, y1, step, checks)),
            f"{nx} x {ny} = {nx * ny / 1e6:.0f} M points, {nx * ny * 2 / 1e6:.0f} MB",
        )


if __name__ == "__main__":
    main()

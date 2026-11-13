"""Pack a height scan of DCS into the height map Retribution ships.

The scan comes from a mission of `make_scan_missions.py`, run in DCS with Retribution
open: `Saved Games/DCS/Retribution/Heightmaps/<scan>.bin` and `<scan>.json`. The
packed file, `resources/heightmaps/<terrain>.dem`, goes into the release zip (it is
too large for git); see `game/theater/groundheight.py` for the format.

Usage, from the root of the repository:
    python scripts/heightmaps/pack_heightmap.py Caucasus_100m Caucasus
(the second argument is the pydcs `Terrain.name` of the map).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from game.theater import groundheight  # noqa: E402

SCANS = Path.home() / "Saved Games" / "DCS" / "Retribution" / "Heightmaps"


def main() -> None:
    scan, terrain = sys.argv[1], sys.argv[2]
    header = json.loads((SCANS / f"{scan}.json").read_text())
    raw = np.fromfile(SCANS / f"{scan}.bin", dtype="<u2")
    heights = (raw.astype(np.float64) - 32768) / 4
    heights = heights.reshape(header["nx"], header["ny"])
    groundheight.FOLDER.mkdir(parents=True, exist_ok=True)
    path = groundheight.FOLDER / f"{terrain}.dem"
    groundheight.write(
        path, terrain, header["x0"], header["y0"], header["step"], heights
    )

    # Check: the packed map gives the heights of the scan back, to the metre.
    packed = groundheight.HeightMap(path)
    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(2000):
        i = int(rng.integers(header["nx"]))
        j = int(rng.integers(header["ny"]))
        x = header["x0"] + i * header["step"]
        y = header["y0"] + j * header["step"]
        found = packed.height(x, y)
        assert found is not None
        worst = max(worst, abs(found - heights[i, j]))
    print(f"{path}: {path.stat().st_size / 1e6:.1f} MB, worst error {worst:.2f} m")


if __name__ == "__main__":
    main()

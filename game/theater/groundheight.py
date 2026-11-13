"""Ground height of a DCS map, as DCS itself gives it.

The heights were measured in DCS with `land.getHeight` on a grid over the whole map
(`scripts/heightmaps/`), so they match the terrain of the sim, not a public elevation
model. A DCS map's terrain has no other source Retribution can read.

A map's file, `resources/heightmaps/<terrain>.dem`, ships in the release zip only: it
is too large for git. Without it, `ground_height` answers None and callers keep their
fallback.

Format: `RDEM1\\n`, a little-endian uint32 header length, a JSON header (grid origin,
step, size, rows per block, block offsets), then the blocks. A block is `block_rows`
rows (north along x), each row east along y, heights in whole metres as int16 stored
as the difference from the previous height of the row, xz-compressed. Only the blocks
under the points asked for are read and decompressed.
"""

from __future__ import annotations

import json
import lzma
import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, Optional

import numpy as np
import numpy.typing as npt

MAGIC = b"RDEM1\n"
FOLDER = Path("resources/heightmaps")


@dataclass(frozen=True)
class GridHeader:
    terrain: str
    x0: float
    y0: float
    step: float
    nx: int
    ny: int
    block_rows: int
    #: Where each block starts, from the start of the file, and where the last ends.
    offsets: tuple[int, ...]


class HeightMap:
    def __init__(self, path: Path) -> None:
        self.path = path
        with path.open("rb") as f:
            self.header = _read_header(f)
        self._blocks: dict[int, npt.NDArray[np.int32]] = {}

    def _block(self, index: int) -> npt.NDArray[np.int32]:
        if index not in self._blocks:
            start, end = self.header.offsets[index], self.header.offsets[index + 1]
            with self.path.open("rb") as f:
                f.seek(start)
                raw = lzma.decompress(f.read(end - start))
            deltas = np.frombuffer(raw, dtype="<i2").reshape(-1, self.header.ny)
            self._blocks[index] = np.cumsum(deltas, axis=1, dtype=np.int32)
        return self._blocks[index]

    def _at(self, row: int, column: int) -> float:
        block = self._block(row // self.header.block_rows)
        return float(block[row % self.header.block_rows, column])

    def height(self, x: float, y: float) -> Optional[float]:
        """Metres above sea level at map coordinates `x`, `y`; None off the grid."""
        h = self.header
        i = (x - h.x0) / h.step
        j = (y - h.y0) / h.step
        if not (0 <= i <= h.nx - 1 and 0 <= j <= h.ny - 1):
            return None
        i0, j0 = min(int(i), h.nx - 2), min(int(j), h.ny - 2)
        di, dj = i - i0, j - j0
        return (
            self._at(i0, j0) * (1 - di) * (1 - dj)
            + self._at(i0 + 1, j0) * di * (1 - dj)
            + self._at(i0, j0 + 1) * (1 - di) * dj
            + self._at(i0 + 1, j0 + 1) * di * dj
        )


def _read_header(f: BinaryIO) -> GridHeader:
    if f.read(len(MAGIC)) != MAGIC:
        raise ValueError("Not a Retribution height map.")
    (length,) = struct.unpack("<I", f.read(4))
    d = json.loads(f.read(length).decode("utf-8"))
    return GridHeader(
        terrain=d["terrain"],
        x0=d["x0"],
        y0=d["y0"],
        step=d["step"],
        nx=d["nx"],
        ny=d["ny"],
        block_rows=d["block_rows"],
        offsets=tuple(d["offsets"]),
    )


def write(
    path: Path,
    terrain: str,
    x0: float,
    y0: float,
    step: float,
    heights: npt.NDArray[np.float64],
    block_rows: int = 64,
) -> None:
    """Writes `heights` (metres, rows along x) as a height map file."""
    nx, ny = heights.shape
    metres = np.round(heights).astype(np.int32)
    deltas = np.diff(metres, axis=1, prepend=0).astype("<i2")
    blocks = [
        lzma.compress(deltas[start : start + block_rows].tobytes(), preset=6)
        for start in range(0, nx, block_rows)
    ]

    def header(offsets: list[int]) -> bytes:
        return json.dumps(
            {
                "terrain": terrain,
                "x0": x0,
                "y0": y0,
                "step": step,
                "nx": nx,
                "ny": ny,
                "block_rows": block_rows,
                "offsets": offsets,
            }
        ).encode("utf-8")

    # The offsets are in the header they follow: size it with placeholders first.
    placeholder = [0] * (len(blocks) + 1)
    start = len(MAGIC) + 4 + len(header([10**12] * len(placeholder)))
    offsets = [start]
    for block in blocks:
        offsets.append(offsets[-1] + len(block))
    text = header(offsets).ljust(start - len(MAGIC) - 4)
    with path.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<I", len(text)))
        f.write(text)
        for block in blocks:
            f.write(block)


@lru_cache(maxsize=4)
def heightmap_for(terrain: str, folder: Path = FOLDER) -> Optional[HeightMap]:
    """The height map of the DCS map `terrain` (`Terrain.name`), None without one."""
    path = folder / f"{terrain}.dem"
    if not path.is_file():
        return None
    try:
        return HeightMap(path)
    except (OSError, ValueError, KeyError):
        return None


def ground_height(terrain: str, x: float, y: float) -> Optional[float]:
    """Metres above sea level on the DCS map `terrain`; None when unknown."""
    heightmap = heightmap_for(terrain)
    return None if heightmap is None else heightmap.height(x, y)

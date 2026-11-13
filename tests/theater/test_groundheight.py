"""Ground heights of a DCS map, read from a packed height map."""

from pathlib import Path

import numpy as np
import pytest

from game.theater import groundheight
from game.theater.groundheight import HeightMap


def test_a_packed_map_gives_back_the_heights_to_the_metre(tmp_path: Path) -> None:
    rng = np.random.default_rng(1)
    heights = rng.uniform(-20, 3000, size=(150, 40))
    path = tmp_path / "Test.dem"
    # Small blocks: points on both sides of a block boundary.
    groundheight.write(path, "Test", -1000.0, 500.0, 100.0, heights, block_rows=16)

    heightmap = HeightMap(path)

    for i, j in [(0, 0), (15, 3), (16, 3), (149, 39), (77, 20)]:
        found = heightmap.height(-1000.0 + i * 100, 500.0 + j * 100)
        assert found == pytest.approx(heights[i, j], abs=0.5)


def test_between_points_the_height_is_interpolated(tmp_path: Path) -> None:
    heights = np.array([[0.0, 100.0], [200.0, 300.0]])
    path = tmp_path / "Test.dem"
    groundheight.write(path, "Test", 0.0, 0.0, 100.0, heights)

    heightmap = HeightMap(path)

    assert heightmap.height(50, 50) == pytest.approx(150)
    assert heightmap.height(100, 0) == pytest.approx(200)
    assert heightmap.height(-1, 0) is None
    assert heightmap.height(0, 101) is None


def test_a_map_without_height_map_has_no_height(tmp_path: Path) -> None:
    assert groundheight.heightmap_for("Nowhere", tmp_path) is None

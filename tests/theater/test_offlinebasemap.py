import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image
from shapely.geometry import MultiPolygon, Polygon

from game.theater.landmap import Landmap
from game.theater.offlinebasemap import (
    BOUNDS_FILENAME,
    DEFAULT_COLORS,
    IMAGE_FILENAME,
    PIXEL_CLASSES,
    OfflineBasemap,
    OfflineBasemapBounds,
    render,
    with_palette,
)

FALKLANDS_LANDMAP = Path("resources/theaters/falklands/landmap.p")
SEA, LAND, EXCLUDED, COAST = (PIXEL_CLASSES.index(c) for c in PIXEL_CLASSES)


class _IdentityTransformer:
    """DCS x/y are read as lat/lng degrees directly."""

    @staticmethod
    def transform(x: Any, y: Any) -> tuple[Any, Any]:
        return x, y


TERRAIN: Any = SimpleNamespace(_point_to_ll_transformer=_IdentityTransformer())


def _square(x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _landmap() -> Landmap:
    # Land with a lake, an island in the lake, and an exclusion zone. x is the
    # latitude and y the longitude (see _IdentityTransformer).
    land = Polygon(_square(0, 0, 10, 10), holes=[_square(2, 2, 6, 6)])
    island = Polygon(_square(3, 3, 5, 5))
    exclusion = Polygon(_square(7, 7, 9, 9))
    sea = Polygon(_square(-2, -2, 12, 12)).difference(Polygon(_square(0, 0, 10, 10)))
    return Landmap(
        inclusion_zones=MultiPolygon([land, island]),
        exclusion_zones=MultiPolygon([exclusion]),
        sea_zones=MultiPolygon([sea]),
    )


def _pixel_at(
    image: Image.Image, bounds: OfflineBasemapBounds, lat: float, lng: float
) -> int:
    # Close enough to Mercator near the equator for these tests.
    x = (lng - bounds.west) / (bounds.east - bounds.west) * (image.width - 1)
    y = (bounds.north - lat) / (bounds.north - bounds.south) * (image.height - 1)
    value = image.getpixel((round(x), round(y)))
    assert isinstance(value, int)
    return value


def test_render_paints_each_class() -> None:
    image, bounds = render(_landmap(), TERRAIN, 280)

    assert image.mode == "P"
    assert bounds == OfflineBasemapBounds(south=-2, west=-2, north=12, east=12)
    assert max(image.size) == 280
    assert _pixel_at(image, bounds, -1, -1) == SEA
    assert _pixel_at(image, bounds, 1, 1) == LAND
    assert _pixel_at(image, bounds, 2.5, 2.5) == SEA  # The lake.
    assert _pixel_at(image, bounds, 4, 4) == LAND  # The island in the lake.
    assert _pixel_at(image, bounds, 8, 8) == EXCLUDED
    colors = image.getcolors()
    assert colors is not None
    assert COAST in {index for _, index in colors}


def test_render_uses_web_mercator() -> None:
    # Two land strips of equal height in degrees: the one closer to the pole is
    # taller in pixels.
    landmap = Landmap(
        inclusion_zones=MultiPolygon(
            [Polygon(_square(0, 0, 10, 1)), Polygon(_square(60, 0, 70, 1))]
        ),
        exclusion_zones=MultiPolygon(),
        sea_zones=MultiPolygon(),
    )
    image, _ = render(landmap, TERRAIN, 1000)
    rows = [
        sum(1 for x in range(image.width) if image.getpixel((x, y)) != SEA) > 0
        for y in range(image.height)
    ]
    north_rows = sum(rows[: image.height // 2])
    south_rows = sum(rows[image.height // 2 :])
    assert north_rows > 2 * south_rows


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    landmap_path = tmp_path / "landmap.p"
    assert OfflineBasemap.for_landmap(landmap_path) is None

    image, bounds = render(_landmap(), TERRAIN, 100)
    OfflineBasemap(tmp_path / IMAGE_FILENAME, bounds).save(image)

    loaded = OfflineBasemap.for_landmap(landmap_path)
    assert loaded == OfflineBasemap(tmp_path / IMAGE_FILENAME, bounds)
    saved = Image.open(loaded.image_path)
    assert saved.mode == "P"
    assert saved.tobytes() == image.tobytes()
    assert json.loads((tmp_path / BOUNDS_FILENAME).read_text())["north"] == 12


def test_with_palette_swaps_colours_only() -> None:
    image, _ = render(_landmap(), TERRAIN, 100)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    recolored = Image.open(
        io.BytesIO(with_palette(buffer.getvalue(), {"land": "#102030"}))
    )

    assert recolored.tobytes() == image.tobytes()
    palette = recolored.getpalette()
    assert palette is not None
    assert palette[3 * LAND : 3 * LAND + 3] == [0x10, 0x20, 0x30]
    sea = DEFAULT_COLORS["sea"]
    assert palette[0:3] == [int(sea[i : i + 2], 16) for i in (1, 3, 5)]


def test_with_palette_rejects_non_palette_images() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format="PNG")
    with pytest.raises(ValueError):
        with_palette(buffer.getvalue(), {})
    with pytest.raises(ValueError):
        with_palette(b"not a png", {})


def test_falklands_ships_a_small_precomputed_basemap() -> None:
    basemap = OfflineBasemap.for_landmap(FALKLANDS_LANDMAP)
    assert basemap is not None
    assert basemap.image_path.stat().st_size < 2 * 1024 * 1024
    image = Image.open(basemap.image_path)
    assert image.mode == "P"
    # The Falklands islands (around 51.7S 59W) are inside the image.
    bounds = basemap.bounds
    assert bounds.south < -51.7 < bounds.north
    assert bounds.west < -59 < bounds.east


def test_light_theatres_have_no_precomputed_basemap() -> None:
    assert (
        OfflineBasemap.for_landmap(Path("resources/theaters/caucasus/landmap.p"))
        is None
    )

"""Precomputed offline basemap image for theatres with a heavy landmap (GFX-04.2).

Some landmaps (Falklands) are too heavy to be sent to the map client and drawn
as polygons. For those theatres the landmap is rasterised once, at packaging
time, into a palette PNG stored next to ``landmap.p``:

* ``offline_basemap.png``: one pixel class per palette index (see
  ``PIXEL_CLASSES``), drawn in Web Mercator so that Leaflet can display it as a
  plain image overlay between its south-west and north-east corners.
* ``offline_basemap.json``: those corners, in lat/lng.

The palette only carries default colours: the server swaps it for the colours
the client asks for (``with_palette``), so the client stays the single source
of truth for basemap colours and the image follows theming without being
regenerated.

Regenerate with ``python resources/tools/generate_offline_basemap.py``.
"""

from __future__ import annotations

import json
import math
import struct
import zlib
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np
import numpy.typing as npt
from dcs.terrain.terrain import Terrain
from PIL import Image, ImageDraw
from shapely.geometry import MultiPolygon, Polygon

from .landmap import Landmap

IMAGE_FILENAME = "offline_basemap.png"
BOUNDS_FILENAME = "offline_basemap.json"

# Palette index of each pixel class, in drawing order. The names match the keys
# of OFFLINE_BASEMAP_COLORS in client/src/maplayers/colors.ts.
PIXEL_CLASSES = ("sea", "land", "landExcluded", "coastline")

# Colours baked into the palette, so the PNG looks right on its own. The client
# overrides them at request time.
DEFAULT_COLORS = {
    "sea": "#9db4c8",
    "land": "#e4dfd1",
    "landExcluded": "#cdc5ae",
    "coastline": "#6f8496",
}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class OfflineBasemapBounds:
    south: float
    west: float
    north: float
    east: float

    def to_json(self) -> dict[str, float]:
        return {
            "south": self.south,
            "west": self.west,
            "north": self.north,
            "east": self.east,
        }

    @staticmethod
    def from_json(data: Mapping[str, float]) -> OfflineBasemapBounds:
        return OfflineBasemapBounds(
            south=float(data["south"]),
            west=float(data["west"]),
            north=float(data["north"]),
            east=float(data["east"]),
        )


@dataclass(frozen=True)
class OfflineBasemap:
    image_path: Path
    bounds: OfflineBasemapBounds

    @staticmethod
    def for_landmap(landmap_path: Path) -> OfflineBasemap | None:
        """Returns the precomputed basemap stored next to a landmap, if any."""
        image_path = landmap_path.with_name(IMAGE_FILENAME)
        bounds_path = landmap_path.with_name(BOUNDS_FILENAME)
        if not image_path.is_file() or not bounds_path.is_file():
            return None
        with bounds_path.open(encoding="utf-8") as bounds_file:
            bounds = OfflineBasemapBounds.from_json(json.load(bounds_file))
        return OfflineBasemap(image_path, bounds)

    def save(self, image: Image.Image) -> None:
        # No `optimize`: it may drop or reorder palette entries, and the palette
        # index is the pixel class.
        image.save(self.image_path, compress_level=9)
        with self.image_path.with_name(BOUNDS_FILENAME).open(
            "w", encoding="utf-8"
        ) as bounds_file:
            json.dump(self.bounds.to_json(), bounds_file, indent=2)
            bounds_file.write("\n")


def _mercator_y(lat: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    return np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def _polygons(geometry: Union[Polygon, MultiPolygon]) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    return [geometry]


def _rings(polygon: Polygon) -> Iterator[npt.NDArray[np.float64]]:
    yield np.asarray(polygon.exterior.coords)
    for interior in polygon.interiors:
        yield np.asarray(interior.coords)


class _Projection:
    """DCS X/Y -> pixel coordinates of a Web Mercator image."""

    def __init__(
        self, terrain: Terrain, rings: Iterable[npt.NDArray[np.float64]], max_size: int
    ) -> None:
        self.transformer = terrain._point_to_ll_transformer
        lats, lngs = [], []
        for ring in rings:
            lat, lng = self.transformer.transform(ring[:, 0], ring[:, 1])
            lats.append(np.asarray(lat))
            lngs.append(np.asarray(lng))
        if not lats:
            raise ValueError("Landmap has no geometry")
        all_lats = np.concatenate(lats)
        all_lngs = np.concatenate(lngs)
        self.bounds = OfflineBasemapBounds(
            south=float(all_lats.min()),
            west=float(all_lngs.min()),
            north=float(all_lats.max()),
            east=float(all_lngs.max()),
        )
        self.x0 = math.radians(self.bounds.west)
        self.y1 = float(_mercator_y(np.array(self.bounds.north)))
        width = math.radians(self.bounds.east) - self.x0
        height = self.y1 - float(_mercator_y(np.array(self.bounds.south)))
        self.scale = max_size / max(width, height)
        self.size = (
            max(1, round(width * self.scale)),
            max(1, round(height * self.scale)),
        )

    def to_pixels(self, ring: npt.NDArray[np.float64]) -> list[tuple[float, float]]:
        lat, lng = self.transformer.transform(ring[:, 0], ring[:, 1])
        px = (np.radians(np.asarray(lng)) - self.x0) * self.scale
        py = (self.y1 - _mercator_y(np.asarray(lat))) * self.scale
        return list(zip(px.tolist(), py.tolist()))


def _paint(
    image: Image.Image,
    projection: _Projection,
    polygons: list[Polygon],
    index: int,
) -> None:
    """Paints each polygon (holes excluded) with a palette index.

    Each polygon is rasterised into its own mask before being pasted, so the
    holes of one polygon never erase another polygon (an island in a lake).
    """
    for polygon in polygons:
        rings = [projection.to_pixels(ring) for ring in _rings(polygon)]
        xs = [x for ring in rings for x, _ in ring]
        ys = [y for ring in rings for _, y in ring]
        left, top = math.floor(min(xs)), math.floor(min(ys))
        right, bottom = math.ceil(max(xs)) + 1, math.ceil(max(ys)) + 1
        mask = Image.new("1", (right - left, bottom - top), 0)
        draw = ImageDraw.Draw(mask)
        shifted = [[(x - left, y - top) for x, y in ring] for ring in rings]
        draw.polygon(shifted[0], fill=1)
        for hole in shifted[1:]:
            draw.polygon(hole, fill=0)
        image.paste(index, (left, top, right, bottom), mask)


def _palette(colors: Mapping[str, str]) -> list[int]:
    palette: list[int] = []
    for name in PIXEL_CLASSES:
        value = colors[name].lstrip("#")
        palette.extend(int(value[i : i + 2], 16) for i in (0, 2, 4))
    return palette


def render(
    landmap: Landmap, terrain: Terrain, max_size: int
) -> tuple[Image.Image, OfflineBasemapBounds]:
    """Rasterises a landmap like the vector offline basemap draws it.

    The whole image is sea; land is painted over it with its coastline, then
    the exclusion zones. Sea zones need no drawing: the map container shows the
    sea colour wherever the image does not reach.
    """
    inclusion = _polygons(landmap.inclusion_zones)
    exclusion = _polygons(landmap.exclusion_zones)
    sea = _polygons(landmap.sea_zones)
    projection = _Projection(
        terrain,
        (ring for p in inclusion + exclusion + sea for ring in _rings(p)),
        max_size,
    )
    image = Image.new("P", projection.size, PIXEL_CLASSES.index("sea"))
    image.putpalette(_palette(DEFAULT_COLORS))
    _paint(image, projection, inclusion, PIXEL_CLASSES.index("land"))
    draw = ImageDraw.Draw(image)
    coastline = PIXEL_CLASSES.index("coastline")
    for polygon in inclusion:
        for ring in _rings(polygon):
            draw.line(projection.to_pixels(ring), fill=coastline, width=1)
    _paint(image, projection, exclusion, PIXEL_CLASSES.index("landExcluded"))
    return image, projection.bounds


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def with_palette(png: bytes, colors: Mapping[str, str]) -> bytes:
    """Returns the PNG with its palette replaced, without re-encoding pixels."""
    if not png.startswith(PNG_SIGNATURE):
        raise ValueError("Not a PNG image")
    palette = bytes(_palette({**DEFAULT_COLORS, **colors}))
    out = [PNG_SIGNATURE]
    offset = len(PNG_SIGNATURE)
    replaced = False
    while offset < len(png):
        (length,) = struct.unpack(">I", png[offset : offset + 4])
        kind = png[offset + 4 : offset + 8]
        end = offset + 12 + length
        if kind == b"PLTE":
            data = png[offset + 8 : offset + 8 + length]
            # Keep any extra entries, replace only the pixel classes.
            out.append(_chunk(kind, palette + data[len(palette) :]))
            replaced = True
        else:
            out.append(png[offset:end])
        offset = end
    if not replaced:
        raise ValueError("PNG has no palette")
    return b"".join(out)

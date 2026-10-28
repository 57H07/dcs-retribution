"""Generates the precomputed offline basemap of heavy theatres (GFX-04.2).

The map client draws the offline basemap from the landmap polygons, but some
landmaps are too heavy for that (see game/theater/offlinebasemap.py). For those
theatres this script rasterises the landmap into
resources/theaters/<theatre>/offline_basemap.png (+ offline_basemap.json); the
server then sends the image instead of the polygons.

Run from the repository root whenever a listed theatre's landmap.p changes:

    python resources/tools/generate_offline_basemap.py            # all listed
    python resources/tools/generate_offline_basemap.py falklands  # one theatre

To stop using an image for a theatre, delete its two offline_basemap files.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from game.theater.offlinebasemap import (  # noqa: E402
    IMAGE_FILENAME,
    OfflineBasemap,
    render,
)
from game.theater.theaterloader import TheaterLoader  # noqa: E402

# Theatres whose landmap is too heavy to be drawn as polygons by the client.
HEAVY_THEATERS = ["falklands"]

# Longest side of the image, in pixels. 6144 px gives ~300 m per pixel on the
# Falklands, enough for a fallback basemap, for a file of about 300 KB.
DEFAULT_MAX_SIZE = 6144


def generate(theater_name: str, max_size: int) -> None:
    loader = TheaterLoader(theater_name)
    theater = loader.load()
    if theater.landmap is None:
        raise RuntimeError(f"{theater_name} has no landmap")
    start = time.perf_counter()
    image, bounds = render(theater.landmap, theater.terrain, max_size)
    basemap = OfflineBasemap(loader.landmap_path.with_name(IMAGE_FILENAME), bounds)
    basemap.save(image)
    size_kb = basemap.image_path.stat().st_size / 1024
    print(
        f"{theater_name}: {image.width}x{image.height} px, {size_kb:.0f} KB, "
        f"{time.perf_counter() - start:.1f} s -> {basemap.image_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "theaters",
        nargs="*",
        default=HEAVY_THEATERS,
        help="theatre directory names under resources/theaters "
        f"(default: {', '.join(HEAVY_THEATERS)})",
    )
    parser.add_argument("--max-size", type=int, default=DEFAULT_MAX_SIZE)
    args = parser.parse_args()
    for theater_name in args.theaters:
        generate(theater_name, args.max_size)


if __name__ == "__main__":
    main()

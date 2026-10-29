from functools import lru_cache
from pathlib import Path

from game.gamelock import game_lock, locked
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from game import Game
from game.server import GameContext
from game.theater.offlinebasemap import DEFAULT_COLORS, OfflineBasemap, with_palette
from .models import MapZonesJs, ThreatZoneContainerJs, UnculledZoneJs

router: APIRouter = APIRouter(prefix="/map-zones")


@router.get("/terrain", operation_id="get_terrain_zones", response_model=MapZonesJs)
@locked
def get_terrain(game: Game = Depends(GameContext.require)) -> MapZonesJs:
    if game.theater.landmap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    # Heavy landmaps (Falklands) come as a precomputed image, not as polygons.
    return MapZonesJs.from_game(game)


HEX_COLOR = r"^[0-9a-fA-F]{6}$"


@lru_cache(maxsize=4)
def _recolored_basemap(image_path: Path, colors: tuple[tuple[str, str], ...]) -> bytes:
    return with_palette(image_path.read_bytes(), dict(colors))


@router.get(
    "/offline-basemap",
    operation_id="get_offline_basemap_image",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
def get_offline_basemap_image(
    sea: str = Query(DEFAULT_COLORS["sea"][1:], pattern=HEX_COLOR),
    land: str = Query(DEFAULT_COLORS["land"][1:], pattern=HEX_COLOR),
    land_excluded: str = Query(DEFAULT_COLORS["landExcluded"][1:], pattern=HEX_COLOR),
    coastline: str = Query(DEFAULT_COLORS["coastline"][1:], pattern=HEX_COLOR),
    game: Game = Depends(GameContext.require),
) -> Response:
    """Precomputed offline basemap of the theatre (GFX-04.2), in these colours.

    Colours are hex RGB without the leading '#'. 404 when the theatre has no
    precomputed basemap: the client then draws the landmap polygons.
    """
    # Only the theatre path is read under the game lock: recolouring the image is
    # slow and must not stall the simulation or other commands.
    with game_lock():
        landmap_path = game.theater.landmap_path
    basemap = OfflineBasemap.for_landmap(landmap_path)
    if basemap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    colors = (
        ("sea", f"#{sea}"),
        ("land", f"#{land}"),
        ("landExcluded", f"#{land_excluded}"),
        ("coastline", f"#{coastline}"),
    )
    return Response(
        content=_recolored_basemap(basemap.image_path, colors),
        media_type="image/png",
        # The URL does not name the theatre: never reuse another game's image.
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/unculled", operation_id="list_unculled_zones", response_model=list[UnculledZoneJs]
)
@locked
def get_unculled_zones(
    game: Game = Depends(GameContext.require),
) -> list[UnculledZoneJs]:
    return UnculledZoneJs.from_game(game)


@router.get(
    "/threats", operation_id="get_threat_zones", response_model=ThreatZoneContainerJs
)
@locked
def get_threat_zones(
    game: Game = Depends(GameContext.require),
) -> ThreatZoneContainerJs:
    return ThreatZoneContainerJs.for_game(game)

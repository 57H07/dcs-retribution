import io
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from PIL import Image
from shapely.geometry import MultiPolygon, Polygon

from game.server.mapzones.models import MapZonesJs
from game.server.mapzones.routes import get_offline_basemap_image, get_terrain
from game.theater.landmap import Landmap
from game.theater.offlinebasemap import (
    IMAGE_FILENAME,
    PIXEL_CLASSES,
    OfflineBasemap,
    render,
)


class _IdentityTransformer:
    @staticmethod
    def transform(x: Any, y: Any) -> tuple[Any, Any]:
        return x, y


def _landmap() -> Landmap:
    land = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    return Landmap(
        inclusion_zones=MultiPolygon([land]),
        exclusion_zones=MultiPolygon(),
        sea_zones=MultiPolygon(),
    )


def _game(landmap_path: Path) -> Any:
    terrain = SimpleNamespace(_point_to_ll_transformer=_IdentityTransformer())
    theater = SimpleNamespace(
        terrain=terrain, landmap=_landmap(), landmap_path=landmap_path
    )
    return SimpleNamespace(theater=theater)


@pytest.fixture
def heavy_game(tmp_path: Path) -> Any:
    game = _game(tmp_path / "landmap.p")
    image, bounds = render(game.theater.landmap, game.theater.terrain, 64)
    OfflineBasemap(tmp_path / IMAGE_FILENAME, bounds).save(image)
    return game


def test_heavy_theatre_sends_the_image_instead_of_polygons(heavy_game: Any) -> None:
    zones = MapZonesJs.from_game(heavy_game)

    assert zones.inclusion == zones.exclusion == zones.sea == []
    assert zones.offline_image is not None
    assert zones.offline_image.south_west.lat == 0
    assert zones.offline_image.north_east.lng == 1
    assert get_terrain(heavy_game).offline_image == zones.offline_image


def test_light_theatre_sends_polygons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dcs.mapping import LatLng

    monkeypatch.setattr("dcs.mapping.Point.latlng", lambda self: LatLng(self.x, self.y))
    zones = MapZonesJs.from_game(_game(tmp_path / "landmap.p"))

    assert zones.offline_image is None
    assert len(zones.inclusion) == 1


def test_image_is_served_in_the_requested_colours(heavy_game: Any) -> None:
    response = get_offline_basemap_image(
        sea="000000",
        land="ff0000",
        land_excluded="00ff00",
        coastline="0000ff",
        game=heavy_game,
    )

    assert response.media_type == "image/png"
    assert response.headers["cache-control"] == "no-store"
    image = Image.open(io.BytesIO(response.body))
    palette = image.getpalette()
    assert palette is not None
    land = PIXEL_CLASSES.index("land")
    assert palette[3 * land : 3 * land + 3] == [255, 0, 0]


def test_no_image_is_404(tmp_path: Path) -> None:
    with pytest.raises(HTTPException) as error:
        get_offline_basemap_image(
            sea="000000",
            land="000000",
            land_excluded="000000",
            coastline="000000",
            game=_game(tmp_path / "landmap.p"),
        )
    assert error.value.status_code == 404

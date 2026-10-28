from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from game.server.leaflet import LeafletPoint, LeafletPoly, ShapelyUtil
from game.theater import ConflictTheater, Player
from game.theater.offlinebasemap import OfflineBasemap
from game.threatzones import ThreatZones

if TYPE_CHECKING:
    from game import Game


class OfflineBasemapImageJs(BaseModel):
    """Precomputed offline basemap image of a heavy theatre (GFX-04.2).

    Served by GET /map-zones/offline-basemap, drawn between these corners.
    """

    south_west: LeafletPoint
    north_east: LeafletPoint

    class Config:
        title = "OfflineBasemapImage"

    @staticmethod
    def from_basemap(basemap: OfflineBasemap) -> OfflineBasemapImageJs:
        bounds = basemap.bounds
        return OfflineBasemapImageJs(
            south_west=LeafletPoint(lat=bounds.south, lng=bounds.west),
            north_east=LeafletPoint(lat=bounds.north, lng=bounds.east),
        )


class MapZonesJs(BaseModel):
    inclusion: list[LeafletPoly]
    exclusion: list[LeafletPoly]
    sea: list[LeafletPoly]
    # Set for theatres whose landmap is too heavy to send as polygons: the
    # polygon lists are then empty and the client draws this image instead.
    offline_image: OfflineBasemapImageJs | None = None

    class Config:
        title = "MapZones"

    @classmethod
    def empty(cls) -> MapZonesJs:
        return MapZonesJs(inclusion=[], exclusion=[], sea=[])

    @classmethod
    def from_game(cls, game: Game) -> MapZonesJs:
        zones = game.theater.landmap
        if zones is None:
            return cls.empty()

        basemap = OfflineBasemap.for_landmap(game.theater.landmap_path)
        if basemap is not None:
            # Converting and drawing every point of a heavy landmap (Falklands)
            # takes seconds on the server and much longer in the client.
            return MapZonesJs(
                inclusion=[],
                exclusion=[],
                sea=[],
                offline_image=OfflineBasemapImageJs.from_basemap(basemap),
            )

        return MapZonesJs(
            inclusion=ShapelyUtil.polys_to_leaflet(zones.inclusion_zones, game.theater),
            exclusion=ShapelyUtil.polys_to_leaflet(zones.exclusion_zones, game.theater),
            sea=ShapelyUtil.polys_to_leaflet(zones.sea_zones, game.theater),
        )


class UnculledZoneJs(BaseModel):
    position: LeafletPoint
    radius: float

    class Config:
        title = "UnculledZone"

    @staticmethod
    def from_game(game: Game) -> list[UnculledZoneJs]:
        return [
            UnculledZoneJs(
                position=zone.latlng(),
                radius=game.settings.perf_culling_distance * 1000,
            )
            for zone in game.get_culling_zones()
        ]


class ThreatZonesJs(BaseModel):
    full: list[LeafletPoly]
    aircraft: list[LeafletPoly]
    air_defenses: list[LeafletPoly]
    radar_sams: list[LeafletPoly]

    class Config:
        title = "ThreatZones"

    @classmethod
    def from_zones(cls, zones: ThreatZones, theater: ConflictTheater) -> ThreatZonesJs:
        return ThreatZonesJs(
            full=ShapelyUtil.polys_to_leaflet(zones.all, theater),
            aircraft=ShapelyUtil.polys_to_leaflet(zones.airbases, theater),
            air_defenses=ShapelyUtil.polys_to_leaflet(zones.air_defenses, theater),
            radar_sams=ShapelyUtil.polys_to_leaflet(zones.radar_sam_threats, theater),
        )


class ThreatZoneContainerJs(BaseModel):
    blue: ThreatZonesJs
    red: ThreatZonesJs

    class Config:
        title = "ThreatZoneContainer"

    @staticmethod
    def for_game(game: Game) -> ThreatZoneContainerJs:
        return ThreatZoneContainerJs(
            blue=ThreatZonesJs.from_zones(
                game.threat_zone_for(player=Player.BLUE), game.theater
            ),
            red=ThreatZonesJs.from_zones(
                game.threat_zone_for(player=Player.RED), game.theater
            ),
        )

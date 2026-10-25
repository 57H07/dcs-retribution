"""Web engine profile of the campaign map.

Qt 6 makes the default ``QWebEngineProfile`` off-the-record: its HTTP cache only
lives in memory, so every launch downloads all basemap tiles again and nothing is
left to show when the network is gone. The map uses a named, disk-based profile
instead, with QtWebEngine's standard persistent HTTP cache (GFX-04.3).

This is the browser's ordinary HTTP cache: it honours the cache headers sent by
the tile servers, evicts on its own and is size-bounded. No tile is stored by
Retribution itself (the basemap providers' terms restrict offline storage).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from PySide6.QtCore import QCoreApplication, QStandardPaths
from PySide6.QtWebEngineCore import QWebEngineProfile

MAP_PROFILE_NAME = "retribution-map"
# Upper bound of the disk cache. Chromium evicts the least recently used entries
# beyond it.
MAP_HTTP_CACHE_MAX_BYTES = 512 * 1024 * 1024


class HttpCacheConfigurable(Protocol):
    """The part of QWebEngineProfile used to set up the persistent cache."""

    def setPersistentStoragePath(self, path: str) -> None: ...

    def setCachePath(self, path: str) -> None: ...

    def setHttpCacheType(self, type: QWebEngineProfile.HttpCacheType) -> None: ...

    def setHttpCacheMaximumSize(self, maxSize: int) -> None: ...


@dataclass(frozen=True)
class MapProfilePaths:
    storage: Path
    cache: Path

    @staticmethod
    def under(base: Path) -> MapProfilePaths:
        root = base / "DCSRetribution" / "QtWebEngine" / MAP_PROFILE_NAME
        return MapProfilePaths(storage=root / "storage", cache=root / "cache")


def default_profile_paths() -> MapProfilePaths:
    # %LOCALAPPDATA% on Windows: a per-machine cache, kept out of Saved Games.
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.GenericDataLocation
    )
    return MapProfilePaths.under(Path(base))


def configure_persistent_http_cache(
    profile: HttpCacheConfigurable,
    paths: MapProfilePaths,
    max_bytes: int = MAP_HTTP_CACHE_MAX_BYTES,
) -> None:
    """Points the profile at an on-disk HTTP cache.

    Must run before any page of the profile loads.
    """
    paths.storage.mkdir(parents=True, exist_ok=True)
    paths.cache.mkdir(parents=True, exist_ok=True)
    profile.setPersistentStoragePath(str(paths.storage))
    profile.setCachePath(str(paths.cache))
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
    profile.setHttpCacheMaximumSize(max_bytes)


_map_profile: Optional[QWebEngineProfile] = None


def map_web_profile() -> QWebEngineProfile:
    """The shared profile of the map views, created on first use.

    It is owned by the application so that it outlives every page using it
    (QtWebEngine warns when a profile is released before its pages).
    """
    global _map_profile
    if _map_profile is None:
        profile = QWebEngineProfile(MAP_PROFILE_NAME, QCoreApplication.instance())
        configure_persistent_http_cache(profile, default_profile_paths())
        _map_profile = profile
    return _map_profile

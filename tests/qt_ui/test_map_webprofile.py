from pathlib import Path

from PySide6.QtWebEngineCore import QWebEngineProfile

from qt_ui.widgets.map.webprofile import (
    MAP_HTTP_CACHE_MAX_BYTES,
    MapProfilePaths,
    configure_persistent_http_cache,
)


class RecordingProfile:
    def __init__(self) -> None:
        self.storage_path = ""
        self.cache_path = ""
        self.cache_type = QWebEngineProfile.HttpCacheType.MemoryHttpCache
        self.max_size = -1

    def setPersistentStoragePath(self, path: str) -> None:
        self.storage_path = path

    def setCachePath(self, path: str) -> None:
        self.cache_path = path

    def setHttpCacheType(self, type: QWebEngineProfile.HttpCacheType) -> None:
        self.cache_type = type

    def setHttpCacheMaximumSize(self, maxSize: int) -> None:
        self.max_size = maxSize


def test_profile_uses_a_bounded_disk_http_cache(tmp_path: Path) -> None:
    paths = MapProfilePaths.under(tmp_path)
    profile = RecordingProfile()

    configure_persistent_http_cache(profile, paths)

    assert profile.cache_type == QWebEngineProfile.HttpCacheType.DiskHttpCache
    assert profile.max_size == MAP_HTTP_CACHE_MAX_BYTES
    assert Path(profile.cache_path) == paths.cache
    assert Path(profile.storage_path) == paths.storage
    assert paths.cache.is_dir()
    assert paths.storage.is_dir()


def test_profile_paths_are_namespaced_under_the_base(tmp_path: Path) -> None:
    paths = MapProfilePaths.under(tmp_path)

    assert paths.cache.is_relative_to(tmp_path / "DCSRetribution")
    assert paths.storage.is_relative_to(tmp_path / "DCSRetribution")
    assert paths.cache != paths.storage

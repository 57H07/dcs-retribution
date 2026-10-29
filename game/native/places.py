"""External pages and local folders the shell can open (WEB-00.7)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from game import persistency

_REPOSITORY = "https://github.com/dcs-retribution/dcs-retribution"


class ExternalLink(str, Enum):
    """Pages of the Help menu, opened in the system browser."""

    DISCORD = "discord"
    GITHUB = "github"
    UKRAINE = "ukraine"
    PRETENSE_DISCORD = "pretense-discord"
    RELEASES = "releases"
    MANUAL = "manual"
    FORUM_THREAD = "forum-thread"
    ISSUES = "issues"

    @property
    def url(self) -> str:
        return _LINK_URLS[self]


_LINK_URLS: dict[ExternalLink, str] = {
    ExternalLink.DISCORD: "https://" + "discord.gg" + "/" + "b4x34Bg" + "4We",
    ExternalLink.GITHUB: _REPOSITORY,
    ExternalLink.UKRAINE: "https://shdwp.github.io/ukraine/",
    ExternalLink.PRETENSE_DISCORD: "https://" + "discord.gg" + "/" + "PtPsb9Mpk6",
    ExternalLink.RELEASES: f"{_REPOSITORY}/releases",
    ExternalLink.MANUAL: f"{_REPOSITORY}/wiki",
    ExternalLink.FORUM_THREAD: (
        "https://forum.dcs.world/topic/"
        "368593-dcs-retribution-dynamic-campaign-generator/"
    ),
    ExternalLink.ISSUES: f"{_REPOSITORY}/issues",
}


class NativeFolder(str, Enum):
    """Retribution folders the player may want to browse."""

    SAVES = "saves"
    MISSIONS = "missions"

    def path(self) -> Path:
        if self is NativeFolder.SAVES:
            return persistency.save_dir()
        missions = persistency.mission_path_for("")
        missions.mkdir(parents=True, exist_ok=True)
        return missions

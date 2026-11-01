"""Logs and About screens (WEB-08.2): application data, no campaign needed."""

from __future__ import annotations

from pydantic import BaseModel

from game import VERSION
from game.about import (
    ATTRIBUTIONS,
    AUTHORS,
    CONTRIBUTORS,
    SOURCE_URL,
    SPECIAL_THANKS,
)


class LogTailJs(BaseModel):
    """The last lines of the application log (read-only)."""

    lines: list[str]
    #: Lines in the log, shown and not.
    total: int
    #: False when a custom logging configuration keeps no log in memory.
    available: bool


class ThanksJs(BaseModel):
    name: str
    reason: str


class AttributionJs(BaseModel):
    text: str
    url: str


class AboutJs(BaseModel):
    version: str
    source_url: str
    authors: str
    contributors: list[str]
    special_thanks: list[ThanksJs]
    attributions: list[AttributionJs]

    @staticmethod
    def current() -> AboutJs:
        return AboutJs(
            version=VERSION,
            source_url=SOURCE_URL,
            authors=AUTHORS,
            contributors=CONTRIBUTORS,
            special_thanks=[
                ThanksJs(name=t.name, reason=t.reason) for t in SPECIAL_THANKS
            ],
            attributions=[AttributionJs(text=a.text, url=a.url) for a in ATTRIBUTIONS],
        )

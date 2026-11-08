"""The war diary as the API serves it (#193): `game.wardiary`, newest first."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from pydantic import BaseModel

from game.server.missionresult.models import ToneJs

if TYPE_CHECKING:
    from game import Game
    from game.wardiary import DiaryEntry


class WarDiaryBaseJs(BaseModel):
    id: str
    name: str
    taken: bool

    class Config:
        title = "WarDiaryBase"


class WarDiaryFrontJs(BaseModel):
    name: str
    moved_km: float

    class Config:
        title = "WarDiaryFront"


class WarDiaryPackageJs(BaseModel):
    task: str
    target: str
    flights: list[str]
    lost: int
    aircraft: int
    result: str
    tone: ToneJs

    class Config:
        title = "WarDiaryPackage"


class WarDiaryLossJs(BaseModel):
    name: str
    count: int

    class Config:
        title = "WarDiaryLoss"


class WarDiaryPilotJs(BaseModel):
    #: A player pilot, whose career can be opened; null for the others.
    pilot_id: str | None
    name: str
    squadron: str
    aircraft: str
    fate: str

    class Config:
        title = "WarDiaryPilot"


class WarDiaryAwardJs(BaseModel):
    pilot_id: str
    pilot: str
    kind: str
    name: str
    abbreviation: str
    reason: str

    class Config:
        title = "WarDiaryAward"


class WarDiaryEntryJs(BaseModel):
    turn: int
    date: str
    weather: str
    verdict: str
    verdict_tone: ToneJs
    summary: str
    air_kills_friendly: int
    air_kills_enemy: int
    ground_kills_friendly: int
    ground_kills_enemy: int
    bases: list[WarDiaryBaseJs]
    fronts: list[WarDiaryFrontJs]
    packages: list[WarDiaryPackageJs]
    friendly_losses: list[WarDiaryLossJs]
    enemy_losses: list[WarDiaryLossJs]
    pilots: list[WarDiaryPilotJs]
    awards: list[WarDiaryAwardJs]
    budget_next_turn: float | None
    income_next_turn: float | None

    class Config:
        title = "WarDiaryEntry"

    @staticmethod
    def from_entry(entry: DiaryEntry) -> WarDiaryEntryJs:
        return WarDiaryEntryJs(**dataclasses.asdict(entry))


class WarDiaryJs(BaseModel):
    campaign: str
    #: The first turn of the diary of a campaign started before it; null when it
    #: covers the whole campaign.
    since_turn: int | None
    entries: list[WarDiaryEntryJs]

    class Config:
        title = "WarDiary"

    @staticmethod
    def from_game(game: Game) -> WarDiaryJs:
        return WarDiaryJs(
            campaign=game.campaign_name or "",
            since_turn=game.war_diary_since_turn,
            entries=[WarDiaryEntryJs.from_entry(e) for e in reversed(game.war_diary)],
        )

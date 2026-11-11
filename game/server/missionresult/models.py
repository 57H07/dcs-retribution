from __future__ import annotations

import dataclasses
from enum import Enum

from pydantic import BaseModel

from game.commands import MissionResultSnapshot, MissionResultStatus
from game.debriefingreport import AfterActionReport, PilotLine, SortieCard, Tone
from game.theater import Player


class MissionResultStatusJs(str, Enum):
    IDLE = "idle"
    WAITING = "waiting"
    DETECTED = "detected"
    ERROR = "error"

    @staticmethod
    def from_status(status: MissionResultStatus) -> MissionResultStatusJs:
        return MissionResultStatusJs(status.value)


class LossRowJs(BaseModel):
    """One line of the mission status: losses of each side so far."""

    label: str
    blue: int
    red: int

    class Config:
        title = "LossRow"


class MissionResultJs(BaseModel):
    """What the waiting screen shows (Qt: QWaitingForMissionResultWindow)."""

    status: MissionResultStatusJs
    #: The .miz to start in DCS; null when no mission waits for its result.
    miz_path: str | None
    #: The state.json watched for the result.
    state_path: str
    #: True once the mission is over: its results can be accepted.
    mission_ended: bool
    #: Why the last read of state.json failed (status "error").
    error: str | None
    player_country: str | None
    enemy_country: str | None
    #: Losses per side, empty until a state.json was read.
    losses: list[LossRowJs]
    #: Seconds of mission played when DCS last wrote state.json, on the origin of
    #: `GET /game/timeline`; null until DCS reports its clock.
    mission_elapsed: float | None

    class Config:
        title = "MissionResult"

    @staticmethod
    def from_snapshot(snapshot: MissionResultSnapshot) -> MissionResultJs:
        debriefing = snapshot.debriefing
        losses: list[LossRowJs] = []
        player_country = enemy_country = None
        mission_elapsed = None
        if debriefing is not None:
            mission_elapsed = debriefing.mission_elapsed
            player_country = debriefing.player_country
            enemy_country = debriefing.enemy_country
            blue = debriefing.loss_counts(Player.BLUE)
            red = debriefing.loss_counts(Player.RED)
            rows = [
                ("Aircraft lost", blue.aircraft, red.aircraft),
                ("Front line units lost", blue.front_line, red.front_line),
                ("Motorpool units lost", blue.motorpool, red.motorpool),
                ("Convoy units lost", blue.convoy, red.convoy),
                ("Shipping cargo lost", blue.cargo_ships, red.cargo_ships),
                ("Airlift cargo lost", blue.airlift_cargo, red.airlift_cargo),
                ("Ground Objects lost", blue.ground_objects, red.ground_objects),
                ("Scenery Objects lost", blue.scenery, red.scenery),
                ("Bases lost", blue.bases_lost, red.bases_lost),
                ("Runways destroyed", blue.runways_destroyed, red.runways_destroyed),
                ("Pilots rescued (CSAR)", blue.pilots_rescued, red.pilots_rescued),
            ]
            losses = [LossRowJs(label=n, blue=b, red=r) for n, b, r in rows]
        return MissionResultJs(
            status=MissionResultStatusJs.from_status(snapshot.status),
            miz_path=None if snapshot.miz_path is None else str(snapshot.miz_path),
            state_path=str(snapshot.state_path),
            mission_ended=snapshot.mission_ended,
            error=snapshot.error,
            player_country=player_country,
            enemy_country=enemy_country,
            losses=losses,
            mission_elapsed=mission_elapsed,
        )


class ToneJs(str, Enum):
    GOOD = "good"
    BAD = "bad"
    MIXED = "mixed"
    NEUTRAL = "neutral"

    @staticmethod
    def from_tone(tone: Tone) -> ToneJs:
        return ToneJs(tone.value)


class LossLineJs(BaseModel):
    name: str
    count: int

    class Config:
        title = "LossLine"


class PilotLineJs(BaseModel):
    name: str
    aircraft: str
    squadron: str
    held_at: str | None

    class Config:
        title = "PilotLine"


class PackageResultJs(BaseModel):
    task: str
    target: str
    flights: list[str]
    lost: int
    aircraft: int
    result: str
    tone: ToneJs

    class Config:
        title = "PackageResult"


class ReportEventJs(BaseModel):
    #: HH:MM:SS: the DCS clock of a mission event (null when state.json does not
    #: date it), the wall-clock time of an event the engine logged.
    time: str | None
    text: str
    tone: ToneJs

    class Config:
        title = "ReportEvent"


class ObjectiveLineJs(BaseModel):
    title: str
    met: bool
    granted: str

    class Config:
        title = "ObjectiveLine"


class DamagedUnitLineJs(BaseModel):
    friendly: bool
    unit_type: str
    damage_percent: int
    unavailability: str

    class Config:
        title = "DamagedUnitLine"


class SortieAwardJs(BaseModel):
    kind: str
    name: str
    abbreviation: str
    reason: str

    class Config:
        title = "SortieAward"


class SortieCardJs(BaseModel):
    """How the mission went for one player pilot (#192)."""

    pilot_id: str
    pilot: str
    squadron: str
    aircraft: str
    flight: str
    task: str
    target: str
    package_result: str
    package_tone: ToneJs
    air_kills: int
    ground_kills: int
    naval_kills: int
    fate: str
    fate_tone: ToneJs
    flight_time: str
    #: Null until the results are applied.
    sorties_logged: int | None
    rescues: int | None
    awards: list[SortieAwardJs] | None

    class Config:
        title = "SortieCard"

    @staticmethod
    def from_card(card: SortieCard) -> SortieCardJs:
        return SortieCardJs(
            pilot_id=card.pilot_id,
            pilot=card.pilot,
            squadron=card.squadron,
            aircraft=card.aircraft,
            flight=card.flight,
            task=card.task,
            target=card.target,
            package_result=card.package_result,
            package_tone=ToneJs.from_tone(card.package_tone),
            air_kills=card.air_kills,
            ground_kills=card.ground_kills,
            naval_kills=card.naval_kills,
            fate=card.fate,
            fate_tone=ToneJs.from_tone(card.fate_tone),
            flight_time=card.flight_time,
            sorties_logged=card.sorties_logged,
            rescues=card.rescues,
            awards=(
                None
                if card.awards is None
                else [SortieAwardJs(**dataclasses.asdict(a)) for a in card.awards]
            ),
        )


class AfterActionReportJs(BaseModel):
    """The after-action report (`game.debriefingreport.AfterActionReport`)."""

    turn: int
    date: str
    player_country: str
    enemy_country: str
    verdict: str
    verdict_tone: ToneJs
    summary: str
    air_kills_friendly: int
    air_kills_enemy: int
    ground_kills_friendly: int
    ground_kills_enemy: int
    bases_captured: int
    bases_lost: int
    pilots_rescued: list[PilotLineJs]
    rescue_bounty: int
    packages: list[PackageResultJs]
    friendly_losses: list[LossLineJs]
    enemy_losses: list[LossLineJs]
    damaged_units: list[DamagedUnitLineJs]
    events: list[ReportEventJs]
    #: One card per player pilot of the mission; empty without any.
    your_sorties: list[SortieCardJs]
    #: True once the results were applied; the fields below are null before.
    applied: bool
    pilots_captured: list[PilotLineJs] | None
    pilots_still_down: int | None
    budget_next_turn: float | None
    income_next_turn: float | None
    #: The campaign objectives met or missed at the end of the turn (#194).
    objectives: list[ObjectiveLineJs] | None

    class Config:
        title = "AfterActionReport"

    @staticmethod
    def from_report(report: AfterActionReport) -> AfterActionReportJs:
        def pilots(lines: list[PilotLine]) -> list[PilotLineJs]:
            return [PilotLineJs(**dataclasses.asdict(p)) for p in lines]

        return AfterActionReportJs(
            turn=report.turn,
            date=report.date,
            player_country=report.player_country,
            enemy_country=report.enemy_country,
            verdict=report.verdict,
            verdict_tone=ToneJs.from_tone(report.verdict_tone),
            summary=report.summary,
            air_kills_friendly=report.air_kills_friendly,
            air_kills_enemy=report.air_kills_enemy,
            ground_kills_friendly=report.ground_kills_friendly,
            ground_kills_enemy=report.ground_kills_enemy,
            bases_captured=report.bases_captured,
            bases_lost=report.bases_lost,
            pilots_rescued=pilots(report.pilots_rescued),
            rescue_bounty=report.rescue_bounty,
            packages=[
                PackageResultJs(
                    task=p.task,
                    target=p.target,
                    flights=list(p.flights),
                    lost=p.lost,
                    aircraft=p.aircraft,
                    result=p.result,
                    tone=ToneJs.from_tone(p.tone),
                )
                for p in report.packages
            ],
            friendly_losses=[
                LossLineJs(name=x.name, count=x.count) for x in report.friendly_losses
            ],
            enemy_losses=[
                LossLineJs(name=x.name, count=x.count) for x in report.enemy_losses
            ],
            damaged_units=[
                DamagedUnitLineJs(**dataclasses.asdict(d)) for d in report.damaged_units
            ],
            events=[
                ReportEventJs(time=e.time, text=e.text, tone=ToneJs.from_tone(e.tone))
                for e in report.events
            ],
            your_sorties=[SortieCardJs.from_card(c) for c in report.your_sorties],
            applied=report.applied,
            pilots_captured=(
                None
                if report.pilots_captured is None
                else pilots(report.pilots_captured)
            ),
            pilots_still_down=report.pilots_still_down,
            budget_next_turn=report.budget_next_turn,
            income_next_turn=report.income_next_turn,
            objectives=(
                None
                if report.objectives is None
                else [
                    ObjectiveLineJs(**dataclasses.asdict(o)) for o in report.objectives
                ]
            ),
        )


class DebriefingStatusJs(str, Enum):
    #: No result received yet, and none accepted since the application started.
    NONE = "none"
    #: A result was received and is not applied yet.
    PENDING = "pending"
    #: The last accepted result.
    ACCEPTED = "accepted"


class DebriefingJs(BaseModel):
    """What the /debrief screen shows (Qt: QDebriefingWindow)."""

    status: DebriefingStatusJs
    #: True when "Accept results" can be pressed: pending and the mission is over.
    can_accept: bool
    report: AfterActionReportJs | None

    class Config:
        title = "Debriefing"

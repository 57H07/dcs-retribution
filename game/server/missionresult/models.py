from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from game.commands import MissionResultSnapshot, MissionResultStatus
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

    class Config:
        title = "MissionResult"

    @staticmethod
    def from_snapshot(snapshot: MissionResultSnapshot) -> MissionResultJs:
        debriefing = snapshot.debriefing
        losses: list[LossRowJs] = []
        player_country = enemy_country = None
        if debriefing is not None:
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
        )

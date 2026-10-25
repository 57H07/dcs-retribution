from __future__ import annotations

from dataclasses import dataclass, field
from enum import unique, Enum
from typing import Any

from faker import Faker


@unique
class KillCategory(Enum):
    """What kind of target a pilot destroyed."""

    Air = "Air"
    Ground = "Ground"
    Naval = "Naval"


@dataclass
class PilotRecord:
    missions_flown: int = field(default=0)
    air_kills: int = field(default=0)
    ground_kills: int = field(default=0)
    naval_kills: int = field(default=0)

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Saves made before kills were attributed to pilots (PER-03.1).
        state.setdefault("air_kills", 0)
        state.setdefault("ground_kills", 0)
        state.setdefault("naval_kills", 0)
        self.__dict__.update(state)

    def credit_kill(self, category: KillCategory) -> None:
        if category is KillCategory.Air:
            self.air_kills += 1
        elif category is KillCategory.Ground:
            self.ground_kills += 1
        else:
            self.naval_kills += 1

    def kills(self, category: KillCategory) -> int:
        if category is KillCategory.Air:
            return self.air_kills
        if category is KillCategory.Ground:
            return self.ground_kills
        return self.naval_kills


@unique
class PilotStatus(Enum):
    Active = "Active"
    OnLeave = "On leave"
    Dead = "Dead"


@dataclass
class Pilot:
    name: str
    player: bool = field(default=False)
    status: PilotStatus = field(default=PilotStatus.Active)
    record: PilotRecord = field(default_factory=PilotRecord)

    @property
    def alive(self) -> bool:
        return self.status is not PilotStatus.Dead

    @property
    def on_leave(self) -> bool:
        return self.status is PilotStatus.OnLeave

    def send_on_leave(self) -> None:
        if self.status is not PilotStatus.Active:
            raise RuntimeError("Only active pilots may be sent on leave")
        self.status = PilotStatus.OnLeave

    def return_from_leave(self) -> None:
        if self.status is not PilotStatus.OnLeave:
            raise RuntimeError("Only pilots on leave may be returned from leave")
        self.status = PilotStatus.Active

    def kill(self) -> None:
        self.status = PilotStatus.Dead

    @classmethod
    def random(cls, faker: Faker) -> Pilot:
        return Pilot(faker.name())

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import unique, Enum
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID

from faker import Faker

if TYPE_CHECKING:
    from game.ato.flighttype import FlightType


@unique
class KillCategory(Enum):
    """What kind of target a pilot destroyed."""

    Air = "Air"
    Ground = "Ground"
    Naval = "Naval"


@unique
class AwardKind(Enum):
    Rank = "Rank"
    Decoration = "Decoration"


@dataclass(frozen=True)
class Award:
    """A rank or decoration received by a pilot (PER-03.3).

    Only plain values are stored: the award outlives the rules that granted it.
    """

    kind: AwardKind
    name: str
    #: Campaign turn of the mission after which it was awarded.
    turn: int
    #: Start of that mission (campaign date and time).
    date: datetime.datetime
    description: str = ""


@dataclass(frozen=True)
class LogbookEntry:
    """One sortie in a pilot's logbook (PER-03.2).

    Only plain values are stored so that the entry outlives the flight, the
    squadron and the turn it was created in.
    """

    #: Campaign turn the mission was flown in.
    turn: int
    #: Mission start (campaign date and time).
    date: datetime.datetime
    squadron: str
    aircraft: str
    task: FlightType
    #: True if the flight had a combat task or the pilot scored a kill.
    combat: bool
    #: Planned time from takeoff to landing.
    flight_time: datetime.timedelta
    air_kills: int = 0
    ground_kills: int = 0
    naval_kills: int = 0
    #: True if the pilot's aircraft was lost with the pilot aboard. Counted even
    #: when the pilot survived because player pilots are invulnerable.
    died: bool = False

    def kills(self, category: KillCategory) -> int:
        if category is KillCategory.Air:
            return self.air_kills
        if category is KillCategory.Ground:
            return self.ground_kills
        return self.naval_kills


@dataclass
class PilotRecord:
    """A pilot's logbook: campaign totals plus a per-sortie history.

    Totals are kept for every pilot. The per-sortie ``logbook`` is only filled
    for player pilots, whose records are their careers (see
    ``game.squadrons.career``). Nothing here affects gameplay except
    ``missions_flown``, which predates the logbook and drives AI levelling.
    """

    #: Sorties flown. Named before the logbook existed; see ``sorties``.
    missions_flown: int = field(default=0)
    air_kills: int = field(default=0)
    ground_kills: int = field(default=0)
    naval_kills: int = field(default=0)
    combat_sorties: int = field(default=0)
    deaths: int = field(default=0)
    flight_time: datetime.timedelta = field(default_factory=datetime.timedelta)
    logbook: list[LogbookEntry] = field(default_factory=list)
    #: Ranks and decorations in the order they were awarded (PER-03.3).
    awards: list[Award] = field(default_factory=list)

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Saves made before kills were attributed to pilots (PER-03.1).
        state.setdefault("air_kills", 0)
        state.setdefault("ground_kills", 0)
        state.setdefault("naval_kills", 0)
        # Saves made before the logbook existed (PER-03.2).
        state.setdefault("combat_sorties", 0)
        state.setdefault("deaths", 0)
        state.setdefault("flight_time", datetime.timedelta())
        state.setdefault("logbook", [])
        # Saves made before ranks and decorations existed (PER-03.3).
        state.setdefault("awards", [])
        self.__dict__.update(state)

    @property
    def sorties(self) -> int:
        return self.missions_flown

    @property
    def total_kills(self) -> int:
        return self.air_kills + self.ground_kills + self.naval_kills

    @property
    def rank(self) -> Optional[Award]:
        """The latest rank awarded, if any."""
        ranks = [a for a in self.awards if a.kind is AwardKind.Rank]
        return ranks[-1] if ranks else None

    @property
    def decorations(self) -> list[Award]:
        return [a for a in self.awards if a.kind is AwardKind.Decoration]

    def has_award(self, kind: AwardKind, name: str) -> bool:
        return any(a.kind is kind and a.name == name for a in self.awards)

    def log_sortie(self, entry: LogbookEntry, keep_history: bool) -> None:
        """Adds a sortie to the totals, and to the history if keep_history.

        Kills are not added here: ``credit_kill`` already counted them when the
        mission results were committed. The entry only carries the kills of that
        sortie for the history.
        """
        self.missions_flown += 1
        if entry.combat:
            self.combat_sorties += 1
        if entry.died:
            self.deaths += 1
        self.flight_time += entry.flight_time
        if keep_history:
            self.logbook.append(entry)

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
    #: Ejected/shot down and awaiting CSAR rescue on the map.
    Downed = "Downed"
    #: Rescued by CSAR but temporarily unavailable while recovering.
    Recovering = "Recovering"
    #: A downed pilot who was never rescued in time.
    MissingInAction = "Missing in action"


@dataclass
class Pilot:
    name: str
    player: bool = field(default=False)
    status: PilotStatus = field(default=PilotStatus.Active)
    record: PilotRecord = field(default_factory=PilotRecord)
    #: Number of turns until a Recovering pilot returns to Active. Only meaningful
    #: while status is Recovering.
    turns_until_available: int = field(default=0)
    #: The control point holding this pilot prisoner, for one who went missing
    #: rather than being rescued. Retaking that base frees them. None means their
    #: fate is not tied to any base, and they stay missing.
    held_at: Optional[UUID] = field(default=None)

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Older saves predate CSAR and won't have these fields.
        state.setdefault("turns_until_available", 0)
        state.setdefault("held_at", None)
        self.__dict__.update(state)

    @property
    def alive(self) -> bool:
        return self.status not in (PilotStatus.Dead, PilotStatus.MissingInAction)

    @property
    def on_leave(self) -> bool:
        return self.status is PilotStatus.OnLeave

    @property
    def downed(self) -> bool:
        return self.status is PilotStatus.Downed

    @property
    def recovering(self) -> bool:
        return self.status is PilotStatus.Recovering

    @property
    def missing_in_action(self) -> bool:
        return self.status is PilotStatus.MissingInAction

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

    def go_down(self) -> None:
        """Marks the pilot as shot down and awaiting CSAR rescue."""
        self.status = PilotStatus.Downed

    def go_mia(self, held_at: Optional[UUID] = None) -> None:
        """Marks a downed pilot as missing in action (rescue never came).

        ``held_at`` is the control point that took them prisoner, if any. Taking
        that base back frees them; see ``release_from_captivity``.
        """
        if self.status is not PilotStatus.Downed:
            raise RuntimeError("Only downed pilots may go missing in action")
        self.status = PilotStatus.MissingInAction
        self.held_at = held_at

    def release_from_captivity(self, turns: int) -> None:
        """Frees a prisoner when the base holding them is retaken."""
        if self.status is not PilotStatus.MissingInAction:
            raise RuntimeError("Only missing pilots may be released from captivity")
        self.held_at = None
        self.status = PilotStatus.Downed
        self.begin_recovery(turns)

    def begin_recovery(self, turns: int) -> None:
        """Marks a rescued pilot as recovering for the given number of turns.

        A value of zero (or less) returns the pilot to active duty immediately.
        """
        if turns <= 0:
            self.status = PilotStatus.Active
            self.turns_until_available = 0
            return
        self.status = PilotStatus.Recovering
        self.turns_until_available = turns

    def advance_recovery(self) -> None:
        """Advances a recovering pilot's countdown by one turn.

        Returns the pilot to active duty once the countdown reaches zero.
        """
        if self.status is not PilotStatus.Recovering:
            return
        self.turns_until_available -= 1
        if self.turns_until_available <= 0:
            self.turns_until_available = 0
            self.status = PilotStatus.Active

    @classmethod
    def random(cls, faker: Faker) -> Pilot:
        return Pilot(faker.name())

"""Career screen (WEB-08.2): read model of the Qt `CareerDialog` (PER-03.4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from game.squadrons.careerreport import format_date, format_duration, loss, totals

if TYPE_CHECKING:
    from game.squadrons.career import Career
    from game.squadrons.pilot import Award, LogbookEntry


class CareerTotalJs(BaseModel):
    label: str
    value: str


class AwardJs(BaseModel):
    name: str
    #: "Rank" or "Decoration".
    kind: str
    date: str
    turn: int
    description: str

    @staticmethod
    def from_award(award: Award) -> AwardJs:
        return AwardJs(
            name=award.name,
            kind=award.kind.value,
            date=format_date(award.date),
            turn=award.turn,
            description=award.description,
        )


class LogbookEntryJs(BaseModel):
    turn: int
    date: str
    squadron: str
    aircraft: str
    task: str
    combat: bool
    flight_time: str
    air_kills: int
    ground_kills: int
    naval_kills: int
    rescues: int
    #: "", "Ejected", "Killed" or "Ejected, killed".
    loss: str

    @staticmethod
    def from_entry(entry: LogbookEntry) -> LogbookEntryJs:
        return LogbookEntryJs(
            turn=entry.turn,
            date=format_date(entry.date),
            squadron=entry.squadron,
            aircraft=entry.aircraft,
            task=entry.task.value,
            combat=entry.combat,
            flight_time=format_duration(entry.flight_time),
            air_kills=entry.air_kills,
            ground_kills=entry.ground_kills,
            naval_kills=entry.naval_kills,
            rescues=entry.rescues,
            loss=loss(entry),
        )


class CareerJs(BaseModel):
    """A player pilot's logbook, rank, decorations and missions."""

    pilot: str
    squadron: str
    status: str
    alive: bool
    #: Latest rank awarded, null before the first one.
    rank: str | None
    totals: list[CareerTotalJs]
    awards: list[AwardJs]
    #: One entry per mission, most recent first.
    history: list[LogbookEntryJs]

    @staticmethod
    def from_career(career: Career) -> CareerJs:
        pilot = career.pilot
        record = career.logbook
        return CareerJs(
            pilot=pilot.name,
            squadron=str(career.squadron),
            status=pilot.status.value,
            alive=pilot.alive,
            rank=record.rank.name if record.rank is not None else None,
            totals=[
                CareerTotalJs(label=label, value=value)
                for label, value in totals(record)
            ],
            awards=[AwardJs.from_award(a) for a in record.awards],
            history=[LogbookEntryJs.from_entry(e) for e in reversed(record.logbook)],
        )

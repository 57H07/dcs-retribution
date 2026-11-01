"""Text of a pilot's career page (PER-03.4), shared by the web UI (WEB-08.2) and
the Qt `CareerDialog`."""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from .pilot import Award, LogbookEntry, PilotRecord


def format_duration(duration: datetime.timedelta) -> str:
    minutes = int(duration.total_seconds() // 60)
    return f"{minutes // 60}:{minutes % 60:02d}"


def format_date(date: datetime.datetime) -> str:
    return date.strftime("%Y-%m-%d %H:%M")


def totals(record: PilotRecord) -> list[tuple[str, str]]:
    """Logbook totals as (label, value) rows."""
    return [
        ("Sorties", str(record.sorties)),
        ("Combat sorties", str(record.combat_sorties)),
        ("Air kills", str(record.air_kills)),
        ("Ground kills", str(record.ground_kills)),
        ("Naval kills", str(record.naval_kills)),
        ("Shot down", str(record.shot_down)),
        ("Ejections", str(record.ejections)),
        ("Rescued by CSAR", str(record.times_rescued)),
        ("Pilots rescued", str(record.pilots_rescued)),
        ("Killed", str(record.deaths)),
        ("Flight time", format_duration(record.flight_time)),
    ]


AWARD_HEADERS = ["Award", "Type", "Date", "Turn", "Details"]


def award_rows(awards: Sequence[Award]) -> list[list[str]]:
    return [
        [a.name, a.kind.value, format_date(a.date), str(a.turn), a.description]
        for a in awards
    ]


HISTORY_HEADERS = [
    "Turn",
    "Date",
    "Squadron",
    "Aircraft",
    "Task",
    "Combat",
    "Flight time",
    "Air",
    "Ground",
    "Naval",
    "Rescues",
    "Lost",
]


def loss(entry: LogbookEntry) -> str:
    if entry.ejected and entry.died:
        return "Ejected, killed"
    if entry.ejected:
        return "Ejected"
    if entry.died:
        return "Killed"
    return ""


def history_rows(logbook: Sequence[LogbookEntry]) -> list[list[str]]:
    """One row per mission, most recent first."""
    return [
        [
            str(e.turn),
            format_date(e.date),
            e.squadron,
            e.aircraft,
            e.task.value,
            "Yes" if e.combat else "",
            format_duration(e.flight_time),
            str(e.air_kills),
            str(e.ground_kills),
            str(e.naval_kills),
            str(e.rescues) if e.rescues else "",
            loss(e),
        ]
        for e in reversed(logbook)
    ]

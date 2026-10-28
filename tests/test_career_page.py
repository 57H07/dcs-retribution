"""PER-03.4: content of the career page."""

from datetime import datetime, timedelta

from game.ato.flighttype import FlightType
from game.squadrons.pilot import (
    Award,
    AwardKind,
    KillCategory,
    LogbookEntry,
    PilotRecord,
)
from qt_ui.windows.CareerDialog import (
    HISTORY_HEADERS,
    award_rows,
    format_duration,
    history_rows,
    totals,
)


def _entry(turn: int, air_kills: int = 0, died: bool = False) -> LogbookEntry:
    return LogbookEntry(
        turn=turn,
        date=datetime(2026, 6, turn, 8, 30),
        squadron="VF-1",
        aircraft="F-14B",
        task=FlightType.BARCAP,
        combat=True,
        flight_time=timedelta(hours=1, minutes=5),
        air_kills=air_kills,
        died=died,
    )


def _record_after_two_missions() -> PilotRecord:
    record = PilotRecord()
    for entry in (_entry(1, air_kills=2), _entry(2, died=True)):
        for _ in range(entry.air_kills):
            record.credit_kill(KillCategory.Air)
        record.log_sortie(entry, keep_history=True)
    return record


def test_totals_show_the_logbook() -> None:
    rows = dict(totals(_record_after_two_missions()))

    assert rows["Sorties"] == "2"
    assert rows["Combat sorties"] == "2"
    assert rows["Air kills"] == "2"
    assert rows["Shot down"] == "1"
    assert rows["Killed"] == "1"
    assert rows["Ejections"] == "0"
    assert rows["Flight time"] == "2:10"


def test_history_lists_both_missions_most_recent_first() -> None:
    rows = history_rows(_record_after_two_missions().logbook)

    assert len(rows) == 2
    assert all(len(row) == len(HISTORY_HEADERS) for row in rows)
    assert [row[0] for row in rows] == ["2", "1"]
    assert rows[0][1] == "2026-06-02 08:30"
    assert rows[1][HISTORY_HEADERS.index("Air")] == "2"
    assert rows[0][HISTORY_HEADERS.index("Lost")] == "Killed"
    assert rows[1][HISTORY_HEADERS.index("Lost")] == ""
    assert rows[1][HISTORY_HEADERS.index("Task")] == "BARCAP"


def test_award_rows() -> None:
    ace = Award(AwardKind.Decoration, "Ace", 4, datetime(2026, 6, 4), "Five kills.")

    assert award_rows([ace]) == [
        ["Ace", "Decoration", "2026-06-04 00:00", "4", "Five kills."]
    ]


def test_format_duration() -> None:
    assert format_duration(timedelta()) == "0:00"
    assert format_duration(timedelta(hours=12, minutes=7, seconds=59)) == "12:07"

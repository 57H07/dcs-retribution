"""#193: the war diary, one entry per accepted mission result."""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from game import wardiary
from game.commands import missionresult as missionresult_module
from game.commands.missionresult import accept_and_report
from game.debriefingreport import (
    AfterActionReport,
    PilotLine,
    SortieAward,
    Tone,
    build_report,
)
from game.game import Game
from game.squadrons.pilot import PilotStatus
from game.wardiary import (
    DiaryAward,
    DiaryBase,
    DiaryFront,
    DiaryLoss,
    DiaryPackage,
    DiaryPilot,
    FrontPosition,
    TurnSnapshot,
    build_entry,
    export_html,
)
from tests.test_debriefing_report import _debriefing
from tests.test_your_sortie import _mission

KRYMSK = uuid4()


def _applied(report: AfterActionReport) -> AfterActionReport:
    """`report` as `complete_report` leaves it."""
    [card, *others] = report.your_sorties
    card = dataclasses.replace(
        card,
        awards=[SortieAward("Rank", "First Lieutenant", "1st Lt", "")],
    )
    return dataclasses.replace(
        report,
        applied=True,
        your_sorties=[card, *others],
        pilots_captured=[PilotLine("Lt. Sydorenko", "Su-25T", "Rooks", "Maykop")],
        pilots_still_down=0,
        budget_next_turn=1420.5,
        income_next_turn=180.0,
    )


def _entry() -> tuple[wardiary.DiaryEntry, dict[str, Any]]:
    debriefing, parts = _mission()
    debriefing.base_captures[0].control_point.id = KRYMSK
    moroz = parts["moroz"]
    moroz.status = PilotStatus.Dead
    report = _applied(build_report(debriefing))
    before = TurnSnapshot(
        weather="Partly Cloudy, no rain, no fog",
        fronts=(
            FrontPosition(("a", "b"), "Krymsk – Krasnodar", 10000.0),
            FrontPosition(("c", "d"), "Anapa – Novorossiysk", 8000.0),
        ),
    )
    after = (
        FrontPosition(("a", "b"), "Krymsk – Krasnodar", 12400.0),
        FrontPosition(("c", "d"), "Anapa – Novorossiysk", 7950.0),
    )
    return build_entry(report, debriefing, before, after), parts


def test_an_entry_keeps_what_the_debrief_decided() -> None:
    entry, parts = _entry()

    assert (entry.turn, entry.date) == (4, "17 May 2022")
    assert entry.weather == "Partly Cloudy, no rain, no fog"
    assert entry.bases == [DiaryBase(str(KRYMSK), "Krymsk", taken=True)]
    # Moves under 100 m are noise.
    assert entry.fronts == [DiaryFront("Krymsk – Krasnodar", 2.4)]
    assert entry.packages[0] == DiaryPackage(
        task="Strike",
        target="Ammo depot",
        flights=["Uzi 1"],
        lost=1,
        aircraft=2,
        result=entry.packages[0].result,
        tone=entry.packages[0].tone,
    )
    assert entry.friendly_losses == [DiaryLoss("F/A-18C", 1)]
    moroz = parts["moroz"]
    assert entry.pilots == [
        DiaryPilot(str(moroz.id), "Lt. Moroz", "VF-11", "F/A-18C", "Killed in action"),
        DiaryPilot(None, "Lt. Sydorenko", "Rooks", "Su-25T", "Taken prisoner"),
        DiaryPilot(
            str(parts["bondar"].id), "Maj. Bondar", "Rooks", "Su-25T", "Rescued"
        ),
    ]
    assert entry.awards == [
        DiaryAward(str(moroz.id), "Lt. Moroz", "Rank", "First Lieutenant", "1st Lt", "")
    ]
    assert (entry.budget_next_turn, entry.income_next_turn) == (1420.5, 180.0)
    assert entry.verdict_tone == Tone.GOOD.value


def test_the_summary_tells_the_turn_in_one_line() -> None:
    entry, _ = _entry()

    assert entry.summary == (
        "Krymsk taken, Krymsk – Krasnodar front advanced 2.4 km, 1 aircraft lost, "
        "Lt. Moroz killed, Maj. Bondar rescued, Lt. Moroz promoted to First Lieutenant"
    )


def test_a_quiet_turn_is_summed_up_by_its_verdict() -> None:
    debriefing, _ = _debriefing()
    debriefing.base_captures = []
    debriefing.air_losses = dataclasses.replace(
        debriefing.air_losses, player=[], enemy=[]
    )
    debriefing.ejected_pilot_positions = {}
    report = dataclasses.replace(
        build_report(debriefing), pilots_rescued=[], applied=True
    )

    entry = build_entry(report, debriefing, TurnSnapshot("Clear", ()), ())

    assert entry.summary == report.summary


def test_three_accepted_results_give_three_entries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    built = iter(range(1, 4))
    recorded: list[int] = []
    saved: list[Any] = []

    monkeypatch.setattr(
        missionresult_module, "accept_results", lambda game, sim, d: None
    )
    monkeypatch.setattr(
        missionresult_module,
        "build_report",
        lambda d: SimpleNamespace(turn=next(built)),
    )
    monkeypatch.setattr(
        missionresult_module, "complete_report", lambda report, d, messages: report
    )
    monkeypatch.setattr(wardiary, "snapshot", lambda game: TurnSnapshot("Clear", ()))
    monkeypatch.setattr(wardiary, "front_positions", lambda game: ())
    monkeypatch.setattr(
        wardiary,
        "build_entry",
        lambda report, debriefing, before, after: report.turn,
    )
    monkeypatch.setattr(
        wardiary.autosaves, "autosave", lambda game, kind: saved.append(kind)
    )
    game = SimpleNamespace(informations=[], war_diary=recorded)

    for _ in range(3):
        accept_and_report(cast(Any, game), cast(Any, None), cast(Any, None))

    assert recorded == [1, 2, 3]
    # The autosave of the new turn carries its entry.
    assert saved == [wardiary.autosaves.SaveKind.TURN] * 3


def test_a_failing_diary_never_blocks_the_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        missionresult_module, "accept_results", lambda game, sim, d: None
    )
    monkeypatch.setattr(missionresult_module, "build_report", lambda d: "report")
    monkeypatch.setattr(
        missionresult_module, "complete_report", lambda report, d, messages: report
    )

    def broken(game: Any) -> Any:
        raise RuntimeError("no theater")

    monkeypatch.setattr(wardiary, "snapshot", broken)
    game = SimpleNamespace(informations=[], war_diary=[])

    assert accept_and_report(cast(Any, game), cast(Any, None), cast(Any, None)) == (
        "report"
    )
    assert game.war_diary == []


def test_an_old_save_starts_its_diary_at_the_next_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Game, "on_load", lambda self, **kwargs: None)
    game = Game.__new__(Game)
    game.__setstate__(
        {
            "turn": 12,
            "pilots_captured_this_turn": [],
            "campaign_id": "abc",
            "laser_code_registry": object(),
        }
    )

    assert game.war_diary == []
    assert game.war_diary_since_turn == 12


def test_the_export_is_one_page_that_needs_nothing_else() -> None:
    entry, _ = _entry()
    older = dataclasses.replace(entry, turn=3, summary="Quiet <day>")

    page = export_html("Operation <Dawn>", [older, entry], since_turn=3)

    assert page.startswith("<!doctype html>")
    assert "<title>War diary · Operation &lt;Dawn&gt;</title>" in page
    # Newest first.
    assert page.index("Turn 4") < page.index("Turn 3")
    assert "Quiet &lt;day&gt;" in page
    assert "Krymsk taken" in page
    assert "Lt. Moroz" in page
    # Self-contained: no script, no outside file.
    assert "<script" not in page and "http" not in page
    assert "The diary begins at turn 3" in page

"""#192: the 'Your sortie' cards of the after-action report, one per player pilot."""

from __future__ import annotations

import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from game.ato.flighttype import FlightType
from game.debriefing import AirLosses, Debriefing, GroundLosses, RescuedPilot
from game.debriefingreport import (
    SortieAward,
    SortieCard,
    Tone,
    build_report,
    complete_report,
)
from game.squadrons.awards import load_rules
from game.squadrons.pilot import (
    Award,
    AwardKind,
    KillCategory,
    LogbookEntry,
    Pilot,
    PilotStatus,
)
from game.theater import Player
from tests.test_debriefing_report import _debriefing, _flight, _package, _Squadron

RULES = load_rules([Path("tests/resources/careers")])
DATE = datetime.datetime(2022, 5, 17, 6, 0)


def _kill(pilot: Pilot, flight: Any, category: KillCategory) -> Any:
    return SimpleNamespace(pilot=pilot, flight=flight, category=category, time=None)


def _entry(turn: int, **kwargs: Any) -> LogbookEntry:
    values: dict[str, Any] = dict(
        turn=turn,
        date=DATE,
        squadron="VF-11",
        aircraft="F/A-18C",
        task=FlightType.STRIKE,
        combat=True,
        flight_time=datetime.timedelta(minutes=65),
    )
    values.update(kwargs)
    return LogbookEntry(**values)


def _award(kind: AwardKind, name: str, turn: int, description: str = "") -> Award:
    return Award(kind, name, turn, DATE, description)


def _mission() -> tuple[Debriefing, dict[str, Any]]:
    """Two player pilots flew, one was shot down; a third was rescued by CSAR."""
    debriefing, parts = _debriefing()
    game = parts["game"]
    squadron = _Squadron("VF-11", Player.BLUE)
    moroz = Pilot("Lt. Moroz", player=True)
    wingman = Pilot("Lt. Petrenko")
    kovalenko = Pilot("Capt. Kovalenko", player=True)
    bondar = Pilot("Maj. Bondar", player=True)
    uzi = _flight(squadron, "F/A-18C", 2, "Uzi 1", (moroz, wingman), minutes=65)
    viper = _flight(
        squadron, "F-16CM", 1, "Viper 1", (kovalenko,), FlightType.DEAD, minutes=50
    )
    depot = game.blue.ato.packages[1].target
    sam = game.blue.ato.packages[0].target
    game.blue.ato.packages = [
        _package("Strike", depot, [uzi]),
        _package("DEAD", sam, [viper]),
    ]
    game.blue.air_wing = SimpleNamespace(
        iter_squadrons=lambda: iter(
            [SimpleNamespace(current_roster=[moroz, wingman, kovalenko, bondar])]
        )
    )
    debriefing.air_losses = AirLosses(
        player=[cast(Any, SimpleNamespace(flight=uzi, pilot=moroz))], enemy=[]
    )
    debriefing.ground_losses = GroundLosses()
    debriefing.ejected_pilot_positions = {id(moroz): cast(Any, object())}
    debriefing.pilot_kills = [
        _kill(kovalenko, viper, KillCategory.Air),
        _kill(kovalenko, viper, KillCategory.Ground),
        _kill(kovalenko, viper, KillCategory.Ground),
        _kill(wingman, uzi, KillCategory.Air),
    ]
    debriefing.rescued_pilots = {
        cast(Any, 1): RescuedPilot(
            "Maj. Bondar", "Su-25T", "Rooks", Player.BLUE, pilot=bondar
        ),
    }
    pilots = {"moroz": moroz, "kovalenko": kovalenko, "bondar": bondar}
    return debriefing, {**parts, **pilots}


def _card(cards: list[SortieCard], pilot: Pilot) -> SortieCard:
    [card] = [c for c in cards if c.pilot_id == str(pilot.id)]
    return card


def test_before_the_results_are_applied_a_card_shows_the_mission_data() -> None:
    debriefing, parts = _mission()

    report = build_report(debriefing)

    cards = report.your_sorties
    assert [c.pilot for c in cards] == ["Lt. Moroz", "Capt. Kovalenko", "Maj. Bondar"]
    strike, dead = report.packages
    moroz = _card(cards, parts["moroz"])
    assert (moroz.aircraft, moroz.flight, moroz.squadron) == (
        "F/A-18C",
        "Uzi 1",
        "VF-11",
    )
    assert (moroz.task, moroz.target) == ("Strike", strike.target)
    assert (moroz.package_result, moroz.package_tone) == (strike.result, strike.tone)
    assert (moroz.fate, moroz.fate_tone) == ("Ejected", Tone.MIXED)
    assert moroz.flight_time == "1:05"
    kovalenko = _card(cards, parts["kovalenko"])
    assert (kovalenko.task, kovalenko.target) == ("DEAD", dead.target)
    assert (kovalenko.air_kills, kovalenko.ground_kills, kovalenko.naval_kills) == (
        1,
        2,
        0,
    )
    assert (kovalenko.fate, kovalenko.fate_tone) == ("Returned", Tone.GOOD)
    bondar = _card(cards, parts["bondar"])
    assert (bondar.flight, bondar.fate, bondar.fate_tone) == (
        "",
        "Rescued by CSAR",
        Tone.GOOD,
    )
    # Decided when the results are applied.
    assert all(c.awards is None and c.sorties_logged is None for c in cards)


def test_once_applied_a_card_shows_what_the_logbook_committed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import game.income

    monkeypatch.setattr(
        game.income, "Income", lambda game, player: SimpleNamespace(total=0.0)
    )
    debriefing, parts = _mission()
    report = build_report(debriefing)
    moroz, kovalenko = parts["moroz"], parts["kovalenko"]
    moroz.status = PilotStatus.Downed
    moroz.record.logbook = [_entry(4, ejected=True)]
    moroz.record.awards = [
        _award(AwardKind.Rank, "Second Lieutenant", 2),
        _award(AwardKind.Rank, "First Lieutenant", 4),
    ]
    kovalenko.record.logbook = [
        _entry(3),
        _entry(4, air_kills=1, ground_kills=2, rescues=1, aircraft="F-16CM"),
    ]
    kovalenko.record.awards = [
        _award(AwardKind.Decoration, "Ace", 4, "Five aerial victories.")
    ]
    parts["bondar"].status = PilotStatus.Recovering

    final = complete_report(report, debriefing, [], rules=RULES)

    cards = final.your_sorties
    first = _card(cards, moroz)
    assert (first.fate, first.fate_tone) == ("Ejected, awaiting rescue", Tone.MIXED)
    assert first.sorties_logged == 1
    assert first.awards == [
        SortieAward("Rank", "First Lieutenant", "1st Lt", ""),
    ]
    second = _card(cards, kovalenko)
    assert (second.air_kills, second.ground_kills, second.rescues) == (1, 2, 1)
    assert second.awards == [
        SortieAward("Decoration", "Ace", "", "Five aerial victories."),
    ]
    third = _card(cards, parts["bondar"])
    assert (third.fate, third.awards, third.sorties_logged) == (
        "Rescued by CSAR",
        [],
        0,
    )


def test_a_pilot_killed_with_their_aircraft_shows_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import game.income

    monkeypatch.setattr(
        game.income, "Income", lambda game, player: SimpleNamespace(total=0.0)
    )
    debriefing, parts = _mission()
    debriefing.ejected_pilot_positions = {}
    report = build_report(debriefing)
    moroz = parts["moroz"]
    assert (_card(report.your_sorties, moroz).fate) == "Shot down"

    moroz.status = PilotStatus.Dead
    moroz.record.logbook = [_entry(4, died=True)]
    final = complete_report(report, debriefing, [], rules=RULES)

    card = _card(final.your_sorties, moroz)
    assert (card.fate, card.fate_tone) == ("Killed in action", Tone.BAD)


def test_a_mission_without_player_pilot_has_no_card() -> None:
    debriefing, _ = _debriefing()
    debriefing.ejected_pilot_positions = {}

    assert build_report(debriefing).your_sorties == []

"""PER-03.3: data-driven ranks and decorations."""

import datetime
import pickle
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest

from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.squadrons import AirWing, Pilot
from game.squadrons import awards
from game.squadrons.awards import AwardRules, award_careers, load_rules, rules_for
from game.squadrons.pilot import AwardKind, KillCategory, PilotRecord

TEST_RULES = Path(__file__).parent / "resources" / "careers"
MISSION_START = datetime.datetime(2000, 6, 1, 8, 30)


@pytest.fixture
def rules() -> list[AwardRules]:
    return load_rules([TEST_RULES])


def _usa(rules: list[AwardRules]) -> AwardRules:
    found = rules_for(rules, "USA", MISSION_START.date())
    assert found is not None
    return found


def _record(sorties: int = 0, air_kills: int = 0, hours: float = 0) -> PilotRecord:
    record = PilotRecord(missions_flown=sorties, air_kills=air_kills)
    record.flight_time = datetime.timedelta(hours=hours)
    return record


def _air_wing(country: str, *pilots: Pilot) -> AirWing:
    squadron = SimpleNamespace(
        current_roster=list(pilots), country=SimpleNamespace(name=country)
    )
    return cast(AirWing, SimpleNamespace(iter_squadrons=lambda: iter([squadron])))


def test_rules_are_chosen_by_country_then_period(rules: list[AwardRules]) -> None:
    assert _usa(rules).name == "Test Air Force"
    france = rules_for(rules, "France", MISSION_START.date())
    assert france is not None and france.name == "Any Air Force"
    before_period = rules_for(rules, "USA", datetime.date(1944, 6, 6))
    assert before_period is not None and before_period.name == "Any Air Force"
    assert rules_for([], "USA", MISSION_START.date()) is None


def test_fifth_air_kill_awards_the_ace_decoration(rules: list[AwardRules]) -> None:
    usa = _usa(rules)
    record = _record(air_kills=4)

    usa.evaluate(record, 3, MISSION_START)
    assert not record.has_award(AwardKind.Decoration, "Ace")

    record.credit_kill(KillCategory.Air)
    granted = usa.evaluate(record, 4, MISSION_START)

    assert [a.name for a in granted] == ["Ace"]
    ace = record.decorations[0]
    assert (ace.name, ace.turn, ace.date) == ("Ace", 4, MISSION_START)
    assert ace.description == "Five aerial victories."
    assert usa.evaluate(record, 5, MISSION_START) == []
    assert [a.name for a in record.decorations] == ["Ace"]


def test_ranks_are_granted_in_order_and_the_latest_is_held(
    rules: list[AwardRules],
) -> None:
    usa = _usa(rules)
    record = _record()

    usa.evaluate(record, 1, MISSION_START)
    assert record.rank is not None and record.rank.name == "Second Lieutenant"

    # Captain needs both 3 sorties and 4 flight hours.
    record.missions_flown = 3
    record.flight_time = datetime.timedelta(hours=3)
    usa.evaluate(record, 2, MISSION_START)
    assert record.rank is not None and record.rank.name == "First Lieutenant"

    record.flight_time = datetime.timedelta(hours=4)
    usa.evaluate(record, 3, MISSION_START)
    assert record.rank is not None and record.rank.name == "Captain"
    ranks = [a.name for a in record.awards if a.kind is AwardKind.Rank]
    assert ranks == ["Second Lieutenant", "First Lieutenant", "Captain"]


def test_unknown_logbook_value_is_rejected() -> None:
    data = {"name": "Bad", "decorations": [{"name": "X", "requires": {"kils": 5}}]}

    with pytest.raises(ValueError, match="kils"):
        AwardRules.from_data(data, "bad.yaml")


def test_invalid_file_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text("ranks: [{abbreviation: X}]\n")
    (tmp_path / "good.yaml").write_text("name: Good\n")

    assert [r.name for r in load_rules([tmp_path, tmp_path / "missing"])] == ["Good"]


def test_awards_are_evaluated_after_each_mission(
    rules: list[AwardRules], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(awards, "default_rules", lambda: tuple(rules))
    player = Pilot("Maverick", player=True)
    player.record.air_kills = 5
    ai = Pilot("Goose")
    ai.record.air_kills = 5
    game = MagicMock()
    game.turn = 7
    game.conditions.start_time = MISSION_START
    game.blue.air_wing = _air_wing("USA", player, ai)
    game.red.air_wing = _air_wing("Russia")

    MissionResultsProcessor(game).commit_pilot_awards()

    assert [a.name for a in player.record.awards] == ["Second Lieutenant", "Ace"]
    assert ai.record.awards == []
    assert game.message.call_count == 2


def test_award_careers_reports_who_got_what(rules: list[AwardRules]) -> None:
    player = Pilot("Maverick", player=True)

    granted = award_careers(_air_wing("France", player), 1, MISSION_START, rules)

    assert [(name, a.name) for name, a in granted] == [("Maverick", "Pilot")]


def test_awards_survive_save_and_reload(rules: list[AwardRules]) -> None:
    record = _record(sorties=3, air_kills=5, hours=6)
    _usa(rules).evaluate(record, 1, MISSION_START)

    loaded = pickle.loads(pickle.dumps(record))

    assert loaded.awards == record.awards
    assert loaded.rank is not None and loaded.rank.name == "Captain"


def test_saves_without_awards_still_load() -> None:
    record = PilotRecord()
    state = dict(record.__dict__)
    del state["awards"]
    loaded = PilotRecord.__new__(PilotRecord)

    loaded.__setstate__(state)

    assert loaded.awards == [] and loaded.rank is None


def test_shipped_rules_load_and_cover_every_country() -> None:
    shipped = load_rules([Path("resources/careers")])

    assert shipped, "resources/careers must ship rules"
    for rules in shipped:
        assert rules.ranks, f"{rules.name} has no ranks"
    assert rules_for(shipped, "Atlantis", MISSION_START.date()) is not None
    usa = rules_for(shipped, "USA", MISSION_START.date())
    assert usa is not None and usa.countries == {"USA"}

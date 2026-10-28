"""CSAR-01.11: an optional bounty is paid for each successful rescue."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from dcs.mapping import Point
from dcs.terrain import Terrain

from game import persistency
from game.coalition import Coalition
from game.debriefing import Debriefing
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.squadrons.downedpilot import DownedPilot
from game.squadrons.pilot import Pilot
from game.theater.player import Player

_TERRAIN = MagicMock(spec=Terrain)


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16885)


class _Coalition:
    """Just the budget of a coalition, credited the way Coalition does it."""

    def __init__(self, budget: float) -> None:
        self.budget = budget
        self.downed_pilots: list[DownedPilot] = []

    adjust_budget = Coalition.adjust_budget


def _downed(budget: float) -> DownedPilot:
    squadron = MagicMock()
    coalition = _Coalition(budget)
    squadron.coalition = coalition
    downed = DownedPilot(
        pilot=Pilot("Rescuee"),
        squadron=squadron,
        _position=Point(0.0, 0.0, _TERRAIN),
        player=Player.BLUE,
        turn_downed=1,
        turns_remaining=3,
        was_player=False,
        aircraft_name="F/A-18C Hornet",
    )
    coalition.downed_pilots.append(downed)
    return downed


def _rescue(bounty: int) -> Any:
    downed = _downed(budget=500.0)
    game = MagicMock()
    game.settings = SimpleNamespace(
        csar_rescue_bounty=bounty,
        csar_ai_recovery_turns=2,
        csar_player_recovery_turns=1,
    )
    game.coalitions = []
    game.db.downed_pilots.get.return_value = downed
    debriefing = MagicMock()
    debriefing.state_data.rescued_pilot_ids = [str(downed.id)]
    MissionResultsProcessor(game).commit_csar_results(debriefing)
    assert downed.pilot.recovering
    return downed.squadron.coalition


def test_rescue_with_a_bounty_credits_the_rescuing_side() -> None:
    assert _rescue(bounty=25).budget == 525.0


def test_rescue_without_a_bounty_leaves_the_budget_unchanged() -> None:
    assert _rescue(bounty=0).budget == 500.0


def test_bounty_is_off_by_default() -> None:
    from game.settings import Settings

    assert Settings().csar_rescue_bounty == 0


def test_debriefing_reports_the_bounty_per_side() -> None:
    debriefing = Debriefing.__new__(Debriefing)
    debriefing.game = MagicMock()
    debriefing.game.settings = SimpleNamespace(csar_rescue_bounty=10)
    debriefing.rescued_pilots = {}
    debriefing.record_rescue(_downed(budget=0.0))
    debriefing.record_rescue(_downed(budget=0.0))

    assert debriefing.rescue_bounty_for(Player.BLUE) == 20
    assert debriefing.rescue_bounty_for(Player.RED) == 0

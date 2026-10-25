"""PER-03.1: kills reported by S_EVENT_KILL are credited to the shooter's pilot."""

import pickle
from typing import Any, cast
from unittest.mock import MagicMock

from game.debriefing import Debriefing, KillAttribution, StateData
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.squadrons import Pilot
from game.squadrons.pilot import KillCategory, PilotRecord
from game.theater import Player
from game.unitmap import FlyingUnit, FrontLineUnit, TheaterUnitMapping, UnitMap


def _flight(side: Player) -> Any:
    flight = MagicMock()
    flight.squadron.player = side
    flight.departure.captured.is_blue = side.is_blue
    return flight


def _kill(initiator: str, target: str) -> dict[str, str]:
    return {"initiator": initiator, "target": target}


def _state(*kills: dict[str, str]) -> dict[str, Any]:
    return {
        "mission_ended": True,
        "kill_events": [kill["target"] for kill in kills],
        "kill_attributions": list(kills),
    }


class Scenario:
    """A blue two-ship against a red two-ship, plus ground units and a ship."""

    def __init__(self) -> None:
        self.unit_map = UnitMap()
        self.lead = Pilot("Lead")
        self.wingman = Pilot("Wingman")
        self.bandit = Pilot("Bandit")
        blue = _flight(Player.BLUE)
        red = _flight(Player.RED)
        self.unit_map.aircraft["Blue 1-1"] = FlyingUnit(blue, self.lead)
        self.unit_map.aircraft["Blue 1-2"] = FlyingUnit(blue, self.wingman)
        self.unit_map.aircraft["Red 1-1"] = FlyingUnit(red, self.bandit)
        self.unit_map.aircraft["Red 1-2"] = FlyingUnit(red, Pilot("Bandit 2"))

        red_cp = MagicMock()
        red_cp.captured = Player.RED
        self.unit_map.front_line_units["T-72 #1"] = FrontLineUnit(MagicMock(), red_cp)
        blue_cp = MagicMock()
        blue_cp.captured = Player.BLUE
        self.unit_map.front_line_units["M1 #1"] = FrontLineUnit(MagicMock(), blue_cp)

        ship = MagicMock()
        ship.is_ship = True
        ship.ground_object.is_friendly = lambda to_player: to_player is Player.RED
        self.unit_map.theater_objects["Frigate"] = TheaterUnitMapping(ship, MagicMock())

    def debrief(self, *kills: dict[str, str]) -> Debriefing:
        return Debriefing(_state(*kills), MagicMock(), self.unit_map)


def test_two_air_kills_by_flight_member_1_are_credited_to_that_pilot() -> None:
    scenario = Scenario()
    debriefing = scenario.debrief(
        _kill("Blue 1-1", "Red 1-1"), _kill("Blue 1-1", "Red 1-2")
    )

    MissionResultsProcessor.commit_pilot_kills(debriefing)

    assert scenario.lead.record.air_kills == 2
    assert scenario.lead.record.ground_kills == 0
    assert scenario.lead.record.naval_kills == 0
    assert scenario.wingman.record == PilotRecord()


def test_kills_are_categorised_air_ground_naval() -> None:
    scenario = Scenario()
    debriefing = scenario.debrief(
        _kill("Blue 1-2", "Red 1-1"),
        _kill("Blue 1-2", "T-72 #1"),
        _kill("Blue 1-2", "Frigate"),
    )

    assert [kill.category for kill in debriefing.pilot_kills] == [
        KillCategory.Air,
        KillCategory.Ground,
        KillCategory.Naval,
    ]
    assert all(kill.pilot is scenario.wingman for kill in debriefing.pilot_kills)


def test_enemy_pilots_are_credited_too() -> None:
    scenario = Scenario()
    debriefing = scenario.debrief(_kill("Red 1-1", "Blue 1-2"))

    MissionResultsProcessor.commit_pilot_kills(debriefing)

    assert scenario.bandit.record.air_kills == 1


def test_friendly_untracked_and_non_aircraft_kills_are_not_credited() -> None:
    scenario = Scenario()
    debriefing = scenario.debrief(
        _kill("Blue 1-1", "Blue 1-2"),  # fratricide
        _kill("Blue 1-1", "M1 #1"),  # friendly ground unit
        _kill("Blue 1-1", "Infantry #12"),  # untracked target
        _kill("SAM site", "Red 1-1"),  # shooter is not a flight member
    )

    assert debriefing.pilot_kills == []


def test_a_target_is_credited_only_once() -> None:
    scenario = Scenario()
    debriefing = scenario.debrief(
        _kill("Blue 1-1", "Red 1-1"), _kill("Blue 1-2", "Red 1-1")
    )

    assert [kill.pilot for kill in debriefing.pilot_kills] == [scenario.lead]


def test_state_without_kill_attributions_still_parses() -> None:
    """state.json from a mission generated before PER-03.1, and an empty Lua
    table that json.lua may encode as an object."""
    unit_map = UnitMap()
    assert StateData.from_json({}, unit_map).kill_attributions == []
    assert (
        StateData.from_json({"kill_attributions": {}}, unit_map).kill_attributions == []
    )


def test_numeric_map_object_names_are_normalised() -> None:
    assert KillAttribution.from_json(
        {"initiator": "Blue 1-1", "target": 1234}
    ) == KillAttribution("Blue 1-1", "1234")
    assert KillAttribution.from_json({"target": "x"}) is None


def test_pilot_record_from_an_old_save_loads_with_zero_kills() -> None:
    old = PilotRecord.__new__(PilotRecord)
    old.__dict__.update({"missions_flown": 7})  # the only field before PER-03.1

    loaded = cast(PilotRecord, pickle.loads(pickle.dumps(old)))

    assert loaded == PilotRecord(missions_flown=7)
    loaded.credit_kill(KillCategory.Ground)
    assert loaded.kills(KillCategory.Ground) == 1


def test_kills_survive_save_and_reload() -> None:
    pilot = Pilot("Maverick")
    pilot.record.credit_kill(KillCategory.Air)
    pilot.record.credit_kill(KillCategory.Naval)

    loaded = cast(Pilot, pickle.loads(pickle.dumps(pilot)))

    assert loaded.record.air_kills == 1
    assert loaded.record.naval_kills == 1

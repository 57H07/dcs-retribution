"""PER-03.2: player pilot logbook and career data model."""

import pickle
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from game.ato.flighttype import FlightType
from game.debriefing import Debriefing
from game.settings import Settings
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.squadrons import AirWing, Pilot, Squadron
from game.squadrons.career import careers, player_career
from game.squadrons.pilot import KillCategory, LogbookEntry, PilotRecord
from game.theater import Player
from game.unitmap import FlyingUnit, UnitMap

MISSION_START = datetime(2026, 6, 1, 8, 30)
TAKEOFF = datetime(2026, 6, 1, 9, 0)


def _flight(
    side: Player,
    pilots: list[Pilot],
    task: FlightType = FlightType.TARCAP,
    duration: timedelta = timedelta(hours=1, minutes=30),
) -> Any:
    flight = MagicMock()
    flight.squadron.player = side
    flight.squadron.name = f"{side.name} squadron"
    flight.unit_type = "F-16CM"
    flight.flight_type = task
    flight.roster.iter_pilots = lambda: iter(pilots)
    flight.flight_plan.takeoff_time = lambda: TAKEOFF
    flight.flight_plan.landing_time = TAKEOFF + duration
    return flight


class Mission:
    """A blue flight led by the player against a red two-ship."""

    def __init__(self, task: FlightType = FlightType.TARCAP) -> None:
        self.player = Pilot("Maverick", player=True)
        self.wingman = Pilot("Goose")
        self.bandit = Pilot("Bandit")
        self.blue = _flight(Player.BLUE, [self.player, self.wingman], task)
        self.red = _flight(Player.RED, [self.bandit, Pilot("Bandit 2")])

        self.unit_map = UnitMap()
        self.unit_map.aircraft["Blue 1-1"] = FlyingUnit(self.blue, self.player)
        self.unit_map.aircraft["Blue 1-2"] = FlyingUnit(self.blue, self.wingman)
        self.unit_map.aircraft["Red 1-1"] = FlyingUnit(self.red, self.bandit)
        self.unit_map.aircraft["Red 1-2"] = FlyingUnit(self.red, Pilot("Bandit 2"))

        self.game = MagicMock()
        self.game.turn = 3
        self.game.conditions.start_time = MISSION_START
        self.game.blue.ato.packages = [SimpleNamespace(flights=[self.blue])]
        self.game.red.ato.packages = [SimpleNamespace(flights=[self.red])]

    def fly(self, *kills: tuple[str, str]) -> Debriefing:
        state = {
            "mission_ended": True,
            "kill_events": [target for _, target in kills],
            "kill_attributions": [
                {"initiator": initiator, "target": target}
                for initiator, target in kills
            ],
        }
        debriefing = Debriefing(state, self.game, self.unit_map)
        processor = MissionResultsProcessor(self.game)
        processor.commit_pilot_kills(debriefing)
        processor.commit_pilot_logbooks(debriefing)
        return debriefing


def test_mission_adds_one_sortie_and_its_kills_to_the_player_logbook() -> None:
    mission = Mission()

    mission.fly(("Blue 1-1", "Red 1-1"), ("Blue 1-1", "Red 1-2"))

    record = mission.player.record
    assert record.sorties == 1
    assert record.combat_sorties == 1
    assert record.air_kills == 2
    assert record.flight_time == timedelta(hours=1, minutes=30)
    assert record.logbook == [
        LogbookEntry(
            turn=3,
            date=MISSION_START,
            squadron="BLUE squadron",
            aircraft="F-16CM",
            task=FlightType.TARCAP,
            combat=True,
            flight_time=timedelta(hours=1, minutes=30),
            air_kills=2,
        )
    ]


def test_ai_pilots_keep_totals_but_no_history() -> None:
    mission = Mission()

    mission.fly(("Blue 1-2", "Red 1-1"))

    assert mission.wingman.record.sorties == 1
    assert mission.wingman.record.air_kills == 1
    assert mission.wingman.record.logbook == []
    assert mission.bandit.record.sorties == 1


def test_history_grows_one_entry_per_mission() -> None:
    mission = Mission()

    mission.fly(("Blue 1-1", "Red 1-1"))
    mission.game.turn = 4
    mission.fly()

    record = mission.player.record
    assert record.sorties == 2
    assert [entry.turn for entry in record.logbook] == [3, 4]
    assert [entry.air_kills for entry in record.logbook] == [1, 0]
    assert record.air_kills == sum(e.air_kills for e in record.logbook)
    assert record.flight_time == timedelta(hours=3)


def test_non_combat_sortie_becomes_combat_when_the_pilot_scores() -> None:
    quiet = Mission(FlightType.TRANSPORT)
    quiet.fly()
    assert quiet.player.record.combat_sorties == 0
    assert not quiet.player.record.logbook[0].combat

    lucky = Mission(FlightType.TRANSPORT)
    lucky.fly(("Blue 1-1", "Red 1-1"))
    assert lucky.player.record.combat_sorties == 1


def test_lost_aircraft_logs_a_death() -> None:
    mission = Mission()

    mission.fly(("Red 1-1", "Blue 1-1"))

    assert mission.player.record.deaths == 1
    assert mission.player.record.logbook[0].died
    assert mission.wingman.record.deaths == 0


def test_unknown_flight_time_counts_as_zero() -> None:
    mission = Mission()
    mission.blue.flight_plan.takeoff_time = MagicMock(side_effect=NotImplementedError)

    mission.fly()

    assert mission.player.record.flight_time == timedelta()
    assert mission.player.record.sorties == 1


def test_logbook_survives_save_and_reload() -> None:
    mission = Mission()
    mission.fly(("Blue 1-1", "Red 1-1"))

    loaded = cast(Pilot, pickle.loads(pickle.dumps(mission.player)))

    assert loaded.record == mission.player.record
    assert loaded.record.logbook[0].kills(KillCategory.Air) == 1


def test_record_from_an_old_save_loads_with_an_empty_logbook() -> None:
    old = PilotRecord.__new__(PilotRecord)
    old.__dict__.update({"missions_flown": 7, "air_kills": 2})

    loaded = cast(PilotRecord, pickle.loads(pickle.dumps(old)))

    assert loaded == PilotRecord(missions_flown=7, air_kills=2)
    assert loaded.sorties == 7
    assert loaded.flight_time == timedelta()
    assert loaded.logbook == []


def _squadron(name: str, roster: list[Pilot], pilot_limit: int = 12) -> Squadron:
    squadron = Squadron.__new__(Squadron)
    squadron.name = name
    squadron.nickname = None
    squadron.current_roster = roster
    squadron.available_pilots = list(roster)
    settings = Settings()
    settings.enable_squadron_pilot_limits = True
    settings.squadron_pilot_limit = pilot_limit
    squadron.settings = settings
    return squadron


def _air_wing(*squadrons: Squadron) -> AirWing:
    return cast(AirWing, SimpleNamespace(iter_squadrons=lambda: iter(squadrons)))


def test_every_player_pilot_has_a_career_and_a_living_one_is_exposed() -> None:
    fallen = Pilot("Fallen", player=True)
    fallen.kill()
    first = _squadron("VF-1", [Pilot("AI"), fallen])
    alive = Pilot("Alive", player=True)
    second = _squadron("VF-2", [alive, Pilot("Iceman", player=True)])

    found = careers(_air_wing(first, second))

    assert [c.pilot.name for c in found] == ["Alive", "Iceman", "Fallen"]
    assert found[0].squadron is second
    assert found[0].logbook is alive.record
    exposed = player_career(_air_wing(first, second))
    assert exposed is not None and exposed.pilot is alive
    assert player_career(_air_wing(_squadron("VF-3", [Pilot("AI")]))) is None


def test_player_can_create_their_pilot() -> None:
    squadron = _squadron("VF-1", [Pilot("AI")])

    pilot = squadron.create_player_pilot("Maverick")

    assert pilot.player
    assert pilot in squadron.current_roster
    assert pilot in squadron.available_pilots
    assert player_career(_air_wing(squadron)) is not None


def test_cannot_create_a_pilot_in_a_full_squadron() -> None:
    squadron = _squadron("VF-1", [Pilot("AI")], pilot_limit=1)

    with pytest.raises(RuntimeError):
        squadron.create_player_pilot("Maverick")

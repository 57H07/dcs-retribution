"""PER-03.5: ejections and rescues counted in the career."""

import pickle
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

from dcs.mapping import Point
from dcs.terrain import Terrain

from game.ato.flighttype import FlightType
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.squadrons.awards import AwardRules
from game.squadrons.csarservice import CsarService
from game.squadrons.downedpilot import DownedPilot
from game.squadrons.pilot import AwardKind, LogbookEntry, Pilot, PilotRecord
from game.theater import Player

_TERRAIN = cast(Terrain, MagicMock())
TAKEOFF = datetime(2026, 6, 1, 9, 0)


def _game(**settings: Any) -> Any:
    defaults = dict(
        invulnerable_player_pilots=False,
        csar_enabled=True,
        csar_enabled_red=True,
        csar_ejection_chance=0,
        csar_control_point_radius=0,
        csar_safe_zone_recovery=False,
        csar_rescue_bounty=0,
        csar_capture_radius=30,
        csar_survival_turns=3,
        csar_survival_turns_hostile=2,
        csar_ai_recovery_turns=2,
        csar_player_recovery_turns=1,
        csar_prisoners_of_war=False,
        csar_rescue_ai_pilots=True,
        csar_cluster_radius=0,
    )
    defaults.update(settings)
    game = MagicMock()
    game.settings = SimpleNamespace(**defaults)
    game.turn = 3
    game.conditions.start_time = TAKEOFF
    game.theater.closest_control_point.return_value.is_friendly.return_value = True
    game.theater.conflicts.return_value = []
    game.theater.is_in_sea.return_value = False
    game.blue.ato.packages = []
    game.red.ato.packages = []
    game.coalitions = [game.blue, game.red]
    return game


def _flight(pilots: list[Any], task: FlightType = FlightType.TARCAP) -> Any:
    flight = MagicMock()
    flight.squadron.player = Player.BLUE
    flight.squadron.name = "VF-1"
    flight.squadron.coalition.downed_pilots = []
    flight.unit_type = "F-16CM"
    flight.flight_type = task
    flight.client_count = 0
    flight.returned_to_squadron = False
    flight.roster.iter_pilots = lambda: iter(pilots)
    flight.flight_plan.takeoff_time = lambda: TAKEOFF
    flight.flight_plan.landing_time = TAKEOFF + timedelta(hours=1)
    return flight


def _fly(game: Any, *flights: Any, lost: Any = None, ejected: bool = True) -> Any:
    """Commits a mission flown by the flights, losing ``lost``'s aircraft."""
    game.blue.ato.packages = [SimpleNamespace(flights=list(flights))]
    debriefing = MagicMock()
    debriefing.pilot_kills = []
    debriefing.air_losses.losses = []
    debriefing.ejected_pilot_positions = {}
    processor = MissionResultsProcessor(game)
    if lost is not None:
        pilot, flight = lost
        loss = SimpleNamespace(pilot=pilot, flight=flight)
        debriefing.air_losses.losses = [loss]
        if ejected:
            debriefing.ejected_pilot_positions = {id(pilot): Point(1, 2, _TERRAIN)}
        with patch(
            "game.squadrons.csarservice.find_downed_pilot_position",
            return_value=Point(1, 2, _TERRAIN),
        ):
            processor._process_lost_pilot(loss, debriefing, CsarService(game))
    processor.commit_pilot_logbooks(debriefing)
    return debriefing


def _rescue(game: Any, downed: DownedPilot, rescuers: list[Pilot]) -> Any:
    """Flies a player CSAR flight that Ops.CSAR reports picked up ``downed``."""
    csar = _flight(list(rescuers), FlightType.CSAR)
    csar.client_count = 1
    csar.package.target = downed
    game.blue.ato.packages = [SimpleNamespace(flights=[csar])]
    game.db.downed_pilots.get.return_value = downed
    debriefing = MagicMock()
    debriefing.state_data.rescued_pilot_ids = [str(downed.id)]
    debriefing.unit_map.aircraft.values.return_value = []
    debriefing.pilot_kills = []
    debriefing.air_losses.losses = []
    processor = MissionResultsProcessor(game)
    processor.commit_csar_results(debriefing)
    processor.commit_pilot_logbooks(debriefing)
    return csar


def test_ejection_then_rescue_adds_one_of_each_to_the_ejected_pilot() -> None:
    game = _game()
    maverick = Pilot("Maverick", player=True)
    flight = _flight([maverick])

    _fly(game, flight, lost=(maverick, flight))

    record = maverick.record
    assert maverick.downed
    assert record.ejections == 1
    assert record.shot_down == 1
    assert record.deaths == 0
    assert record.logbook[0].ejected
    assert not record.logbook[0].died

    downed = flight.squadron.coalition.downed_pilots[0]
    game.turn = 4
    _rescue(game, downed, [Pilot("Rescuer")])

    assert maverick.recovering
    assert record.ejections == 1
    assert record.times_rescued == 1
    # Not flying the rescue sortie, so no sortie for the rescued pilot.
    assert record.sorties == 1


def test_rescuing_crew_get_a_rescue_counter() -> None:
    game = _game()
    downed_pilot = Pilot("Downed")
    flight = _flight([downed_pilot])
    _fly(game, flight, lost=(downed_pilot, flight))
    downed = flight.squadron.coalition.downed_pilots[0]

    pilot, copilot = Pilot("Jolly", player=True), Pilot("Jolly 2")
    _rescue(game, downed, [pilot, copilot])

    assert pilot.record.pilots_rescued == 1
    assert copilot.record.pilots_rescued == 1
    assert pilot.record.logbook[-1].rescues == 1
    assert pilot.record.times_rescued == 0
    assert downed_pilot.record.pilots_rescued == 0


def test_csar_flight_sent_after_someone_else_gets_no_credit() -> None:
    game = _game()
    first, second = Pilot("First"), Pilot("Second")
    flight = _flight([first, second])
    _fly(game, flight, lost=(first, flight))
    _fly(game, flight, lost=(second, flight))
    rescued, other = flight.squadron.coalition.downed_pilots

    busy = _flight([Pilot("Busy")], FlightType.CSAR)
    busy.client_count = 1
    busy.package.target = other
    rescuer = Pilot("Rescuer")
    csar = _rescue(game, rescued, [rescuer])
    game.blue.ato.packages = [SimpleNamespace(flights=[csar, busy])]
    processor = MissionResultsProcessor(game)
    processor._credit_rescuers({rescued}, set(), MagicMock())

    assert processor.pilot_rescues[id(rescuer)] == 1
    assert id(next(busy.roster.iter_pilots())) not in processor.pilot_rescues


def test_loss_without_ejection_is_a_death_not_an_ejection() -> None:
    game = _game()
    pilot = Pilot("Goose", player=True)
    flight = _flight([pilot])

    _fly(game, flight, lost=(pilot, flight), ejected=False)

    assert pilot.record.deaths == 1
    assert pilot.record.shot_down == 1
    assert pilot.record.ejections == 0
    assert pilot.record.logbook[0].died
    assert not pilot.record.logbook[0].ejected


def test_ejection_with_csar_off_is_an_ejection_and_a_death() -> None:
    game = _game(csar_enabled=False)
    pilot = Pilot("Goose", player=True)
    flight = _flight([pilot])

    _fly(game, flight, lost=(pilot, flight))

    entry = pilot.record.logbook[0]
    assert entry.ejected and entry.died
    assert pilot.record.ejections == 1
    assert pilot.record.deaths == 1
    assert pilot.record.shot_down == 1


def test_invulnerable_player_who_ejects_did_not_die() -> None:
    game = _game(invulnerable_player_pilots=True)
    pilot = Pilot("Maverick", player=True)
    flight = _flight([pilot])

    _fly(game, flight, lost=(pilot, flight))

    assert pilot.record.ejections == 1
    assert pilot.record.deaths == 0


def test_simulated_loss_survived_counts_as_an_ejection() -> None:
    game = _game(csar_ejection_chance=100)
    pilot = Pilot("AI")
    flight = _flight([pilot])
    flight.package.target.position = Point(1, 2, _TERRAIN)
    flight.arrival.position = Point(1000, 2, _TERRAIN)

    _fly(game, flight, lost=(pilot, flight), ejected=False)

    assert pilot.downed
    assert pilot.record.ejections == 1
    assert pilot.record.deaths == 0


def test_pilot_never_rescued_dies_when_the_countdown_ends() -> None:
    game = _game()
    pilot = Pilot("AI")
    flight = _flight([pilot])
    _fly(game, flight, lost=(pilot, flight))
    downed = flight.squadron.coalition.downed_pilots[0]

    CsarService(game).expire(downed)

    assert pilot.record.ejections == 1
    assert pilot.record.deaths == 1
    assert pilot.record.shot_down == 1


def test_rescue_counters_can_be_award_conditions() -> None:
    rules = AwardRules.from_data(
        {
            "name": "Test",
            "decorations": [
                {"name": "Survivor", "requires": {"times_rescued": 1}},
                {"name": "Rescue Medal", "requires": {"pilots_rescued": 2}},
                {"name": "Caterpillar", "requires": {"ejections": 1}},
                {"name": "Wound Badge", "requires": {"shot_down": 1}},
            ],
        },
        "test",
    )
    record = PilotRecord(ejections=1, shot_down=1, times_rescued=1, pilots_rescued=1)

    granted = rules.evaluate(record, 1, TAKEOFF)

    assert [a.name for a in granted] == ["Survivor", "Caterpillar", "Wound Badge"]
    assert not record.has_award(AwardKind.Decoration, "Rescue Medal")


def test_counters_survive_save_and_reload() -> None:
    record = PilotRecord(ejections=2, shot_down=3, times_rescued=1, pilots_rescued=4)
    record.logbook.append(
        LogbookEntry(
            turn=1,
            date=TAKEOFF,
            squadron="VF-1",
            aircraft="F-16CM",
            task=FlightType.CSAR,
            combat=False,
            flight_time=timedelta(hours=1),
            ejected=True,
            rescues=2,
        )
    )

    assert pickle.loads(pickle.dumps(record)) == record


def test_old_save_counts_its_deaths_as_shot_down() -> None:
    old = PilotRecord.__new__(PilotRecord)
    old.__dict__.update({"missions_flown": 7, "deaths": 2})

    loaded = cast(PilotRecord, pickle.loads(pickle.dumps(old)))

    assert loaded.shot_down == 2
    assert loaded.ejections == 0
    assert loaded.times_rescued == 0
    assert loaded.pilots_rescued == 0


def test_old_logbook_entry_loads_without_ejection() -> None:
    entry = LogbookEntry(
        turn=1,
        date=TAKEOFF,
        squadron="VF-1",
        aircraft="F-16CM",
        task=FlightType.TARCAP,
        combat=True,
        flight_time=timedelta(),
    )
    state = dict(entry.__dict__)
    del state["ejected"], state["rescues"]
    old = LogbookEntry.__new__(LogbookEntry)
    object.__setattr__(old, "__dict__", state)

    loaded = cast(LogbookEntry, pickle.loads(pickle.dumps(old)))

    assert not loaded.ejected
    assert loaded.rescues == 0

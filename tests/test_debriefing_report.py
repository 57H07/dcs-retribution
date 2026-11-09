"""WEB-05.2: the after-action report computed from a Debriefing."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from game import debriefingreport
from game.ato.flighttype import FlightType
from game.debriefing import (
    AirLosses,
    BaseCaptureEvent,
    Debriefing,
    GroundLosses,
    RescuedPilot,
    SideLossCounts,
)
from game.debriefingreport import (
    LossLine,
    ObjectiveLine,
    PilotLine,
    ReportEvent,
    Tone,
    build_report,
    complete_report,
    logged_events,
    verdict,
)
from game.infos.information import Information
from game.objectives import (
    CampaignObjective,
    CampaignObjectives,
    ObjectiveKind,
    ObjectiveState,
)
from game.squadrons.pilot import KillCategory
from game.theater import ControlPoint, Player
from game.theater.theatergroundobject import TheaterGroundObject


def _counts(
    aircraft: int = 0, ground: int = 0, bases_lost: int = 0, scenery: int = 0
) -> SideLossCounts:
    return SideLossCounts(aircraft, ground, 0, 0, 0, 0, 0, scenery, bases_lost, 0, 0)


@pytest.mark.parametrize(
    "friendly, enemy, title, tone",
    [
        (_counts(), _counts(), "No contact", Tone.NEUTRAL),
        (_counts(aircraft=1), _counts(aircraft=3), "Tactical victory", Tone.GOOD),
        (_counts(ground=4), _counts(scenery=1), "Tactical defeat", Tone.BAD),
        (_counts(aircraft=2), _counts(ground=2), "Stalemate", Tone.MIXED),
        # Bases decide before losses.
        (_counts(aircraft=5), _counts(bases_lost=1), "Tactical victory", Tone.GOOD),
        (_counts(bases_lost=1), _counts(aircraft=9), "Tactical defeat", Tone.BAD),
    ],
)
def test_verdict(
    friendly: SideLossCounts, enemy: SideLossCounts, title: str, tone: Tone
) -> None:
    assert verdict(friendly, enemy)[:2] == (title, tone)


def test_verdict_summary() -> None:
    summary = verdict(_counts(aircraft=1), _counts(ground=2, bases_lost=1))[2]
    assert summary == "Enemy lost 2 units, we lost 1 unit. 1 base captured."


# --- a Debriefing without the heavy __init__ -----------------------------------


class _Squadron:
    def __init__(self, name: str, player: Player) -> None:
        self.name = name
        self.player = player


class _Type:
    def __init__(self, name: str) -> None:
        self.display_name = name

    def __str__(self) -> str:
        return self.display_name


def _flight(
    squadron: _Squadron,
    unit_type: str,
    count: int,
    custom_name: str | None = None,
    pilots: tuple[Any, ...] = (),
    task: FlightType = FlightType.STRIKE,
    minutes: int = 0,
) -> Any:
    takeoff = datetime.datetime(2022, 5, 17, 6, 10)
    return SimpleNamespace(
        squadron=squadron,
        unit_type=_Type(unit_type),
        count=count,
        custom_name=custom_name,
        roster=SimpleNamespace(iter_pilots=lambda: iter(pilots)),
        flight_type=task,
        flight_plan=SimpleNamespace(
            takeoff_time=lambda: takeoff,
            landing_time=takeoff + datetime.timedelta(minutes=minutes),
        ),
    )


class _Tgo(TheaterGroundObject):
    """A ground object reduced to what the package results read."""

    def __init__(self, name: str, alive: int) -> None:  # no super().__init__
        self.name = name
        self._alive = alive

    @property
    def alive_unit_count(self) -> int:
        return self._alive

    def is_friendly(self, to_player: Player) -> bool:
        return False

    @property
    def symbol_set_and_entity(self) -> Any:
        raise NotImplementedError


def _tgo(name: str, alive: int) -> TheaterGroundObject:
    return _Tgo(name, alive)


def _package(task: str, target: Any, flights: list[Any]) -> Any:
    return SimpleNamespace(
        primary_task=SimpleNamespace(value=task), target=target, flights=flights
    )


def _debriefing() -> tuple[Debriefing, dict[str, Any]]:
    blue_sq = _Squadron("VF-11", Player.BLUE)
    red_sq = _Squadron("Red 1", Player.RED)
    viper = _flight(blue_sq, "F-16CM", 2, "Viper 1")
    hornet = _flight(blue_sq, "F/A-18C", 4)
    mig = _flight(red_sq, "MiG-29A", 2)
    sam = _tgo("SA-11 Krasnodar", alive=2)
    depot = _tgo("Ammo depot", alive=4)
    cp = cast(ControlPoint, SimpleNamespace(name="Krymsk"))
    pilot = SimpleNamespace(name="Lt. Moroz")

    air = AirLosses(
        player=[cast(Any, SimpleNamespace(flight=hornet, pilot=pilot))],
        enemy=[cast(Any, SimpleNamespace(flight=mig, pilot=None))] * 2,
    )
    sam_unit = SimpleNamespace(
        theater_unit=SimpleNamespace(ground_object=sam, type=SimpleNamespace(id="Kub"))
    )
    depot_unit = SimpleNamespace(
        theater_unit=SimpleNamespace(
            ground_object=depot, type=SimpleNamespace(id="Depot")
        )
    )
    ground = GroundLosses(
        enemy_ground_objects=[cast(Any, sam_unit)] * 2 + [cast(Any, depot_unit)],
    )
    game = SimpleNamespace(
        turn=4,
        conditions=SimpleNamespace(start_time=datetime.datetime(2022, 5, 17, 6, 0)),
        settings=SimpleNamespace(
            csar_rescue_bounty=10, persistent_damage_aircraft_write_off=False
        ),
        blue=SimpleNamespace(
            ato=SimpleNamespace(
                packages=[
                    _package("DEAD", sam, [viper]),
                    _package("Strike", depot, [hornet]),
                    _package("BARCAP", cp, [viper]),
                    _package("CAS", cp, []),
                ]
            ),
            downed_pilots=["one", "two"],
            budget=1420.456,
        ),
        pilots_captured_this_turn=[],
        objectives=CampaignObjectives(),
    )

    debriefing = Debriefing.__new__(Debriefing)
    debriefing.game = cast(Any, game)
    debriefing.player_country = "Ukraine"
    debriefing.enemy_country = "Russia"
    debriefing.air_losses = air
    debriefing.ground_losses = ground
    debriefing.base_captures = [BaseCaptureEvent(cp, Player.BLUE)]
    debriefing.rescued_pilots = {
        cast(Any, 1): RescuedPilot("Capt. Hrytsenko", "Su-25T", "Rooks", Player.BLUE),
        cast(Any, 2): RescuedPilot("Maj. Ivanov", "MiG-29A", "Red 1", Player.RED),
    }
    debriefing.pilot_kills = [
        cast(Any, SimpleNamespace(pilot=pilot, flight=viper, category=KillCategory.Air))
    ]
    debriefing.damaged_aircraft = []
    debriefing.damaged_ground_units = []
    return debriefing, {"game": game, "pilot": pilot}


def test_report_before_the_results_are_applied() -> None:
    debriefing, _ = _debriefing()
    report = build_report(debriefing)

    assert (report.turn, report.date) == (4, "17 May 2022")
    assert (report.verdict, report.verdict_tone) == ("Tactical victory", Tone.GOOD)
    assert (report.air_kills_friendly, report.air_kills_enemy) == (2, 1)
    assert (report.ground_kills_friendly, report.ground_kills_enemy) == (3, 0)
    assert (report.bases_captured, report.bases_lost) == (1, 0)
    assert report.pilots_rescued == [
        PilotLine("Capt. Hrytsenko", "Su-25T", "Rooks", None)
    ]
    assert report.rescue_bounty == 10
    assert report.friendly_losses == [LossLine("F/A-18C", 1)]
    assert report.enemy_losses == [
        LossLine("MiG-29A", 2),
        LossLine("Kub", 2),
        LossLine("Depot", 1),
    ]

    # Packages without flights are left out.
    assert [(p.task, p.target, p.flights) for p in report.packages] == [
        ("DEAD", "SA-11 Krasnodar", ["Viper 1"]),
        ("Strike", "Ammo depot", ["4x F/A-18C"]),
        ("BARCAP", "Krymsk", ["Viper 1"]),
    ]
    assert [(p.lost, p.aircraft, p.result, p.tone) for p in report.packages] == [
        (0, 2, "Target destroyed", Tone.GOOD),
        (1, 4, "Target 25%", Tone.MIXED),
        (0, 2, "No losses", Tone.GOOD),
    ]

    assert report.events == [
        ReportEvent(None, "Krymsk captured", Tone.GOOD),
        ReportEvent(None, "Lt. Moroz (Viper 1) scored an air kill", Tone.GOOD),
        ReportEvent(None, "F/A-18C of VF-11 lost · Lt. Moroz", Tone.BAD),
        ReportEvent(None, "Enemy MiG-29A shot down", Tone.GOOD),
        ReportEvent(None, "Enemy MiG-29A shot down", Tone.GOOD),
    ]

    # Unknown until the results are applied.
    assert not report.applied
    assert report.pilots_captured is None
    assert report.pilots_still_down is None
    assert report.budget_next_turn is None


def test_report_once_the_results_are_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    import game.income

    debriefing, parts = _debriefing()
    report = build_report(debriefing)
    parts["game"].pilots_captured_this_turn = [
        SimpleNamespace(
            name="Lt. Moroz",
            aircraft="F/A-18C",
            squadron="VF-11",
            player=Player.BLUE,
            control_point="Maykop",
        ),
        SimpleNamespace(
            name="Red",
            aircraft="MiG-29A",
            squadron="Red 1",
            player=Player.RED,
            control_point="Kutaisi",
        ),
    ]
    monkeypatch.setattr(
        game.income, "Income", lambda game, player: SimpleNamespace(total=180.0)
    )
    message = Information("Base captured", "Krymsk is ours", turn=4)
    message.timestamp = datetime.datetime(2026, 10, 30, 21, 5, 9)
    separator = Information("End of turn #4", "-" * 40, turn=4)
    separator.timestamp = datetime.datetime(2026, 10, 30, 21, 5, 10)

    final = complete_report(report, debriefing, [message, separator])

    assert final.applied
    assert final.pilots_captured == [
        PilotLine("Lt. Moroz", "F/A-18C", "VF-11", "Maykop")
    ]
    assert final.pilots_still_down == 2
    assert (final.budget_next_turn, final.income_next_turn) == (1420.46, 180.0)
    assert final.events[: len(report.events)] == report.events
    assert final.events[len(report.events) :] == [
        ReportEvent("21:05:09", "Base captured: Krymsk is ours", Tone.NEUTRAL),
        ReportEvent("21:05:10", "End of turn #4", Tone.NEUTRAL),
    ]
    # What was read before applying is kept.
    assert final.packages == report.packages
    assert final.verdict == report.verdict


def test_logged_events_without_title() -> None:
    message = Information("", "Repairs begun", turn=1)
    assert [e.text for e in logged_events([message])] == ["Repairs begun"]


def test_the_objectives_resolved_this_turn_have_their_own_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#194: met or missed, with what was granted, and not again in the log."""
    import game.income

    monkeypatch.setattr(
        game.income, "Income", lambda game, player: SimpleNamespace(total=180.0)
    )
    debriefing, parts = _debriefing()
    report = build_report(debriefing)
    assert report.objectives is None

    def objective(title: str, state: ObjectiveState, turn: int | None) -> Any:
        return CampaignObjective(
            title,
            ObjectiveKind.CAPTURE,
            "Krymsk",
            None,
            state=state,
            resolved_turn=turn,
            granted="+150 budget" if state is ObjectiveState.MET else "",
        )

    parts["game"].objectives.objectives = [
        objective("Capture Krymsk", ObjectiveState.MET, 4),
        objective("Capture Anapa", ObjectiveState.MISSED, 4),
        objective("Capture Maykop", ObjectiveState.MET, 2),  # an earlier turn
        objective("Capture Sochi", ObjectiveState.IN_PROGRESS, None),
    ]
    met = Information("Objective met: Capture Krymsk", "Reward: +150 budget", turn=4)
    missed = Information("Objective missed: Capture Anapa", "", turn=4)

    final = complete_report(report, debriefing, [met, missed])

    assert final.objectives == [
        ObjectiveLine("Capture Krymsk", True, "+150 budget"),
        ObjectiveLine("Capture Anapa", False, ""),
    ]
    assert final.events == report.events

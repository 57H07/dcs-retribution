"""The after-action report of a mission (WEB-05.2).

What the debriefing shows, computed from a `Debriefing` without any UI: the web
report (`GET /game/mission/result/report`) and the Qt debriefing window both read
it, so that neither front end holds report rules.

A report is built in two steps. `build_report` reads the result before it is
applied: verdict, kills, losses, rescues reported by the mission, the result of each
package (the ATO is replaced by the next turn's, so this must happen first) and the
mission events. `complete_report` adds what is only known once the results were
applied and the turn passed: pilots taken prisoner, pilots still down, the budget of
the next turn and the messages the engine logged meanwhile, with their time.
"""

from __future__ import annotations

import dataclasses
import logging
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, TYPE_CHECKING, TypeVar

from game.theater import Player
from game.theater.theatergroundobject import TheaterGroundObject

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.ato.package import Package
    from game.debriefing import Debriefing, SideLossCounts
    from game.infos.information import Information

T = TypeVar("T")


class Tone(Enum):
    """How a line reads for the player: good, bad, mixed or neutral news."""

    GOOD = "good"
    BAD = "bad"
    MIXED = "mixed"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class LossLine:
    """One line of a casualty report: a unit type and how many were lost."""

    name: str
    count: int


@dataclass(frozen=True)
class PilotLine:
    name: str
    aircraft: str
    squadron: str
    #: The base holding a prisoner; None for a rescued pilot.
    held_at: str | None = None


@dataclass(frozen=True)
class PackageResult:
    """How a friendly package of the mission fared."""

    task: str
    target: str
    flights: list[str]
    lost: int
    aircraft: int
    result: str
    tone: Tone


@dataclass(frozen=True)
class ReportEvent:
    #: Wall-clock time the engine logged the event (HH:MM:SS); None for events
    #: read from state.json, which carries no time.
    time: str | None
    text: str
    tone: Tone


@dataclass(frozen=True)
class DamagedUnitLine:
    friendly: bool
    unit_type: str
    damage_percent: int
    unavailability: str


@dataclass(frozen=True)
class AfterActionReport:
    turn: int
    date: str
    player_country: str
    enemy_country: str
    verdict: str
    verdict_tone: Tone
    summary: str
    #: Enemy aircraft destroyed (kills scored by friendly forces).
    air_kills_friendly: int
    #: Friendly aircraft destroyed (kills scored by the enemy).
    air_kills_enemy: int
    #: Enemy ground units, ships and buildings destroyed.
    ground_kills_friendly: int
    #: Friendly ground units, ships and buildings destroyed.
    ground_kills_enemy: int
    bases_captured: int
    bases_lost: int
    pilots_rescued: list[PilotLine]
    rescue_bounty: int
    packages: list[PackageResult]
    friendly_losses: list[LossLine]
    enemy_losses: list[LossLine]
    damaged_units: list[DamagedUnitLine]
    events: list[ReportEvent]
    #: True once the results were applied: the fields below are then known.
    applied: bool = False
    pilots_captured: list[PilotLine] | None = None
    pilots_still_down: int | None = None
    budget_next_turn: float | None = None
    income_next_turn: float | None = None


# --- casualty lists (formerly in qt_ui/windows/QDebriefingWindow.py) -----------


def _lines(losses: Mapping[T, int], make_name: Callable[[T], str]) -> list[LossLine]:
    lines = []
    for unit_type, count in losses.items():
        try:
            name = make_name(unit_type)
        except AttributeError:
            logging.exception(f"Could not make unit name for {unit_type}")
            name = str(getattr(unit_type, "id", unit_type))
        lines.append(LossLine(name, count))
    return lines


def loss_lines(debriefing: Debriefing, player: Player) -> list[LossLine]:
    """Every unit `player` lost in the mission, by type and origin."""
    return [
        *_lines(debriefing.air_losses.by_type(player), lambda u: u.display_name),
        *_lines(debriefing.front_line_losses_by_type(player), str),
        *_lines(
            debriefing.motorpool_losses_by_type(player),
            lambda u: f"{u} from motorpool",
        ),
        *_lines(debriefing.convoy_losses_by_type(player), lambda u: f"{u} from convoy"),
        *_lines(
            debriefing.cargo_ship_losses_by_type(player),
            lambda u: f"{u} from cargo ship",
        ),
        *_lines(
            debriefing.airlift_losses_by_type(player), lambda u: f"{u} from airlift"
        ),
        *_lines(debriefing.ground_object_losses_by_type(player), str),
        *_lines(debriefing.scenery_losses_by_type(player), str),
    ]


# --- verdict --------------------------------------------------------------------


def ground_losses(counts: SideLossCounts) -> int:
    """Ground units, ships and buildings in a side's loss counts."""
    return (
        counts.front_line
        + counts.motorpool
        + counts.convoy
        + counts.cargo_ships
        + counts.ground_objects
        + counts.scenery
    )


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def verdict(friendly: SideLossCounts, enemy: SideLossCounts) -> tuple[str, Tone, str]:
    """Title, tone and one-line summary of the mission outcome.

    Bases change hands first: capturing more bases than were lost is a victory
    whatever the losses. Otherwise the side that lost fewer units (aircraft, ground
    units, ships and buildings) carries the day.
    """
    captured, lost = enemy.bases_lost, friendly.bases_lost
    friendly_units = friendly.aircraft + ground_losses(friendly)
    enemy_units = enemy.aircraft + ground_losses(enemy)

    parts = [
        f"Enemy lost {_plural(enemy_units, 'unit')}, "
        f"we lost {_plural(friendly_units, 'unit')}."
    ]
    if captured:
        parts.append(f"{_plural(captured, 'base')} captured.")
    if lost:
        parts.append(f"{_plural(lost, 'base')} lost.")
    summary = " ".join(parts)

    if captured != lost:
        won = captured > lost
    elif enemy_units != friendly_units:
        won = enemy_units > friendly_units
    elif enemy_units == 0:
        return "No contact", Tone.NEUTRAL, "No losses on either side."
    else:
        return "Stalemate", Tone.MIXED, summary
    if won:
        return "Tactical victory", Tone.GOOD, summary
    return "Tactical defeat", Tone.BAD, summary


# --- packages -------------------------------------------------------------------


def _flight_name(flight: Flight) -> str:
    if flight.custom_name:
        return flight.custom_name
    return f"{flight.count}x {flight.unit_type}"


def _target_units_destroyed(debriefing: Debriefing, tgo: TheaterGroundObject) -> int:
    losses = debriefing.ground_losses
    return sum(
        1
        for loss in losses.enemy_ground_objects + losses.player_ground_objects
        if loss.theater_unit.ground_object is tgo
    ) + sum(
        1
        for loss in losses.enemy_scenery + losses.player_scenery
        if loss.ground_unit.ground_object is tgo
    )


def _package_result(
    debriefing: Debriefing, package: Package, lost: int, aircraft: int
) -> tuple[str, Tone]:
    target = package.target
    if isinstance(target, TheaterGroundObject) and not target.is_friendly(
        to_player=Player.BLUE
    ):
        # Read before the results are applied: alive counts are pre-mission.
        alive = target.alive_unit_count
        destroyed = _target_units_destroyed(debriefing, target)
        if alive > 0:
            if destroyed >= alive:
                return "Target destroyed", Tone.GOOD
            if destroyed > 0:
                return f"Target {round(100 * destroyed / alive)}%", Tone.MIXED
            return "Target intact", Tone.BAD
    if aircraft and lost >= aircraft:
        return "Package lost", Tone.BAD
    if lost:
        return f"{lost} aircraft lost", Tone.MIXED
    return "No losses", Tone.GOOD


def package_results(debriefing: Debriefing) -> list[PackageResult]:
    """The result of every friendly package of the mission, in ATO order."""
    lost_by_flight: Counter[int] = Counter(
        id(loss.flight) for loss in debriefing.air_losses.player
    )
    results = []
    for package in debriefing.game.blue.ato.packages:
        if not package.flights:
            continue
        task = package.primary_task
        lost = sum(lost_by_flight[id(f)] for f in package.flights)
        aircraft = sum(f.count for f in package.flights)
        result, tone = _package_result(debriefing, package, lost, aircraft)
        results.append(
            PackageResult(
                task="" if task is None else task.value,
                target=package.target.name,
                flights=[_flight_name(f) for f in package.flights],
                lost=lost,
                aircraft=aircraft,
                result=result,
                tone=tone,
            )
        )
    return results


# --- events ---------------------------------------------------------------------


def mission_events(debriefing: Debriefing) -> list[ReportEvent]:
    """What happened in the mission, as state.json reports it (no times)."""
    events = []
    for capture in debriefing.base_captures:
        if capture.captured_by_player.is_blue:
            events.append(
                ReportEvent(None, f"{capture.control_point.name} captured", Tone.GOOD)
            )
        else:
            events.append(
                ReportEvent(
                    None, f"{capture.control_point.name} lost to the enemy", Tone.BAD
                )
            )
    for kill in debriefing.pilot_kills:
        if not kill.flight.squadron.player.is_blue:
            continue
        category = kill.category.value.lower()
        article = "an" if category[0] in "aeiou" else "a"
        events.append(
            ReportEvent(
                None,
                f"{kill.pilot.name} ({_flight_name(kill.flight)}) scored "
                f"{article} {category} kill",
                Tone.GOOD,
            )
        )
    for loss in debriefing.air_losses.player:
        pilot = "" if loss.pilot is None else f" · {loss.pilot.name}"
        events.append(
            ReportEvent(
                None,
                f"{loss.flight.unit_type} of {loss.flight.squadron.name} lost{pilot}",
                Tone.BAD,
            )
        )
    for loss in debriefing.air_losses.enemy:
        events.append(
            ReportEvent(None, f"Enemy {loss.flight.unit_type} shot down", Tone.GOOD)
        )
    return events


def _is_separator(text: str) -> bool:
    return bool(text) and set(text) == {"-"}


def logged_events(messages: Iterable[Information]) -> list[ReportEvent]:
    """Messages the engine logged while applying the results, with their time."""
    events = []
    for message in messages:
        text = message.title
        if message.text and not _is_separator(message.text):
            text = f"{text}: {message.text}" if text else message.text
        events.append(
            ReportEvent(message.timestamp.strftime("%H:%M:%S"), text, Tone.NEUTRAL)
        )
    return events


# --- report ---------------------------------------------------------------------


def _pilot_line(pilot: Any, held_at: str | None = None) -> PilotLine:
    return PilotLine(pilot.name, pilot.aircraft, pilot.squadron, held_at)


def build_report(debriefing: Debriefing) -> AfterActionReport:
    """The report of a mission result not applied yet."""
    game = debriefing.game
    friendly = debriefing.loss_counts(Player.BLUE)
    enemy = debriefing.loss_counts(Player.RED)
    title, tone, summary = verdict(friendly, enemy)
    return AfterActionReport(
        turn=game.turn,
        date=game.conditions.start_time.strftime("%d %B %Y"),
        player_country=debriefing.player_country,
        enemy_country=debriefing.enemy_country,
        verdict=title,
        verdict_tone=tone,
        summary=summary,
        air_kills_friendly=enemy.aircraft,
        air_kills_enemy=friendly.aircraft,
        ground_kills_friendly=ground_losses(enemy),
        ground_kills_enemy=ground_losses(friendly),
        bases_captured=enemy.bases_lost,
        bases_lost=friendly.bases_lost,
        pilots_rescued=[
            _pilot_line(p) for p in debriefing.rescued_pilots_for(Player.BLUE)
        ],
        rescue_bounty=debriefing.rescue_bounty_for(Player.BLUE),
        packages=package_results(debriefing),
        friendly_losses=loss_lines(debriefing, Player.BLUE),
        enemy_losses=loss_lines(debriefing, Player.RED),
        damaged_units=[
            DamagedUnitLine(
                r.player.is_blue, r.unit_type, r.damage_percent, r.unavailability
            )
            for r in debriefing.damaged_unit_reports()
        ],
        events=mission_events(debriefing),
    )


def minimal_report(debriefing: Debriefing) -> AfterActionReport:
    """What is left to show when the full report could not be built."""
    game = debriefing.game
    return AfterActionReport(
        turn=game.turn,
        date=game.conditions.start_time.strftime("%d %B %Y"),
        player_country=debriefing.player_country,
        enemy_country=debriefing.enemy_country,
        verdict="Results applied",
        verdict_tone=Tone.NEUTRAL,
        summary="The detailed report could not be built; see the log.",
        air_kills_friendly=0,
        air_kills_enemy=0,
        ground_kills_friendly=0,
        ground_kills_enemy=0,
        bases_captured=0,
        bases_lost=0,
        pilots_rescued=[],
        rescue_bounty=0,
        packages=[],
        friendly_losses=[],
        enemy_losses=[],
        damaged_units=[],
        events=[],
        applied=True,
    )


def complete_report(
    report: AfterActionReport,
    debriefing: Debriefing,
    messages: Iterable[Information],
) -> AfterActionReport:
    """`report` once its results were applied and the next turn began.

    `messages` are the `Game.informations` entries logged meanwhile.
    """
    from game.income import Income

    game = debriefing.game
    return dataclasses.replace(
        report,
        applied=True,
        # Rescues the results processor credited to surviving AI CSAR flights.
        pilots_rescued=[
            _pilot_line(p) for p in debriefing.rescued_pilots_for(Player.BLUE)
        ],
        rescue_bounty=debriefing.rescue_bounty_for(Player.BLUE),
        pilots_captured=[
            _pilot_line(p, p.control_point)
            for p in debriefing.captured_pilots_for(Player.BLUE)
        ],
        pilots_still_down=len(game.blue.downed_pilots),
        budget_next_turn=round(game.blue.budget, 2),
        income_next_turn=round(Income(game, player=Player.BLUE).total, 2),
        events=report.events + logged_events(messages),
    )

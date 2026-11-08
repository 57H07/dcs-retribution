"""The war diary (#193): one entry per accepted mission result, kept in the save.

An entry is built from what the debrief already computed: the completed
after-action report (`game.debriefingreport`) and the `Debriefing` it was read
from, plus two things only known around the turn change: the weather of the
mission and how far each front line moved. It holds plain values only, so the
save stays small over a long campaign (no event log, no damaged units) and an
entry outlives the bases, pilots and packages it names.

The diary of a campaign started before this feature begins with the first turn
accepted after the update: `Game.war_diary_since_turn` says when.
"""

from __future__ import annotations

import dataclasses
import html
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from game import autosaves
from game.theater import Player
from game.weather.description import describe_sky

if TYPE_CHECKING:
    from game.debriefing import Debriefing
    from game.debriefingreport import AfterActionReport
    from game.game import Game

#: Front line moves below this are noise of the strength rounding (km).
MIN_FRONT_MOVE_KM = 0.1


@dataclass(frozen=True)
class DiaryBase:
    #: `ControlPoint.id`, to open the base.
    id: str
    name: str
    #: True if we took it, False if we lost it.
    taken: bool


@dataclass(frozen=True)
class DiaryFront:
    name: str
    #: Positive when our side advanced, negative when it fell back.
    moved_km: float


@dataclass(frozen=True)
class DiaryPackage:
    task: str
    target: str
    flights: list[str]
    lost: int
    aircraft: int
    result: str
    #: A `debriefingreport.Tone` value: "good", "bad", "mixed" or "neutral".
    tone: str


@dataclass(frozen=True)
class DiaryLoss:
    name: str
    count: int


@dataclass(frozen=True)
class DiaryPilot:
    #: `Pilot.id` of a player pilot, to open their career; None for the others.
    pilot_id: str | None
    name: str
    squadron: str
    aircraft: str
    #: "Killed in action", "Taken prisoner" or "Rescued".
    fate: str


@dataclass(frozen=True)
class DiaryAward:
    pilot_id: str
    pilot: str
    #: "Rank" or "Decoration".
    kind: str
    name: str
    abbreviation: str
    reason: str


@dataclass(frozen=True)
class DiaryEntry:
    turn: int
    date: str
    weather: str
    verdict: str
    verdict_tone: str
    #: The turn in one line: bases, fronts, losses, pilots, awards.
    summary: str
    air_kills_friendly: int
    air_kills_enemy: int
    ground_kills_friendly: int
    ground_kills_enemy: int
    bases: list[DiaryBase] = field(default_factory=list)
    fronts: list[DiaryFront] = field(default_factory=list)
    packages: list[DiaryPackage] = field(default_factory=list)
    friendly_losses: list[DiaryLoss] = field(default_factory=list)
    enemy_losses: list[DiaryLoss] = field(default_factory=list)
    pilots: list[DiaryPilot] = field(default_factory=list)
    awards: list[DiaryAward] = field(default_factory=list)
    budget_next_turn: float | None = None
    income_next_turn: float | None = None


@dataclass(frozen=True)
class FrontPosition:
    """Where a front line stands: its depth from our base, in metres."""

    #: Ids of its two control points (ours first).
    key: tuple[str, str]
    name: str
    depth_m: float


@dataclass(frozen=True)
class TurnSnapshot:
    """What the turn change overwrites: read before the results are applied."""

    weather: str
    fronts: tuple[FrontPosition, ...]


# --- snapshots ------------------------------------------------------------------


def front_positions(game: Game) -> tuple[FrontPosition, ...]:
    positions = []
    for front_line in game.theater.conflicts():
        blue, red = front_line.blue_cp, front_line.red_cp
        positions.append(
            FrontPosition(
                key=(str(blue.id), str(red.id)),
                name=f"{blue.name} – {red.name}",
                depth_m=blue.position.distance_to_point(front_line.position),
            )
        )
    return tuple(positions)


def snapshot(game: Game) -> TurnSnapshot:
    return TurnSnapshot(str(describe_sky(game.conditions)), front_positions(game))


# --- entry ----------------------------------------------------------------------


def _fronts(
    before: Iterable[FrontPosition], after: Iterable[FrontPosition]
) -> list[DiaryFront]:
    now = {front.key: front for front in after}
    moves = []
    for front in before:
        moved = now.get(front.key)
        if moved is None:
            # The front closed: a base changed hands, told by `bases`.
            continue
        km = (moved.depth_m - front.depth_m) / 1000
        if abs(km) >= MIN_FRONT_MOVE_KM:
            moves.append(DiaryFront(front.name, round(km, 1)))
    return moves


def _pilots(report: AfterActionReport, debriefing: Debriefing) -> list[DiaryPilot]:
    pilots = []
    for loss in debriefing.air_losses.player:
        pilot = loss.pilot
        if pilot is None or pilot.alive:
            continue
        pilots.append(
            DiaryPilot(
                str(pilot.id) if pilot.player else None,
                pilot.name,
                loss.flight.squadron.name,
                str(loss.flight.unit_type),
                "Killed in action",
            )
        )
    for line in report.pilots_captured or []:
        pilots.append(
            DiaryPilot(None, line.name, line.squadron, line.aircraft, "Taken prisoner")
        )
    # The rescues as the results credited them (AI CSAR flights included).
    for rescued in debriefing.rescued_pilots_for(Player.BLUE):
        pilot = rescued.pilot
        pilots.append(
            DiaryPilot(
                str(pilot.id) if pilot is not None and pilot.player else None,
                rescued.name,
                rescued.squadron,
                rescued.aircraft,
                "Rescued",
            )
        )
    return pilots


def _awards(report: AfterActionReport) -> list[DiaryAward]:
    return [
        DiaryAward(
            card.pilot_id,
            card.pilot,
            award.kind,
            award.name,
            award.abbreviation,
            award.reason,
        )
        for card in report.your_sorties
        for award in card.awards or []
    ]


_FATE_WORDS = {
    "Killed in action": "killed",
    "Taken prisoner": "taken prisoner",
    "Rescued": "rescued",
}


def summary(entry: DiaryEntry, fallback: str) -> str:
    """The turn in one line; `fallback` (the verdict summary) for a quiet turn."""
    parts = [f"{b.name} {'taken' if b.taken else 'lost'}" for b in entry.bases]
    parts += [
        f"{f.name} front {'advanced' if f.moved_km > 0 else 'fell back'} "
        f"{abs(f.moved_km)} km"
        for f in entry.fronts
    ]
    if entry.air_kills_enemy:
        parts.append(f"{entry.air_kills_enemy} aircraft lost")
    if entry.air_kills_friendly:
        parts.append(f"{entry.air_kills_friendly} enemy aircraft shot down")
    # Player pilots only: the others are in the details.
    parts += [f"{p.name} {_FATE_WORDS[p.fate]}" for p in entry.pilots if p.pilot_id]
    parts += [
        f"{a.pilot} {'promoted to' if a.kind == 'Rank' else 'awarded'} {a.name}"
        for a in entry.awards
    ]
    return ", ".join(parts) if parts else fallback


def build_entry(
    report: AfterActionReport,
    debriefing: Debriefing,
    before: TurnSnapshot,
    after: Sequence[FrontPosition],
) -> DiaryEntry:
    """The entry of a completed report, `before` and `after` the turn changed."""
    entry = DiaryEntry(
        turn=report.turn,
        date=report.date,
        weather=before.weather,
        verdict=report.verdict,
        verdict_tone=report.verdict_tone.value,
        summary="",
        air_kills_friendly=report.air_kills_friendly,
        air_kills_enemy=report.air_kills_enemy,
        ground_kills_friendly=report.ground_kills_friendly,
        ground_kills_enemy=report.ground_kills_enemy,
        bases=[
            DiaryBase(
                str(capture.control_point.id),
                capture.control_point.name,
                capture.captured_by_player.is_blue,
            )
            for capture in debriefing.base_captures
        ],
        fronts=_fronts(before.fronts, after),
        packages=[
            DiaryPackage(
                p.task,
                p.target,
                list(p.flights),
                p.lost,
                p.aircraft,
                p.result,
                p.tone.value,
            )
            for p in report.packages
        ],
        friendly_losses=[DiaryLoss(x.name, x.count) for x in report.friendly_losses],
        enemy_losses=[DiaryLoss(x.name, x.count) for x in report.enemy_losses],
        pilots=_pilots(report, debriefing),
        awards=_awards(report),
        budget_next_turn=report.budget_next_turn,
        income_next_turn=report.income_next_turn,
    )
    return _with_summary(entry, report.summary)


def _with_summary(entry: DiaryEntry, fallback: str) -> DiaryEntry:
    return dataclasses.replace(entry, summary=summary(entry, fallback))


def record_turn(
    game: Game,
    report: AfterActionReport,
    debriefing: Debriefing,
    before: TurnSnapshot,
) -> None:
    """Adds the entry of `report` to the diary, and to the autosave of the turn.

    The caller holds the game lock. The turn's autosave was written while the turn
    passed, before the report was complete: it is written again with the entry.
    """
    game.war_diary.append(
        build_entry(report, debriefing, before, front_positions(game))
    )
    autosaves.autosave(game, autosaves.SaveKind.TURN)


# --- export ---------------------------------------------------------------------

_STYLE = """
body { font-family: Segoe UI, Arial, sans-serif; margin: 2rem auto; max-width: 56rem;
  padding: 0 1rem; color: #1d232a; background: #f6f5f1; line-height: 1.45; }
h1 { margin-bottom: 0.2rem; }
.note { color: #5b6470; font-style: italic; }
article { background: #fff; border: 1px solid #d6d3c9; padding: 0.8rem 1.1rem;
  margin: 1rem 0; }
h2 { font-size: 1.1rem; margin: 0 0 0.3rem; }
.meta { color: #5b6470; font-size: 0.9rem; }
.good { color: #2f7d32; } .bad { color: #b3261e; } .mixed { color: #a8660a; }
h3 { font-size: 0.95rem; margin: 0.8rem 0 0.2rem; }
ul { margin: 0.2rem 0; padding-left: 1.2rem; }
"""


def _e(value: object) -> str:
    return html.escape(str(value))


def _list(title: str, items: list[str]) -> str:
    if not items:
        return ""
    lines = "".join(f"<li>{item}</li>" for item in items)
    return f"<h3>{_e(title)}</h3><ul>{lines}</ul>"


def _entry_html(entry: DiaryEntry) -> str:
    parts = [
        f"<article><h2>Turn {entry.turn} · {_e(entry.date)}</h2>",
        f'<p class="meta">{_e(entry.weather)} · '
        f'<span class="{_e(entry.verdict_tone)}">{_e(entry.verdict)}</span></p>',
        f"<p>{_e(entry.summary)}</p>",
        _list(
            "Bases",
            [f"{_e(b.name)} {'taken' if b.taken else 'lost'}" for b in entry.bases],
        ),
        _list(
            "Front lines",
            [f"{_e(f.name)}: {f.moved_km:+} km" for f in entry.fronts],
        ),
        _list(
            "Packages",
            [
                f"{_e(p.task)} · {_e(p.target)} ({_e(', '.join(p.flights))}): "
                f'<span class="{_e(p.tone)}">{_e(p.result)}</span>, '
                f"{p.lost} / {p.aircraft} lost"
                for p in entry.packages
            ],
        ),
        _list(
            "Our losses", [f"{_e(x.name)} × {x.count}" for x in entry.friendly_losses]
        ),
        _list(
            "Enemy losses", [f"{_e(x.name)} × {x.count}" for x in entry.enemy_losses]
        ),
        _list(
            "Pilots",
            [
                f"{_e(p.name)} ({_e(p.squadron)}, {_e(p.aircraft)}): {_e(p.fate)}"
                for p in entry.pilots
            ],
        ),
        _list(
            "Awards",
            [
                f"{_e(a.pilot)}: {_e(a.name)}"
                + (f" ({_e(a.reason)})" if a.reason else "")
                for a in entry.awards
            ],
        ),
        "</article>",
    ]
    return "".join(parts)


def export_html(
    campaign: str, entries: Sequence[DiaryEntry], since_turn: int | None
) -> str:
    """The whole diary as one HTML page, newest first, that needs nothing else."""
    note = (
        f'<p class="note">This campaign was started before the war diary existed. '
        f"The diary begins at turn {since_turn}.</p>"
        if since_turn is not None
        else ""
    )
    body = "".join(_entry_html(e) for e in reversed(entries)) or (
        '<p class="note">No turn recorded yet.</p>'
    )
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        f"<title>War diary · {_e(campaign)}</title>"
        f"<style>{_STYLE}</style></head>"
        f'<body><h1>War diary</h1><p class="meta">{_e(campaign)}</p>{note}'
        f"{body}</body></html>\n"
    )


def log_failure(what: str) -> None:
    logging.exception(f"War diary: could not {what}")

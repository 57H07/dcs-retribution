"""Rotating autosaves of a campaign, and the saves the Load screen offers (#190).

Each campaign has its own folder under `<Saved Games>/Retribution/Saves/Autosaves`,
named after `Game.campaign_id`. It holds one autosave at the start of each turn
(`turn-0012.retribution`) and one before each Take off (`takeoff-0012.retribution`),
for the last N turns, plus `index.json`: what each save is, so the Load screen lists
them without unpickling any. Manual saves of the campaign are recorded in the same
index (their files stay where the player put them).

Going back a turn and playing on starts another timeline: an autosave drops the
autosaves of the turns after it, which belonged to the abandoned one.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from game import persistency

if TYPE_CHECKING:
    from game import Game

AUTOSAVES_FOLDER = "Autosaves"
INDEX_FILE = "index.json"
DEFAULT_KEEP_TURNS = 5
MAX_KEEP_TURNS = 50


class SaveKind(str, Enum):
    #: Autosave at the start of a turn.
    TURN = "turn"
    #: Autosave before Take off, with the planning of the turn.
    TAKEOFF = "takeoff"
    #: Saved by the player (Save, Save as).
    MANUAL = "manual"

    @property
    def is_autosave(self) -> bool:
        return self is not SaveKind.MANUAL


@dataclass(frozen=True)
class SaveEntry:
    id: str
    kind: SaveKind
    path: Path
    turn: int
    game_date: date
    saved_at: datetime
    campaign_name: str

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "path": str(self.path),
            "turn": self.turn,
            "game_date": self.game_date.isoformat(),
            "saved_at": self.saved_at.isoformat(timespec="seconds"),
            "campaign_name": self.campaign_name,
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> SaveEntry:
        return SaveEntry(
            id=data["id"],
            kind=SaveKind(data["kind"]),
            path=Path(data["path"]),
            turn=int(data["turn"]),
            game_date=date.fromisoformat(data["game_date"]),
            saved_at=datetime.fromisoformat(data["saved_at"]),
            campaign_name=data["campaign_name"],
        )


def autosaves_root() -> Path:
    return persistency.save_dir() / AUTOSAVES_FOLDER


def campaign_folder(game: Game, root: Path | None = None) -> Path:
    return (root or autosaves_root()) / game.campaign_id


def autosave(
    game: Game, kind: SaveKind, keep: int | None = None, root: Path | None = None
) -> SaveEntry | None:
    """Autosave `game`; None when it failed (logged: the turn or Take off goes on).

    A failed write never replaces the previous autosave of the same turn.
    """
    if not kind.is_autosave:
        raise ValueError(f"{kind} is not an autosave")
    try:
        return _autosave(game, kind, keep, root)
    except Exception:
        logging.exception("Could not autosave turn %s", getattr(game, "turn", "?"))
        return None


def _autosave(
    game: Game, kind: SaveKind, keep: int | None, root: Path | None
) -> SaveEntry:
    folder = campaign_folder(game, root)
    entry = _entry(
        game,
        kind,
        id=f"{kind.value}-{game.turn:04d}",
        path=folder / f"{kind.value}-{game.turn:04d}.retribution",
    )
    persistency.write_game(game, entry.path)
    entries = []
    for existing in _read_index(folder):
        if existing.id == entry.id:
            continue
        if _abandoned_by(existing, entry):
            _delete(existing.path)
        else:
            entries.append(existing)
    entries.append(entry)
    _write_index(folder, _rotate(entries, keep_turns() if keep is None else keep))
    return entry


def _abandoned_by(existing: SaveEntry, new: SaveEntry) -> bool:
    """True when `existing` is an autosave of a timeline `new` left behind.

    The start of turn T comes before its Take off, so a new start of turn T also
    leaves the Take off of turn T behind. Manual saves are the player's: kept.
    """
    if not existing.kind.is_autosave:
        return False
    if existing.turn > new.turn:
        return True
    return (
        new.kind is SaveKind.TURN
        and existing.kind is SaveKind.TAKEOFF
        and existing.turn == new.turn
    )


def keep_turns() -> int:
    """How many turns of autosaves the player keeps (File → Preferences)."""
    from game import liberation_install

    return liberation_install.autosave_turns()


def _rotate(entries: list[SaveEntry], keep: int) -> list[SaveEntry]:
    """Delete the autosaves older than the last `keep` turns; returns the rest."""
    turns = sorted({e.turn for e in entries if e.kind.is_autosave}, reverse=True)
    kept_turns = set(turns[: max(keep, 1)])
    kept = []
    for entry in entries:
        if entry.kind.is_autosave and entry.turn not in kept_turns:
            _delete(entry.path)
        else:
            kept.append(entry)
    return kept


def _delete(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logging.exception("Could not delete the old autosave %s", path)


def list_saves(game: Game, root: Path | None = None) -> list[SaveEntry]:
    """The saves of the campaign whose file still exists, newest first."""
    entries = [e for e in _read_index(campaign_folder(game, root)) if e.path.exists()]
    # The index is in the order of the saves: reversed first, the newest of saves
    # made within the same second still comes first.
    return sorted(reversed(entries), key=lambda e: e.saved_at, reverse=True)


def record_manual_save(game: Game, path: Path, root: Path | None = None) -> None:
    """Remember that the player saved the campaign to `path` (Save, Save as)."""
    path = Path(path).resolve()
    digest = hashlib.sha1(str(path).lower().encode("utf-8")).hexdigest()[:12]
    # The save itself succeeded: failing to list it must not fail it.
    try:
        entry = _entry(game, SaveKind.MANUAL, id=f"manual-{digest}", path=path)
        folder = campaign_folder(game, root)
        entries = [e for e in _read_index(folder) if e.id != entry.id]
        _write_index(folder, entries + [entry])
    except Exception:
        logging.exception("Could not record the save %s", path)


def find_save(game: Game, save_id: str, root: Path | None = None) -> SaveEntry:
    """The listed save `save_id` of the campaign; KeyError when there is none."""
    for entry in list_saves(game, root):
        if entry.id == save_id:
            return entry
    raise KeyError(save_id)


def previous_turn_save(game: Game, root: Path | None = None) -> SaveEntry | None:
    """The autosave to go back a turn: before Take off of the previous turn, or
    else its start. None when there is none."""
    candidates = [
        e
        for e in list_saves(game, root)
        if e.kind.is_autosave and e.turn == game.turn - 1
    ]
    for kind in (SaveKind.TAKEOFF, SaveKind.TURN):
        for entry in candidates:
            if entry.kind is kind:
                return entry
    return None


def _entry(game: Game, kind: SaveKind, id: str, path: Path) -> SaveEntry:
    return SaveEntry(
        id=id,
        kind=kind,
        path=path,
        turn=game.turn,
        game_date=game.conditions.start_time.date(),
        saved_at=datetime.now().replace(microsecond=0),
        campaign_name=game.campaign_name or "",
    )


def _read_index(folder: Path) -> list[SaveEntry]:
    path = folder / INDEX_FILE
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as f:
            return [SaveEntry.from_json(item) for item in json.load(f)]
    except (OSError, ValueError, KeyError, TypeError):
        logging.exception("Unreadable autosave index %s", path)
        return []


def _write_index(folder: Path, entries: list[SaveEntry]) -> None:
    text = json.dumps([e.to_json() for e in entries], indent=2)
    persistency.write_atomically(
        folder / INDEX_FILE, lambda f: f.write(text.encode("utf-8"))
    )


def fork(game: Game) -> None:
    """Give `game` autosaves of its own: a copy saved to another file must not
    rotate or drop the autosaves of the original."""
    game.campaign_id = uuid4().hex

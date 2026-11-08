"""#190: rotating autosaves per campaign, per turn and before take off."""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from game import autosaves
from game.autosaves import SaveKind


@dataclass
class FakeGame:
    """Just what a save needs: picklable, with a theater holding a landmap."""

    campaign_id: str = "campaign-a"
    campaign_name: str = "Exercise Quasar"
    turn: int = 1
    savepath: str = ""
    theater: Any = field(default_factory=lambda: SimpleNamespace(landmap="LANDMAP"))
    conditions: Any = field(
        default_factory=lambda: SimpleNamespace(start_time=datetime(1999, 6, 14, 8))
    )


def fake_game(**fields: Any) -> Any:
    """A `FakeGame`, typed loosely: it stands for a `Game`."""
    return FakeGame(**fields)


def _load(path: Path) -> Any:
    with path.open("rb") as f:
        return pickle.load(f)


def test_turn_autosave_is_listed_and_loadable(tmp_path: Path) -> None:
    game = fake_game(turn=3)

    entry = autosaves.autosave(game, SaveKind.TURN, root=tmp_path)

    assert entry is not None
    [listed] = autosaves.list_saves(game, root=tmp_path)
    assert listed.id == entry.id
    assert listed.kind is SaveKind.TURN
    assert listed.turn == 3
    assert listed.campaign_name == "Exercise Quasar"
    assert listed.game_date.isoformat() == "1999-06-14"
    assert _load(listed.path).turn == 3


def test_only_the_last_n_turns_are_kept(tmp_path: Path) -> None:
    game = fake_game()
    for turn in range(1, 5):
        game.turn = turn
        autosaves.autosave(game, SaveKind.TURN, root=tmp_path)
        autosaves.autosave(game, SaveKind.TAKEOFF, keep=2, root=tmp_path)

    kept = autosaves.list_saves(game, root=tmp_path)

    assert sorted((e.turn, e.kind.value) for e in kept) == [
        (3, "takeoff"),
        (3, "turn"),
        (4, "takeoff"),
        (4, "turn"),
    ]
    files = sorted(p.name for p in (tmp_path / "campaign-a").glob("*.retribution"))
    assert files == [
        "takeoff-0003.retribution",
        "takeoff-0004.retribution",
        "turn-0003.retribution",
        "turn-0004.retribution",
    ]


def test_playing_on_from_an_earlier_turn_drops_the_abandoned_turns(
    tmp_path: Path,
) -> None:
    game = fake_game()
    for turn in range(1, 5):
        game.turn = turn
        autosaves.autosave(game, SaveKind.TURN, root=tmp_path)
        autosaves.autosave(game, SaveKind.TAKEOFF, root=tmp_path)

    # Back to the start of turn 2, then on to turn 3 again.
    game.turn = 3
    autosaves.autosave(game, SaveKind.TURN, root=tmp_path)

    kept = autosaves.list_saves(game, root=tmp_path)
    assert sorted((e.turn, e.kind.value) for e in kept) == [
        (1, "takeoff"),
        (1, "turn"),
        (2, "takeoff"),
        (2, "turn"),
        (3, "turn"),
    ]


def test_a_failed_autosave_keeps_the_previous_one_and_the_game_intact(
    tmp_path: Path,
) -> None:
    game = fake_game(turn=2)
    autosaves.autosave(game, SaveKind.TURN, root=tmp_path)

    game.savepath = lambda: None  # cannot be pickled
    assert autosaves.autosave(game, SaveKind.TURN, root=tmp_path) is None

    assert game.theater.landmap == "LANDMAP"
    [kept] = autosaves.list_saves(game, root=tmp_path)
    assert _load(kept.path).savepath == ""
    assert not list((tmp_path / "campaign-a").glob("*.tmp"))


def test_manual_saves_are_listed_but_never_rotated(tmp_path: Path) -> None:
    game = fake_game(turn=1)
    manual = tmp_path / "elsewhere" / "my campaign.retribution"
    manual.parent.mkdir()
    manual.write_bytes(b"save")
    autosaves.record_manual_save(game, manual, root=tmp_path)
    for turn in range(2, 6):
        game.turn = turn
        autosaves.autosave(game, SaveKind.TURN, keep=1, root=tmp_path)

    saves = autosaves.list_saves(game, root=tmp_path)

    assert [(e.kind.value, e.turn) for e in saves if e.kind is SaveKind.MANUAL] == [
        ("manual", 1)
    ]
    assert manual.exists()
    assert autosaves.find_save(game, saves[-1].id, root=tmp_path) == saves[-1]


def test_a_manual_save_deleted_by_the_player_is_not_listed(tmp_path: Path) -> None:
    game = fake_game()
    manual = tmp_path / "gone.retribution"
    manual.write_bytes(b"save")
    autosaves.record_manual_save(game, manual, root=tmp_path)
    manual.unlink()

    assert autosaves.list_saves(game, root=tmp_path) == []


def test_previous_turn_prefers_the_save_before_take_off(tmp_path: Path) -> None:
    game = fake_game()
    for turn in (1, 2):
        game.turn = turn
        autosaves.autosave(game, SaveKind.TURN, root=tmp_path)
    game.turn = 1
    assert autosaves.previous_turn_save(game, root=tmp_path) is None

    game.turn = 2
    turn_1 = autosaves.previous_turn_save(game, root=tmp_path)
    assert turn_1 is not None and (turn_1.turn, turn_1.kind) == (1, SaveKind.TURN)

    game.turn = 2
    autosaves.autosave(game, SaveKind.TAKEOFF, root=tmp_path)
    game.turn = 3
    autosaves.autosave(game, SaveKind.TURN, root=tmp_path)
    turn_2 = autosaves.previous_turn_save(game, root=tmp_path)
    assert turn_2 is not None and (turn_2.turn, turn_2.kind) == (2, SaveKind.TAKEOFF)


def test_an_unknown_save_cannot_be_found(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        autosaves.find_save(fake_game(), "turn-0099", root=tmp_path)


def test_a_save_as_copy_gets_autosaves_of_its_own(tmp_path: Path) -> None:
    original = fake_game(turn=8)
    autosaves.autosave(original, SaveKind.TURN, root=tmp_path)
    copy = fake_game(turn=3, campaign_id=original.campaign_id)
    autosaves.fork(copy)

    autosaves.autosave(copy, SaveKind.TURN, root=tmp_path)

    assert [e.turn for e in autosaves.list_saves(original, root=tmp_path)] == [8]


def test_an_autosave_never_breaks_the_turn(tmp_path: Path) -> None:
    broken: Any = SimpleNamespace()  # no campaign_id, turn or theater
    assert autosaves.autosave(broken, SaveKind.TURN, root=tmp_path) is None

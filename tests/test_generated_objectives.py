"""#210: objectives generated for a campaign that defines none, all along the front.

They follow the front as it moves: at the end of each turn the objectives met or
missed are replaced by new ones on the front as it is then, and the ones the front
has passed are closed without reward nor penalty.
"""

from __future__ import annotations

from typing import Any

from game import objectivegen, objectives
from game.objectives import ObjectiveKind, ObjectiveState
from tests.test_campaign_objectives import (
    BLUE,
    RED,
    FakeGame,
    _connect,
    _cp,
    _tgo,
)


class At:
    """A position on a line, as far as the generator measures."""

    def __init__(self, x: float) -> None:
        self.x = x

    def distance_to_point(self, other: "At") -> float:
        return abs(self.x - other.x)


def _place(cp: Any, x: float) -> Any:
    cp.position = At(x)
    for tgo in cp.ground_objects:
        tgo.position = At(x)
    return cp


def _theater(count: int = 4) -> tuple[FakeGame, dict[str, Any]]:
    """Kobuleti - Batumi (blue) | Kutaisi - Tbilisi (red), along a line.

    Kutaisi, on the front, has a SAM, an EWR and a factory; Tbilisi, behind it,
    the same. A second red base, Senaki, faces Batumi from further away.
    """
    kobuleti = _place(_cp("Kobuleti", BLUE), 0)
    batumi = _place(_cp("Batumi", BLUE), 10)
    kutaisi = _place(
        _cp(
            "Kutaisi",
            ground_objects=[
                _tgo("SAM-Kutaisi"),
                _tgo("EWR-Kutaisi", category="ewr"),
                _tgo("Factory-Kutaisi", category="factory", iads=False),
            ],
        ),
        20,
    )
    senaki = _place(_cp("Senaki"), 40)
    tbilisi = _place(
        _cp(
            "Tbilisi",
            ground_objects=[
                _tgo("SAM-Tbilisi"),
                _tgo("Factory-Tbilisi", category="factory", iads=False),
            ],
        ),
        30,
    )
    _connect(kobuleti, batumi)
    _connect(batumi, kutaisi)
    _connect(batumi, senaki)
    _connect(kutaisi, tbilisi)
    game = FakeGame([kobuleti, batumi, kutaisi, senaki, tbilisi])
    game.turn = 0
    game.settings.generated_objectives_count = count
    game.objectives.generate = True
    parts = dict(
        kobuleti=kobuleti,
        batumi=batumi,
        kutaisi=kutaisi,
        senaki=senaki,
        tbilisi=tbilisi,
    )
    return game, parts


def _titles(
    game: FakeGame, state: ObjectiveState = ObjectiveState.IN_PROGRESS
) -> list[str]:
    return [o.title for o in game.objectives.objectives if o.state is state]


def _top_up(game: FakeGame, announce: bool = False) -> None:
    objectivegen.top_up(game, announce)  # type: ignore[arg-type]


def _end_turn(game: FakeGame) -> None:
    objectives.end_of_turn(game)  # type: ignore[arg-type]
    game.turn += 1


def test_one_objective_of_each_kind_on_the_front() -> None:
    game, parts = _theater()

    _top_up(game)

    assert _titles(game) == [
        "Capture Kutaisi",
        "Blind the enemy air defences at Kutaisi",
        "Destroy the factory at Kutaisi",
        "Hold Batumi",
    ]
    capture, iads, factory, hold = game.objectives.objectives
    assert all(o.generated for o in game.objectives.objectives)
    assert capture.kind is ObjectiveKind.CAPTURE
    assert capture.control_point_id == parts["kutaisi"].id
    # The land air defences of the base: its SAM and its radar, not the factory.
    assert iads.kind is ObjectiveKind.DESTROY
    assert {
        t.original_name
        for t in parts["kutaisi"].ground_objects
        if t.id in iads.ground_object_ids
    } == {"SAM-Kutaisi", "EWR-Kutaisi"}
    assert [
        t.original_name
        for t in parts["kutaisi"].ground_objects
        if t.id in factory.ground_object_ids
    ] == ["Factory-Kutaisi"]
    assert hold.kind is ObjectiveKind.HOLD
    assert hold.control_point_id == parts["batumi"].id
    # Deadlines a few turns ahead, and a reward each.
    assert [o.deadline for o in game.objectives.objectives] == [5, 3, 4, 3]
    assert all(not o.reward.is_empty for o in game.objectives.objectives)
    # Nothing behind the front.
    assert not any("Tbilisi" in t or "Kobuleti" in t for t in _titles(game))
    # Generated at campaign creation: nothing announced.
    assert game.messages == []


def test_as_many_as_the_setting_asks() -> None:
    game, _ = _theater(count=2)
    _top_up(game)
    assert _titles(game) == [
        "Capture Kutaisi",
        "Blind the enemy air defences at Kutaisi",
    ]


def test_the_nearest_enemy_base_is_taken_first() -> None:
    """Kutaisi is 10 from Batumi, Senaki 30: then Senaki for a second capture."""
    game, _ = _theater(count=6)
    _top_up(game)
    assert _titles(game) == [
        "Capture Kutaisi",
        "Blind the enemy air defences at Kutaisi",
        "Destroy the factory at Kutaisi",
        "Hold Batumi",
        "Capture Senaki",
    ]


def test_the_objectives_spread_along_the_front() -> None:
    """With air defences at Senaki too, the second objective goes there."""
    game, parts = _theater(count=2)
    sam = _tgo("SAM-Senaki")
    sam.control_point = parts["senaki"]
    sam.position = parts["senaki"].position
    parts["senaki"].ground_objects.append(sam)

    _top_up(game)

    assert _titles(game) == [
        "Capture Kutaisi",
        "Blind the enemy air defences at Senaki",
    ]


def test_without_a_front_there_is_none() -> None:
    blue = _place(_cp("Batumi", BLUE), 0)
    red = _place(_cp("Kutaisi", ground_objects=[_tgo("SAM")]), 50)
    game = FakeGame([blue, red])
    game.objectives.generate = True
    _top_up(game)
    assert game.objectives.objectives == []


def test_a_met_objective_is_replaced_on_the_new_front() -> None:
    game, parts = _theater(count=1)
    _top_up(game)
    assert _titles(game) == ["Capture Kutaisi"]

    parts["kutaisi"].captured = BLUE
    _end_turn(game)

    assert _titles(game, ObjectiveState.MET) == ["Capture Kutaisi"]
    # Kutaisi is the player's: Tbilisi, behind it, is the front now.
    assert _titles(game) == ["Capture Tbilisi"]
    [(_, text)] = [m for m in game.messages if m[0] == "New objective: Capture Tbilisi"]
    assert text.startswith("By turn 5.")


def test_an_objective_the_front_has_passed_is_closed_and_replaced() -> None:
    game, parts = _theater(count=4)
    _top_up(game)
    budget = game.blue.budget

    # Both enemy bases facing Batumi fall: Batumi is behind the front now.
    parts["kutaisi"].captured = BLUE
    parts["senaki"].captured = BLUE
    _end_turn(game)

    hold = next(o for o in game.objectives.objectives if o.title == "Hold Batumi")
    assert hold.state is ObjectiveState.OVERTAKEN
    assert hold.resolved_turn == 0
    assert hold.granted == ""
    assert any(t == "Objective overtaken: Hold Batumi" for t, _ in game.messages)
    # Captured with Kutaisi: the destroy objectives there are met.
    assert _titles(game, ObjectiveState.MET) == [
        "Capture Kutaisi",
        "Blind the enemy air defences at Kutaisi",
        "Destroy the factory at Kutaisi",
    ]
    assert game.blue.budget > budget
    # The new ones are on the new front only.
    assert _titles(game) == [
        "Capture Tbilisi",
        "Blind the enemy air defences at Tbilisi",
        "Destroy the factory at Tbilisi",
        "Hold Kutaisi",
    ]


def test_a_target_just_used_waits_before_it_comes_back() -> None:
    game, parts = _theater(count=1)
    _top_up(game)
    capture = game.objectives.objectives[0]
    # Missed: the deadline passes without the base being taken.
    assert capture.deadline is not None
    game.turn = capture.deadline
    _end_turn(game)

    assert capture.state is ObjectiveState.MISSED
    assert "Capture Kutaisi" not in _titles(game)
    # Kutaisi waits: the next base on the front is the one to take.
    assert _titles(game) == ["Capture Senaki"]


def test_a_campaign_with_its_own_objectives_gets_none_generated() -> None:
    game, _ = _theater(count=4)
    game.objectives.generate = False
    _end_turn(game)
    assert game.objectives.objectives == []


def test_the_setting_turns_generation_off() -> None:
    game, _ = _theater(count=4)
    game.settings.generate_objectives = False
    _end_turn(game)
    assert game.objectives.objectives == []


def test_same_theater_same_objectives() -> None:
    first, _ = _theater()
    second, _ = _theater()
    _top_up(first)
    _top_up(second)
    assert _titles(first) == _titles(second)

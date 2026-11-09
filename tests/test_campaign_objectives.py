"""#194: optional campaign objectives, read from the campaign YAML.

They never decide the end of the campaign: a met objective only grants its
reward, capped so that a campaign cannot hand out too much.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterable, Iterator
from uuid import uuid4

import pytest

from game import objectives
from game.objectives import ObjectiveKind, ObjectiveState
from game.theater.player import Player

BLUE = Player.BLUE
RED = Player.RED


def _cp(
    name: str,
    owner: Player = RED,
    income: float = 100,
    fleet: bool = False,
    ground_objects: Iterable[Any] = (),
) -> Any:
    cp = SimpleNamespace(
        id=uuid4(),
        name=name,
        captured=owner,
        income_per_turn=income,
        is_fleet=fleet,
        ground_objects=[],
        operational=True,
    )
    cp.runway_is_operational = lambda: cp.operational
    for tgo in ground_objects:
        tgo.control_point = cp
        cp.ground_objects.append(tgo)
    return cp


def _tgo(
    original_name: str, category: str = "aa", iads: bool = True, ship: bool = False
) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        name=f"Random {original_name}",
        obj_name=f"Random {original_name}",
        original_name=original_name,
        category=category,
        is_iads=iads,
        sea_object=ship,
        is_dead=False,
        statics=[],
        control_point=None,
    )


class FakeSquadron:
    def __init__(self, name: str, room: int) -> None:
        self.name = name
        self.aircraft = SimpleNamespace(display_name="F/A-18C")
        self.owned_aircraft = 4
        self.room = room
        self.pilots = 0

    def room_for_aircraft(self) -> int:
        return self.room

    def add_pilots(self, count: int) -> None:
        self.pilots += count


class FakeCoalition:
    def __init__(self, player: Player, squadrons: Iterable[FakeSquadron] = ()):
        self.player = player
        self.budget = 1000.0
        self.air_wing = SimpleNamespace(iter_squadrons=lambda: iter(list(squadrons)))

    def adjust_budget(self, amount: float) -> None:
        self.budget += amount


class FakeTheater:
    def __init__(self, cps: list[Any]) -> None:
        self.controlpoints = cps

    def control_points_for(self, player: Player) -> Iterator[Any]:
        return (cp for cp in self.controlpoints if cp.captured is player)

    @property
    def ground_objects(self) -> Iterator[Any]:
        for cp in self.controlpoints:
            yield from cp.ground_objects


class FakeGame:
    def __init__(self, cps: list[Any], squadrons: Iterable[FakeSquadron] = ()) -> None:
        self.turn = 1
        self.theater = FakeTheater(cps)
        self.settings = SimpleNamespace(
            player_income_multiplier=1.0, enemy_income_multiplier=1.0
        )
        self.blue = FakeCoalition(BLUE, squadrons)
        self.red = FakeCoalition(RED)
        self.messages: list[tuple[str, str]] = []
        self.objectives = objectives.CampaignObjectives()

    def coalition_for(self, player: Player) -> FakeCoalition:
        return self.blue if player.is_blue else self.red

    def message(self, title: str, text: str = "") -> None:
        self.messages.append((title, text))


def _game(yaml: list[dict[str, Any]], **kwargs: Any) -> tuple[FakeGame, dict[str, Any]]:
    """Batumi (blue, 100/turn), Kutaisi and Senaki (red, 100/turn each)."""
    sam = _tgo("SAM-Kutaisi")
    ewr = _tgo("EWR-Senaki", category="ewr")
    depot = _tgo("Depot-Senaki", category="ammo", iads=False)
    batumi = _cp("Batumi", BLUE)
    kutaisi = _cp("Kutaisi", ground_objects=[sam])
    senaki = _cp("Senaki", ground_objects=[ewr, depot])
    carrier = _cp("CVN-74", BLUE, income=0, fleet=True)
    game = FakeGame([batumi, kutaisi, senaki, carrier], **kwargs)
    game.objectives = objectives.load(yaml, game)  # type: ignore[arg-type]
    parts = dict(
        batumi=batumi,
        kutaisi=kutaisi,
        senaki=senaki,
        carrier=carrier,
        sam=sam,
        ewr=ewr,
        depot=depot,
    )
    return game, parts


def _end_turns(game: FakeGame, count: int = 1) -> None:
    for _ in range(count):
        objectives.end_of_turn(game)  # type: ignore[arg-type]
        game.turn += 1


def _only(game: FakeGame) -> objectives.CampaignObjective:
    [objective] = game.objectives.objectives
    return objective


# --- loading -------------------------------------------------------------------


def test_a_campaign_without_objectives_has_none() -> None:
    game, _ = _game([])
    assert game.objectives.objectives == []
    _end_turns(game, 3)
    assert game.messages == []
    assert game.blue.budget == 1000


def test_objectives_are_read_from_the_yaml_and_bad_ones_are_dropped() -> None:
    game, parts = _game(
        [
            {"capture": "Kutaisi", "by_turn": 5, "title": "Take Kutaisi"},
            {"capture": "Nowhere"},  # no such base
            {"capture": "Batumi"},  # already ours
            {"hold": "Batumi"},  # a hold needs an until_turn
            {"teleport": "Kutaisi"},  # no such kind
        ]
    )
    [objective] = game.objectives.objectives
    assert objective.title == "Take Kutaisi"
    assert objective.kind is ObjectiveKind.CAPTURE
    assert objective.target == "Kutaisi"
    assert objective.deadline == 5
    assert objective.state is ObjectiveState.IN_PROGRESS


def test_an_objective_gets_a_title_when_the_campaign_gives_none() -> None:
    game, _ = _game([{"destroy": {"category": "iads"}}, {"capture": "Senaki"}])
    assert [o.title for o in game.objectives.objectives] == [
        "Destroy the enemy IADS",
        "Capture Senaki",
    ]


# --- capture ------------------------------------------------------------------


def test_a_capture_met_in_time_grants_its_budget() -> None:
    game, parts = _game(
        [{"capture": "Kutaisi", "by_turn": 3, "reward": {"budget": 150}}]
    )
    _end_turns(game)
    assert _only(game).state is ObjectiveState.IN_PROGRESS

    parts["kutaisi"].captured = BLUE
    _end_turns(game)

    objective = _only(game)
    assert objective.state is ObjectiveState.MET
    assert objective.resolved_turn == 2
    assert game.blue.budget == 1150
    assert game.messages == [("Objective met: Capture Kutaisi", "Reward: +150 budget")]


def test_a_capture_too_late_is_missed_without_penalty() -> None:
    game, parts = _game(
        [{"capture": "Kutaisi", "by_turn": 2, "reward": {"budget": 150}}]
    )
    _end_turns(game, 2)

    assert _only(game).state is ObjectiveState.MISSED
    assert game.messages == [("Objective missed: Capture Kutaisi", "")]
    parts["kutaisi"].captured = BLUE
    _end_turns(game)
    assert _only(game).state is ObjectiveState.MISSED
    assert game.blue.budget == 1000


def test_the_budget_reward_is_capped_at_two_turns_of_income() -> None:
    # Batumi and Kutaisi bring 200 a turn once Kutaisi is taken: at most 400.
    game, parts = _game([{"capture": "Kutaisi", "reward": {"budget": 99999}}])
    parts["kutaisi"].captured = BLUE
    _end_turns(game)
    assert game.blue.budget == 1400
    assert game.messages[0][1] == "Reward: +400 budget"


# --- hold and survive -----------------------------------------------------------


def test_a_base_held_until_the_turn_is_met() -> None:
    game, _ = _game([{"hold": "Batumi", "until_turn": 3}])
    _end_turns(game, 2)
    assert _only(game).state is ObjectiveState.IN_PROGRESS
    _end_turns(game)
    assert _only(game).state is ObjectiveState.MET
    assert game.messages == [("Objective met: Hold Batumi", "")]


def test_a_base_lost_before_the_turn_is_missed() -> None:
    game, parts = _game([{"hold": "Batumi", "until_turn": 3}])
    parts["batumi"].captured = RED
    _end_turns(game)
    assert _only(game).state is ObjectiveState.MISSED


def test_a_sunk_carrier_misses_its_survive_objective() -> None:
    game, parts = _game([{"survive": "CVN-74", "until_turn": 5}])
    assert _only(game).title == "Keep CVN-74 alive"
    _end_turns(game)
    parts["carrier"].operational = False
    _end_turns(game)
    assert _only(game).state is ObjectiveState.MISSED
    assert _only(game).resolved_turn == 2


# --- destroy --------------------------------------------------------------------


def test_destroying_a_category_counts_progress_until_every_site_is_gone() -> None:
    game, parts = _game([{"destroy": {"category": "iads"}, "by_turn": 4}])
    objective = _only(game)
    assert objectives.progress(objective, game) == objectives.Progress(  # type: ignore[arg-type]
        done=0, total=2, turns_left=4
    )

    parts["sam"].is_dead = True
    _end_turns(game)
    assert objectives.progress(objective, game) == objectives.Progress(  # type: ignore[arg-type]
        done=1, total=2, turns_left=3
    )

    # Taking the base takes the site out of the enemy's hands.
    parts["senaki"].captured = BLUE
    _end_turns(game)
    assert objective.state is ObjectiveState.MET


def test_a_named_ground_object_can_be_the_target_at_one_base() -> None:
    game, parts = _game(
        [
            {"destroy": "Depot-Senaki"},
            {"destroy": {"category": "aa", "at": "Kutaisi"}},
        ]
    )
    depot, sams = game.objectives.objectives
    assert depot.title == "Destroy Depot-Senaki"
    assert sams.title == "Destroy the enemy aa sites at Kutaisi"
    parts["depot"].is_dead = True
    _end_turns(game)
    assert depot.state is ObjectiveState.MET
    assert sams.state is ObjectiveState.IN_PROGRESS


# --- rewards --------------------------------------------------------------------


def _income(game: FakeGame, player: Player, turn: int) -> float:
    from game.income import Income

    return Income(game, player, turn).total  # type: ignore[arg-type]


def test_an_income_bonus_is_paid_for_its_turns_and_capped() -> None:
    # Batumi alone brings 100 a turn: an income bonus is at most 25 of it.
    game, _ = _game(
        [
            {
                "hold": "Batumi",
                "until_turn": 1,
                "reward": {"income": 80, "income_turns": 2},
            }
        ]
    )
    _end_turns(game)  # met at the end of turn 1, paid when the turn reads 2
    assert game.messages == [
        ("Objective met: Hold Batumi", "Reward: +25 income per turn for 2 turns")
    ]
    assert [_income(game, BLUE, turn) for turn in (2, 3, 4)] == [125, 125, 100]


def test_all_the_income_bonuses_together_are_capped_at_half_the_income() -> None:
    game, _ = _game(
        [
            {"hold": "Batumi", "until_turn": 1, "reward": {"income": 25}}
            for _ in range(3)
        ]
    )
    _end_turns(game)
    assert _income(game, BLUE, 2) == 150


def test_reinforcements_go_to_the_named_squadron_within_its_room() -> None:
    hornets = FakeSquadron("VF-11", room=2)
    game, _ = _game(
        [
            {
                "hold": "Batumi",
                "until_turn": 1,
                "reward": {"aircraft": 3, "pilots": 9, "squadron": "VF-11"},
            }
        ],
        squadrons=[hornets],
    )
    _end_turns(game)
    assert hornets.owned_aircraft == 6
    assert hornets.pilots == objectives.REINFORCEMENTS_CAP
    assert game.messages[0][1] == "Reward: 2 F/A-18C for VF-11, 4 pilots for VF-11"


def test_a_reward_for_a_squadron_needs_its_name() -> None:
    game, _ = _game([{"hold": "Batumi", "until_turn": 1, "reward": {"aircraft": 2}}])
    assert game.objectives.objectives == []


def test_the_enemy_loses_budget_and_income_within_the_caps() -> None:
    # The enemy brings 200 a turn (Kutaisi, Senaki): a cut is at most 400 of
    # budget and 50 of income.
    game, _ = _game(
        [
            {
                "hold": "Batumi",
                "until_turn": 1,
                "reward": {"enemy_budget": 1000, "enemy_income": 500},
            }
        ]
    )
    _end_turns(game)
    assert game.red.budget == 600
    assert _income(game, RED, 2) == 150
    assert game.messages[0][1] == (
        "Reward: -400 enemy budget, -50 enemy income per turn"
    )


def test_a_base_renamed_by_the_generation_is_found_by_its_miz_name() -> None:
    game, parts = _game([])
    carrier = parts["carrier"]
    miz_names = {carrier.id: "CVN-74"}
    carrier.name = "CVN-72 Abraham Lincoln"

    loaded = objectives.load(
        [{"survive": "CVN-74", "until_turn": 5}], game, miz_names  # type: ignore[arg-type]
    )

    [objective] = loaded.objectives
    assert objective.title == "Keep CVN-72 Abraham Lincoln alive"
    assert objective.target == "CVN-72 Abraham Lincoln"


def test_the_iads_are_the_land_sites_not_the_ships() -> None:
    game, parts = _game([])
    parts["senaki"].ground_objects.append(_tgo("Naval-2", "ship", ship=True))
    parts["senaki"].ground_objects[-1].control_point = parts["senaki"]

    loaded = objectives.load(
        [{"destroy": {"category": "iads"}}], game  # type: ignore[arg-type]
    )

    [objective] = loaded.objectives
    assert len(objective.ground_object_ids) == 2

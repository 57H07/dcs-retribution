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
from game.settings import Settings
from game.theater.player import Player

BLUE = Player.BLUE
RED = Player.RED


class FakeControlPoint:
    def __init__(
        self,
        name: str,
        owner: Player,
        income: float,
        fleet: bool,
        ground_objects: Iterable[Any],
    ) -> None:
        self.id = uuid4()
        self.name = name
        self.captured = owner
        self.income_per_turn = income
        self.is_fleet = fleet
        self.ground_objects: list[Any] = []
        self.connected_points: list[FakeControlPoint] = []
        self.operational = True
        self.position = None
        for tgo in ground_objects:
            tgo.control_point = self
            self.ground_objects.append(tgo)

    def runway_is_operational(self) -> bool:
        return self.operational

    @property
    def has_active_frontline(self) -> bool:
        return any(c.captured is not self.captured for c in self.connected_points)


def _cp(
    name: str,
    owner: Player = RED,
    income: float = 100,
    fleet: bool = False,
    ground_objects: Iterable[Any] = (),
) -> Any:
    return FakeControlPoint(name, owner, income, fleet, ground_objects)


def _connect(a: Any, b: Any) -> None:
    a.connected_points.append(b)
    b.connected_points.append(a)


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
        position=None,
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
        self.settings = Settings()
        self.blue = FakeCoalition(BLUE, squadrons)
        self.red = FakeCoalition(RED)
        self.messages: list[tuple[str, str]] = []
        self.objectives = objectives.CampaignObjectives()

    def coalition_for(self, player: Player) -> FakeCoalition:
        return self.blue if player.is_blue else self.red

    def message(self, title: str, text: str = "") -> None:
        self.messages.append((title, text))


def _game(yaml: list[dict[str, Any]], **kwargs: Any) -> tuple[FakeGame, dict[str, Any]]:
    """Batumi (blue, 100/turn) faces Kutaisi and Senaki (red, 100/turn each).

    Behind the front, without income: Kobuleti (blue) behind Batumi, Tbilisi
    (red) behind Kutaisi.
    """
    sam = _tgo("SAM-Kutaisi")
    ewr = _tgo("EWR-Senaki", category="ewr")
    depot = _tgo("Depot-Senaki", category="ammo", iads=False)
    rear_sam = _tgo("SAM-Tbilisi")
    factory = _tgo("Factory-Tbilisi", category="factory", iads=False)
    batumi = _cp("Batumi", BLUE)
    kutaisi = _cp("Kutaisi", ground_objects=[sam])
    senaki = _cp("Senaki", ground_objects=[ewr, depot])
    kobuleti = _cp("Kobuleti", BLUE, income=0)
    tbilisi = _cp("Tbilisi", income=0, ground_objects=[rear_sam, factory])
    carrier = _cp("CVN-74", BLUE, income=0, fleet=True)
    _connect(batumi, kutaisi)
    _connect(batumi, senaki)
    _connect(kobuleti, batumi)
    _connect(kutaisi, tbilisi)
    game = FakeGame([batumi, kutaisi, senaki, kobuleti, tbilisi, carrier], **kwargs)
    game.objectives = objectives.load(yaml, game)  # type: ignore[arg-type]
    parts = dict(
        batumi=batumi,
        kutaisi=kutaisi,
        senaki=senaki,
        kobuleti=kobuleti,
        tbilisi=tbilisi,
        carrier=carrier,
        sam=sam,
        rear_sam=rear_sam,
        factory=factory,
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
        "Destroy the enemy IADS near the front",
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
    assert hornets.pilots == 4
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


# --- near the front -------------------------------------------------------------


def test_objectives_behind_the_front_are_dropped() -> None:
    game, _ = _game(
        [
            {"capture": "Tbilisi"},  # behind Kutaisi
            {"hold": "Kobuleti", "until_turn": 3},  # behind Batumi
            {"destroy": "Factory-Tbilisi"},
            {"destroy": {"category": "factory", "at": "Tbilisi"}},
            {"survive": "CVN-74", "until_turn": 3},  # a fleet sails to the fight
            {"capture": "Kutaisi"},
        ]
    )
    assert [o.title for o in game.objectives.objectives] == [
        "Keep CVN-74 alive",
        "Capture Kutaisi",
    ]


def test_a_category_counts_only_the_sites_near_the_front() -> None:
    game, parts = _game([{"destroy": {"category": "aa"}}])
    assert _only(game).ground_object_ids == [parts["sam"].id]


# --- reward settings ------------------------------------------------------------


def _met_hold(reward: dict[str, Any], **kwargs: Any) -> FakeGame:
    game, _ = _game([{"hold": "Batumi", "until_turn": 1, "reward": reward}], **kwargs)
    return game


def test_rewards_can_be_turned_off() -> None:
    game = _met_hold({"budget": 100, "income": 20})
    game.settings.objective_rewards = False
    _end_turns(game)
    assert _only(game).state is ObjectiveState.MET
    assert game.messages == [("Objective met: Hold Batumi", "")]
    assert game.blue.budget == 1000
    assert _income(game, BLUE, 2) == 100


def test_turning_rewards_off_stops_the_bonuses_already_granted() -> None:
    game = _met_hold({"income": 20, "enemy_income": 40})
    _end_turns(game)
    assert (_income(game, BLUE, 2), _income(game, RED, 2)) == (120, 160)
    game.settings.objective_income_rewards = False
    game.settings.objective_enemy_penalties = False
    assert (_income(game, BLUE, 2), _income(game, RED, 2)) == (100, 200)


def test_the_reward_scale_multiplies_what_the_campaign_promises() -> None:
    game = _met_hold(
        {"budget": 100, "aircraft": 4, "squadron": "VF-11"},
        squadrons=[FakeSquadron("VF-11", room=8)],
    )
    game.settings.objective_reward_scale = 0.5
    _end_turns(game)
    assert game.blue.budget == 1050
    assert game.messages[0][1] == "Reward: +50 budget, 2 F/A-18C for VF-11"


def test_each_kind_of_reward_can_be_turned_off() -> None:
    hornets = FakeSquadron("VF-11", room=8)
    game = _met_hold(
        {
            "budget": 100,
            "income": 20,
            "aircraft": 2,
            "pilots": 2,
            "squadron": "VF-11",
            "enemy_budget": 100,
        },
        squadrons=[hornets],
    )
    game.settings.objective_budget_rewards = False
    game.settings.objective_reinforcement_rewards = False
    game.settings.objective_enemy_penalties = False
    _end_turns(game)
    assert game.messages[0][1] == "Reward: +20 income per turn"
    assert (game.blue.budget, game.red.budget) == (1000, 1000)
    assert (hornets.owned_aircraft, hornets.pilots) == (4, 0)


def test_the_caps_are_settings() -> None:
    hornets = FakeSquadron("VF-11", room=8)
    game = _met_hold(
        {"budget": 1000, "income": 80, "pilots": 9, "squadron": "VF-11"},
        squadrons=[hornets],
    )
    game.settings.objective_budget_cap_turns = 1.0
    game.settings.objective_income_cap = 10
    game.settings.objective_reinforcements_cap = 2
    _end_turns(game)
    assert game.messages[0][1] == (
        "Reward: +100 budget, +10 income per turn, 2 pilots for VF-11"
    )


def test_the_total_income_cap_is_a_setting() -> None:
    game, _ = _game(
        [
            {"hold": "Batumi", "until_turn": 1, "reward": {"income": 25}}
            for _ in range(3)
        ]
    )
    game.settings.objective_total_income_cap = 30
    _end_turns(game)
    assert _income(game, BLUE, 2) == 130


def test_an_objective_in_progress_tells_what_it_would_grant_today() -> None:
    game, _ = _game([{"capture": "Kutaisi", "reward": {"budget": 1000, "income": 10}}])
    game.settings.objective_reward_scale = 0.5
    # Batumi brings 100 a turn: 500 of budget is capped at 200.
    assert objectives.expected_reward(_only(game), game) == (  # type: ignore[arg-type]
        "+200 budget, +5 income per turn"
    )


# --- targets on the map and in the planner ------------------------------------------


def test_an_objective_lists_its_targets_and_which_still_stand() -> None:
    game, parts = _game(
        [{"destroy": {"category": "iads"}}, {"capture": "Kutaisi"}],
    )
    iads, capture = game.objectives.objectives
    parts["sam"].is_dead = True

    assert [
        (t.id, t.name, t.remaining) for t in objectives.targets(iads, game)  # type: ignore[arg-type]
    ] == [
        (parts["sam"].id, "Random SAM-Kutaisi", False),
        (parts["ewr"].id, "Random EWR-Senaki", True),
    ]
    [base] = objectives.targets(capture, game)  # type: ignore[arg-type]
    assert (base.id, base.name, base.remaining) == (
        parts["kutaisi"].id,
        "Kutaisi",
        True,
    )


def test_the_objectives_in_progress_aimed_at_a_target() -> None:
    game, parts = _game(
        [
            {"destroy": {"category": "iads"}, "title": "Blind them"},
            {"capture": "Kutaisi"},
            {"capture": "Senaki", "by_turn": 1},
        ]
    )
    _end_turns(game)  # Senaki is missed

    def titles(target: Any) -> list[str]:
        return [o.title for o in objectives.aimed_at(game, target.id)]  # type: ignore[arg-type]

    assert titles(parts["sam"]) == ["Blind them"]
    assert titles(parts["kutaisi"]) == ["Capture Kutaisi"]
    assert titles(parts["senaki"]) == []
    assert titles(parts["depot"]) == []

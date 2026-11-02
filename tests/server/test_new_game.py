"""WEB-06: the new campaign wizard, on real campaigns."""

from __future__ import annotations

import random
import threading
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote

import pytest

from game import Game, liberation_install
from game.commands import CommandError
from game.commands.newgame import (
    FactionChoice,
    GenerationStatus,
    NewGameGeneration,
    cli_parameters,
    create_game,
    customized_faction,
    find_campaign,
    starting_settings,
)
from game.data.doctrine import ALL_DOCTRINES
from game.dcs.aircrafttype import AircraftType
from game.factions import FACTIONS
from game.gamelock import _GAME_LOCK
from game.naming import NameGenerator
from game.native import NativeContext
from game.server import GameContext
from game.server.newgame.routes import NewGameContext
from tests.flightplans.referencegame import (
    BLUE_FACTION,
    REFERENCE_CAMPAIGN,
    RED_FACTION,
    START_DATE,
    repository_payloads_only,
)
from tests.server.test_air_wing import _request
from tests.server.test_native_routes import FakeBridge

SEED = 2026
CAMPAIGN_ID = REFERENCE_CAMPAIGN.stem


def fingerprint(game: Game) -> dict[str, Any]:
    """What makes two campaigns the same, without the random ids."""

    def side(coalition: Any) -> dict[str, Any]:
        return {
            "faction": coalition.faction.name,
            "budget": coalition.budget,
            "squadrons": sorted(
                (
                    s.name,
                    s.nickname,
                    s.aircraft.variant_id,
                    s.location.name,
                    s.owned_aircraft,
                    s.max_size,
                    s.primary_task.value,
                    sorted(t.value for t in s.auto_assignable_mission_types),
                    sorted(p.name for p in s.pilot_pool + s.active_pilots),
                )
                for s in coalition.air_wing.iter_squadrons()
            ),
            "orders": sorted(str(r) for r in coalition.procurement_requests),
        }

    settings = {
        key: value for key, value in game.settings.__dict__.items() if key != "version"
    }
    return {
        "turn": game.turn,
        "date": game.date,
        "campaign": game.campaign_name,
        "conditions": str(game.conditions.start_time),
        "settings": settings,
        "blue": side(game.blue),
        "red": side(game.red),
        "bases": sorted(
            (cp.name, str(cp.captured), cp.base.total_armor)
            for cp in game.theater.controlpoints
        ),
        "ground_objects": sorted(
            (
                tgo.name,
                tgo.category,
                round(tgo.position.x, 3),
                round(tgo.position.y, 3),
                str(tgo.control_point.captured),
                sorted(unit.name for unit in tgo.units),
            )
            for tgo in game.theater.ground_objects
        ),
    }


def _cli_game() -> Game:
    return create_game(_cli_parameters())


def _cli_parameters() -> Any:
    return cli_parameters(
        REFERENCE_CAMPAIGN,
        BLUE_FACTION,
        RED_FACTION,
        supercarrier=False,
        auto_procurement=True,
        inverted=False,
        cheats=True,
        start_date=START_DATE,
        restrict_weapons_by_date=True,
        advanced_iads=False,
        use_new_squadron_rules=True,
        squadrons_start_full=True,
        seed=SEED,
    )


#: The request of the web wizard for the same flags as `_cli_parameters`.
WEB_REQUEST: dict[str, Any] = {
    "campaign_id": CAMPAIGN_ID,
    "blue": {"name": BLUE_FACTION},
    "red": {"name": RED_FACTION},
    "start_date": START_DATE.date().isoformat(),
    "player_budget": 2000,
    "enemy_budget": 2000,
    "squadrons_start_full": True,
    "seed": SEED,
    "settings": {
        "supercarrier": False,
        "automate_runway_repair": True,
        "automate_front_line_reinforcements": True,
        "automate_aircraft_reinforcements": True,
        "automate_building_repairs": True,
        "automate_ground_object_repairs": True,
        "enable_frontline_cheats": True,
        "enable_base_capture_cheat": True,
        "enable_transfer_cheat": True,
        "restrict_weapons_by_date": True,
        "enable_squadron_aircraft_limits": True,
    },
}


@pytest.fixture(scope="module", autouse=True)
def _payloads(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    missing = Path(tmp_path_factory.mktemp("payloads")) / "none"
    with repository_payloads_only(missing):
        yield


class CreatedBridge(FakeBridge):
    def __init__(self) -> None:
        super().__init__()
        self.created: list[Game] = []

    def game_created(self, game: Game) -> None:
        self.created.append(game)


@pytest.fixture
def bridge(monkeypatch: pytest.MonkeyPatch) -> CreatedBridge:
    fake = CreatedBridge()
    monkeypatch.setattr(NativeContext, "_bridge", fake)
    return fake


@pytest.fixture(autouse=True)
def _generation(monkeypatch: pytest.MonkeyPatch) -> Iterator[NewGameGeneration]:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    generation = NewGameGeneration()
    NewGameContext.set(generation)
    yield generation
    generation.join()
    NewGameContext.set(None)


def _generate(generation: NewGameGeneration, request: dict[str, Any]) -> None:
    status, body = _request("POST", "/new-game/generation", request)
    assert status == 200, body
    generation.join()
    assert (
        generation.snapshot().status is GenerationStatus.CONFIGURING
    ), generation.snapshot().error


# --- Acceptance ----------------------------------------------------------------


def test_a_web_campaign_equals_a_cli_one(
    _generation: NewGameGeneration, bridge: CreatedBridge
) -> None:
    expected = fingerprint(_cli_game())

    _generate(_generation, WEB_REQUEST)
    status, body = _request("POST", "/new-game/generation/begin")
    assert status == 200, body
    _generation.join()
    assert _generation.snapshot().status is GenerationStatus.DONE

    assert len(bridge.created) == 1
    assert fingerprint(bridge.created[0]) == expected


def test_looking_at_the_air_wing_does_not_change_the_campaign(
    _generation: NewGameGeneration, bridge: CreatedBridge
) -> None:
    """What the screens do between generation and turn 0 leaves the seed's result."""
    expected = fingerprint(_cli_game())
    _generate(_generation, WEB_REQUEST)
    status, _ = _request("GET", "/air-wing-config/draft")
    assert status == 200
    random.random()
    _request("POST", "/new-game/generation/begin")
    _generation.join()
    assert fingerprint(bridge.created[0]) == expected


def test_another_seed_makes_another_campaign() -> None:
    first = _cli_parameters()
    second = _cli_parameters()
    second.seed = SEED + 1
    assert fingerprint(create_game(first)) != fingerprint(create_game(second))


# --- Generation ----------------------------------------------------------------


def test_generation_answers_at_once_and_never_holds_the_game_lock(
    _generation: NewGameGeneration, bridge: CreatedBridge
) -> None:
    free_during_steps: list[bool] = []
    steps: list[str] = []
    done = threading.Event()

    def try_lock() -> bool:
        result: list[bool] = []

        def attempt() -> None:
            acquired = _GAME_LOCK.acquire(blocking=False)
            if acquired:
                _GAME_LOCK.release()
            result.append(acquired)

        thread = threading.Thread(target=attempt)
        thread.start()
        thread.join()
        return result[0]

    def on_change() -> None:
        snapshot = _generation.snapshot()
        if snapshot.step is not None and snapshot.step not in steps:
            steps.append(snapshot.step)
            free_during_steps.append(try_lock())
        if snapshot.status is GenerationStatus.DONE:
            done.set()

    _generation._on_change = on_change
    _generate(_generation, WEB_REQUEST)
    assert steps == ["Loading the theater", "Generating the campaign"]
    _request("POST", "/new-game/generation/begin")
    assert done.wait(60)
    assert steps[-1] == "Starting turn 0"
    assert all(free_during_steps)


def test_a_second_generation_is_refused(_generation: NewGameGeneration) -> None:
    _generate(_generation, WEB_REQUEST)
    status, body = _request("POST", "/new-game/generation", WEB_REQUEST)
    assert status == 409
    assert "already" in body["detail"]


def test_cancel_drops_the_draft_and_gives_the_names_back(
    _generation: NewGameGeneration,
) -> None:
    NameGenerator.number = 4242
    _generate(_generation, WEB_REQUEST)
    assert NameGenerator.number != 4242
    status, body = _request("DELETE", "/new-game/generation")
    assert status == 200
    assert body["status"] == "idle"
    assert NameGenerator.number == 4242
    NameGenerator.reset()
    status, _ = _request("GET", "/air-wing-config/draft")
    assert status == 409


def test_a_failure_is_reported_and_can_be_retried(
    _generation: NewGameGeneration, monkeypatch: pytest.MonkeyPatch
) -> None:
    import game.commands.newgame as newgame

    def explode(*_: Any, **__: Any) -> Game:
        raise RuntimeError("broken miz")

    monkeypatch.setattr(newgame, "generate_new_game", explode)
    status, _ = _request("POST", "/new-game/generation", WEB_REQUEST)
    assert status == 200
    _generation.join()
    status, body = _request("GET", "/new-game/generation")
    assert body["status"] == "failed"
    assert "broken miz" in body["error"]
    monkeypatch.undo()
    NewGameContext.set(_generation)
    status, _ = _request("POST", "/new-game/generation", WEB_REQUEST)
    assert status == 200
    _generation.join()


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"campaign_id": "nope"}, 404),
        ({"blue": {"name": "nope"}}, 404),
        ({"settings": {"nope": True}}, 404),
        ({"settings": {"supercarrier": "yes"}}, 422),
        ({"mods": ["nope"]}, 409),
        ({"player_budget": -1}, 422),
    ],
)
def test_refused_parameters(change: dict[str, Any], expected: int) -> None:
    status, _ = _request("POST", "/new-game/generation", {**WEB_REQUEST, **change})
    assert status == expected


def test_begin_needs_a_draft(bridge: CreatedBridge) -> None:
    status, _ = _request("POST", "/new-game/generation/begin")
    assert status == 409


# --- What the wizard offers ----------------------------------------------------


def test_options_list_real_campaigns() -> None:
    status, body = _request("GET", "/new-game/options")
    assert status == 200
    names = {campaign["id"]: campaign for campaign in body["campaigns"]}
    golan = names[CAMPAIGN_ID]
    assert golan["theater"]
    assert golan["description"]
    assert golan["performance_label"]
    assert BLUE_FACTION in body["factions"]
    assert body["default_time_period"] in {p["name"] for p in body["time_periods"]}
    assert {"key": "uh_60l", "label": "UH-60L Black Hawk (v2.1.5)"} in body["mods"]


def test_every_mod_choice_is_a_mod_setting() -> None:
    from dataclasses import fields

    from game.commands.newgame import MOD_CHOICES
    from game.theater.start_generator import ModSettings

    assert {key for key, _ in MOD_CHOICES} == {f.name for f in fields(ModSettings)}


def test_preview_counts_bases_and_front_lines() -> None:
    status, body = _request("GET", f"/new-game/campaigns/{CAMPAIGN_ID}/preview")
    assert status == 200
    assert body["blue_bases"] > 0 and body["red_bases"] > 0
    assert body["front_lines"] >= 1
    south_west, north_east = body["south_west"], body["north_east"]
    for base in body["bases"]:
        assert south_west["lat"] <= base["position"]["lat"] <= north_east["lat"]
        assert south_west["lng"] <= base["position"]["lng"] <= north_east["lng"]
    assert sum(link["front_line"] for link in body["links"]) == body["front_lines"]
    status, _ = _request("GET", "/new-game/campaigns/nope/preview")
    assert status == 404


def test_defaults_recommend_the_campaign_values() -> None:
    campaign = find_campaign(CAMPAIGN_ID)
    status, body = _request("GET", f"/new-game/campaigns/{CAMPAIGN_ID}/defaults")
    assert status == 200
    assert body["blue_faction"] == campaign.recommended_player_faction
    assert body["red_faction"] == campaign.recommended_enemy_faction
    assert body["player_budget"] == campaign.recommended_player_money
    assert (body["start_date"] is None) == (body["time_period"] is not None)
    keys = {
        setting["key"]
        for page in body["settings_pages"]
        for section in page["sections"]
        for setting in section["settings"]
    }
    assert "supercarrier" in keys


def test_campaign_settings_and_income_are_part_of_the_start() -> None:
    campaign = find_campaign("IntotheHornetsNest")
    settings = starting_settings(campaign)
    assert settings.max_frontline_width == 30
    assert settings.player_income_multiplier == (
        campaign.recommended_player_income_multiplier
    )


def test_faction_sheet_has_units_and_addable_units() -> None:
    status, body = _request("GET", f"/new-game/faction?name={quote(BLUE_FACTION)}")
    assert status == 200
    groups = {group["key"]: group for group in body["groups"]}
    assert groups["aircraft"]["units"]
    assert not set(groups["aircraft"]["units"]) & set(groups["aircraft"]["addable"])
    assert body["doctrine"] in body["doctrines"]
    status, _ = _request("GET", "/new-game/faction?name=nope")
    assert status == 404


def test_customized_faction_leaves_the_original_alone() -> None:
    original = FACTIONS[BLUE_FACTION]
    before = set(original.aircraft)
    removed = sorted(str(a) for a in before)[0]
    status, sheet = _request("GET", f"/new-game/faction?name={quote(BLUE_FACTION)}")
    added = next(g for g in sheet["groups"] if g["key"] == "aircraft")["addable"][0]
    faction = customized_faction(
        FactionChoice(
            BLUE_FACTION,
            removed={"aircraft": [removed]},
            added={"aircraft": [added]},
            has_jtac=not original.has_jtac,
            doctrine=ALL_DOCTRINES[-1].name,
        )
    )
    names = {str(a) for a in faction.aircraft}
    assert removed not in names and added in names
    assert faction.has_jtac is not original.has_jtac
    assert faction.doctrine.name == ALL_DOCTRINES[-1].name
    assert original.aircraft == before
    assert faction.all_aircrafts is not None and removed not in {
        str(a) for a in faction.all_aircrafts
    }


def test_customized_faction_refuses_an_unknown_unit() -> None:
    with pytest.raises(CommandError):
        customized_faction(FactionChoice(BLUE_FACTION, added={"aircraft": ["nope"]}))


def test_saving_a_faction_needs_a_new_usable_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from game import persistency

    monkeypatch.setattr(persistency, "factions_dir", lambda: tmp_path)
    body: dict[str, Any] = {"faction": {"name": BLUE_FACTION}, "name": BLUE_FACTION}
    assert _request("POST", "/new-game/factions", body)[0] == 409
    assert _request("POST", "/new-game/factions", {**body, "name": "a/b"})[0] == 409
    status, answer = _request("POST", "/new-game/factions", {**body, "name": "Probe"})
    try:
        assert status == 204, answer
        assert (tmp_path / "Probe.json").exists()
        assert "Probe" in FACTIONS.factions
    finally:
        FACTIONS.factions.pop("Probe", None)


# --- Air wing configuration of the draft ---------------------------------------


@pytest.fixture
def draft(_generation: NewGameGeneration) -> Game:
    _generate(_generation, WEB_REQUEST)
    game = _generation.draft()
    assert game is not None
    return game


def _blue_side() -> dict[str, Any]:
    status, body = _request("GET", "/air-wing-config/draft")
    assert status == 200, body
    assert body["replans"] is False
    return next(side for side in body["sides"] if side["side"] == "blue")


def test_draft_squadron_can_be_edited(draft: Game) -> None:
    squadron = next(
        s for s in _blue_side()["squadrons"] if s["player_names_refusal"] is None
    )
    other_task = next(
        (t for t in squadron["primary_tasks"] if t != squadron["primary_task"]),
        squadron["primary_task"],
    )
    path = f"/air-wing-config/draft/squadrons/{squadron['id']}"
    status, body = _request(
        "PATCH",
        path,
        {
            "name": "Renamed",
            "nickname": "Bees",
            "max_size": 7,
            "primary_task": other_task,
            "player_names": ["Maverick", "Goose"],
        },
    )
    assert status == 204, body
    edited = next(s for s in _blue_side()["squadrons"] if s["id"] == squadron["id"])
    assert edited["name"] == "Renamed"
    assert edited["nickname"] == "Bees"
    assert edited["max_size"] == 7
    assert edited["primary_task"] == other_task
    assert edited["player_names"] == ["Maverick", "Goose"]

    assert _request("PATCH", path, {"name": "  "})[0] == 409
    assert _request("PATCH", path, {"max_size": 0})[0] == 409
    no_slots = next(
        (s for s in _blue_side()["squadrons"] if s["player_names_refusal"]), None
    )
    if no_slots is not None:
        refused = f"/air-wing-config/draft/squadrons/{no_slots['id']}"
        assert _request("PATCH", refused, {"player_names": ["Goose"]})[0] == 409
    assert _request("POST", f"{path}/reroll-nickname")[0] == 204


def test_draft_squadron_can_move_only_to_a_possible_base(draft: Game) -> None:
    squadron = next(s for s in _blue_side()["squadrons"] if len(s["bases"]) > 1)
    target = next(b for b in squadron["bases"] if b["id"] != squadron["base_id"])
    path = f"/air-wing-config/draft/squadrons/{squadron['id']}"
    assert _request("PATCH", path, {"base_id": target["id"]})[0] == 204
    moved = next(s for s in _blue_side()["squadrons"] if s["id"] == squadron["id"])
    assert moved["base_id"] == target["id"]
    enemy = next(iter(draft.theater.control_points_for(draft.red.player)))
    assert _request("PATCH", path, {"base_id": str(enemy.id)})[0] == 409


def test_add_squadron_lists_the_players_modules_first(
    draft: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    options = _blue_side()["aircraft_options"]
    assert not any(o["player_module"] for o in options)
    flyable = [o for o in options if AircraftType.named(o["aircraft_id"]).flyable]
    chosen = flyable[-1]
    module = AircraftType.named(chosen["aircraft_id"]).dcs_unit_type.id
    monkeypatch.setattr(liberation_install, "owned_modules", lambda: [module])

    side = _blue_side()

    assert side["aircraft_options"][0]["aircraft_id"] == chosen["aircraft_id"]
    assert side["aircraft_options"][0]["player_module"] is True


def test_add_squadron_counts_the_squadrons_of_each_aircraft(draft: Game) -> None:
    side = _blue_side()
    for option in side["aircraft_options"]:
        assert option["squadron_count"] == sum(
            s["aircraft"] == option["aircraft"] for s in side["squadrons"]
        )
    option = side["aircraft_options"][0]
    status, _ = _request(
        "POST",
        "/air-wing-config/draft/sides/blue/squadrons",
        {
            "aircraft_id": option["aircraft_id"],
            "base_id": option["bases"][0]["id"],
            "primary_task": option["primary_tasks"][0],
        },
    )
    assert status == 204
    again = next(
        o
        for o in _blue_side()["aircraft_options"]
        if o["aircraft_id"] == option["aircraft_id"]
    )
    assert again["squadron_count"] == option["squadron_count"] + 1


def test_draft_squadrons_can_be_added_and_removed(draft: Game) -> None:
    side = _blue_side()
    option = side["aircraft_options"][0]
    count = len(side["squadrons"])
    status, body = _request(
        "POST",
        "/air-wing-config/draft/sides/blue/squadrons",
        {
            "aircraft_id": option["aircraft_id"],
            "base_id": option["bases"][0]["id"],
            "primary_task": option["primary_tasks"][0],
        },
    )
    assert status == 204, body
    side = _blue_side()
    assert len(side["squadrons"]) == count + 1
    victim = side["squadrons"][0]
    status, _ = _request("DELETE", f"/air-wing-config/draft/squadrons/{victim['id']}")
    assert status == 204
    assert len(_blue_side()["squadrons"]) == count


def test_draft_squadron_can_be_replaced_with_a_preset(draft: Game) -> None:
    squadron = next((s for s in _blue_side()["squadrons"] if s["presets"]), None)
    if squadron is None:
        pytest.skip("The reference campaign leaves no preset free.")
    preset = squadron["presets"][0]
    path = f"/air-wing-config/draft/squadrons/{squadron['id']}/preset"
    assert _request("POST", path, {"preset": preset})[0] == 204
    assert preset in {s["name"] for s in _blue_side()["squadrons"]}
    assert _request("POST", path, {"preset": "nope"})[0] == 404


def test_draft_auto_assign_and_livery(draft: Game) -> None:
    squadron = _blue_side()["squadrons"][0]
    base = f"/air-wing-config/draft/squadrons/{squadron['id']}"
    task = squadron["tasks"][0]
    status, _ = _request(
        "PUT",
        f"{base}/auto-assign",
        {"task": task["task"], "enabled": not task["auto_assign"]},
    )
    assert status == 204
    status, liveries = _request("GET", f"{base}/liveries")
    assert status == 200
    if liveries:
        choice = liveries[0]
        status, _ = _request(
            "PUT",
            f"{base}/livery",
            {
                "livery_id": choice["livery_id"],
                "use_livery_set": choice["use_livery_set"],
            },
        )
        assert status == 204


def test_air_wing_file_round_trip(
    draft: Game, bridge: CreatedBridge, tmp_path: Path
) -> None:
    path = tmp_path / "wing.yaml"
    bridge.answer = str(path)
    before = len(_blue_side()["squadrons"])
    status, body = _request("POST", "/air-wing-config/draft/sides/blue/file/save")
    assert status == 200, body
    assert body["path"] == str(path)
    assert path.exists()
    status, body = _request("POST", "/air-wing-config/draft/sides/blue/file/load")
    assert status == 200, body
    assert len(_blue_side()["squadrons"]) == before

    path.write_text("{}: [", encoding="utf-8")
    status, _ = _request("POST", "/air-wing-config/draft/sides/blue/file/load")
    assert status == 409

    bridge.answer = None
    status, body = _request("POST", "/air-wing-config/draft/sides/blue/file/save")
    assert status == 200
    assert body["path"] is None


def test_draft_faction_tab(draft: Game) -> None:
    status, sheet = _request("GET", "/air-wing-config/draft/sides/red/faction")
    assert status == 200
    group = next(g for g in sheet["groups"] if g["key"] == "preset_groups")
    assert group["addable"]
    unit = group["addable"][0]
    forces = draft.red.armed_forces
    status, _ = _request(
        "POST",
        "/air-wing-config/draft/sides/red/faction/units",
        {"group": "preset_groups", "unit": unit},
    )
    assert status == 204
    assert draft.red.armed_forces is not forces
    assert unit in {str(p) for p in draft.red.faction.preset_groups}
    assert (
        _request(
            "POST",
            "/air-wing-config/draft/sides/red/faction/units",
            {"group": "aircraft", "unit": "nope"},
        )[0]
        == 409
    )

    assert (
        _request(
            "PUT", "/air-wing-config/draft/sides/red/faction/jtac", {"has_jtac": True}
        )[0]
        == 204
    )
    assert draft.red.faction.has_jtac is True
    doctrine = sheet["doctrines"][0]
    assert (
        _request(
            "PUT",
            "/air-wing-config/draft/sides/red/faction/doctrine",
            {"doctrine": doctrine},
        )[0]
        == 204
    )
    assert draft.red.faction.doctrine.name == doctrine
    assert (
        _request(
            "PUT",
            "/air-wing-config/draft/sides/red/faction/doctrine",
            {"doctrine": "x"},
        )[0]
        == 409
    )


# --- In the campaign in play ---------------------------------------------------


@pytest.fixture(scope="module")
def running_game() -> Game:
    game = create_game(_cli_parameters())
    game.pass_turn(no_action=True)
    return game


def test_campaign_target_needs_the_cheat(
    running_game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=running_game), raising=False
    )
    running_game.settings.enable_air_wing_adjustments = False
    status, body = _request("GET", "/air-wing-config/campaign")
    assert status == 409
    assert "Air Wing adjustments" in body["detail"]
    status, wing = _request("GET", "/air-wing")
    assert wing["adjustments_enabled"] is False


def test_campaign_changes_replan_the_turn(
    running_game: Game, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=running_game), raising=False
    )
    running_game.settings.enable_air_wing_adjustments = True
    status, wing = _request("GET", "/air-wing")
    assert wing["adjustments_enabled"] is True
    status, config = _request("GET", "/air-wing-config/campaign")
    assert status == 200
    assert config["replans"] is True

    replans: list[bool] = []
    original = type(running_game.blue).initialize_turn

    def spy(self: Any, is_turn_0: bool) -> None:
        replans.append(is_turn_0)
        original(self, is_turn_0)

    monkeypatch.setattr(type(running_game.blue), "initialize_turn", spy)
    blue = next(side for side in config["sides"] if side["side"] == "blue")
    victim = blue["squadrons"][-1]
    path = f"/air-wing-config/campaign/squadrons/{victim['id']}"

    assert _request("PATCH", path, {"nickname": "Bees"})[0] == 204
    assert replans == []

    assert _request("DELETE", path)[0] == 204
    assert replans == [False]
    assert all(
        flight.squadron.id != victim["id"]
        for package in running_game.blue.ato.packages
        for flight in package.flights
    )

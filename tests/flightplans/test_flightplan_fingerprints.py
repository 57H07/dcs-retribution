"""Flight-plan non-regression harness (WEB-04.0, decision W16).

Plans a fixed set of packages on a deterministic reference game and compares a
fingerprint of their flight plans (waypoints, times, loadouts) with the JSON
references in ``tests/data/flightplans/``. See ``README.md`` in this folder.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from game import Game, persistency
from game.ato import Package
from game.data.weapons import Weapon
from game.server.flightroute.models import FlightRouteJs
from tests.flightplans.fingerprint import compare_to_reference, fingerprint_package
from tests.flightplans.runner import FINGERPRINTS_FILE, SAVE_FILE
from tests.flightplans.scenarios import scenario_names

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Faction units are sets of objects hashed by name, so generation depends on the
#: hash seed. It cannot change in a running process, so a child process pins it.
HASH_SEED = "0"


@dataclass(frozen=True)
class ReferenceRun:
    fingerprints: dict[str, dict[str, Any]]
    game: Game

    def package(self, scenario: str) -> Package:
        return dict(zip(scenario_names(), self.game.blue.ato.packages))[scenario]


@pytest.fixture(scope="module")
def reference_run(tmp_path_factory: pytest.TempPathFactory) -> ReferenceRun:
    output = tmp_path_factory.mktemp("flightplans")
    env = dict(os.environ, PYTHONHASHSEED=HASH_SEED)
    result = subprocess.run(
        [sys.executable, "-m", "tests.flightplans.runner", str(output)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if result.returncode != 0:
        pytest.fail(
            "Reference planning failed:\n" + result.stderr[-4000:], pytrace=False
        )
    fingerprints = json.loads((output / FINGERPRINTS_FILE).read_text(encoding="utf-8"))
    game = persistency.load_game(str(output / SAVE_FILE))
    assert game is not None
    return ReferenceRun(fingerprints, game)


@pytest.mark.parametrize("scenario", scenario_names())
def test_flight_plans_match_reference(
    reference_run: ReferenceRun, scenario: str
) -> None:
    diff = compare_to_reference(scenario, reference_run.fingerprints[scenario])
    if diff is not None:
        pytest.fail(diff, pytrace=False)


def test_every_scenario_is_planned(reference_run: ReferenceRun) -> None:
    assert list(reference_run.fingerprints) == scenario_names()
    assert len(reference_run.game.blue.ato.packages) == len(scenario_names())
    for name, fingerprint in reference_run.fingerprints.items():
        assert fingerprint["flights"], name
        for flight in fingerprint["flights"]:
            assert flight["waypoints"], f"{name}: {flight['task']}"


def test_saved_game_gives_the_same_fingerprints(reference_run: ReferenceRun) -> None:
    """The planned flight plans survive a save/load in another process."""
    for scenario in scenario_names():
        assert (
            fingerprint_package(reference_run.package(scenario))
            == reference_run.fingerprints[scenario]
        ), scenario


def test_reading_a_route_changes_no_fingerprint(reference_run: ReferenceRun) -> None:
    """The Route tab tries the rules of a layout on a copy (WEB-04.4)."""
    game = reference_run.game
    for scenario in scenario_names():
        package = reference_run.package(scenario)
        for flight in package.flights:
            FlightRouteJs.for_flight(game, flight)
        assert fingerprint_package(package) == reference_run.fingerprints[scenario]


# The harness must catch a change of waypoint, time or loadout. Each check
# mutates the loaded game, verifies the fingerprint differs, then restores it.


def test_fingerprint_catches_a_moved_waypoint(reference_run: ReferenceRun) -> None:
    package = reference_run.package("strike_escort")
    before = fingerprint_package(package)
    waypoint = package.flights[0].flight_plan.waypoints[1]
    original = waypoint.position
    waypoint.position = original.point_from_heading(90, 500)
    try:
        assert fingerprint_package(package) != before
    finally:
        waypoint.position = original
    assert fingerprint_package(package) == before


def test_fingerprint_catches_a_time_change(reference_run: ReferenceRun) -> None:
    package = reference_run.package("sead")
    before = fingerprint_package(package)
    original = package.time_over_target
    package.time_over_target = original + timedelta(minutes=1)
    try:
        assert fingerprint_package(package) != before
    finally:
        package.time_over_target = original
    assert fingerprint_package(package) == before


def test_fingerprint_catches_a_loadout_change(reference_run: ReferenceRun) -> None:
    package = reference_run.package("dead")
    before = fingerprint_package(package)
    loadout = package.flights[0].roster.members[0].loadout
    original = dict(loadout.pylons)
    pylon = next(p for p, w in sorted(original.items()) if w is not None)
    loadout.pylons[pylon] = Weapon.with_clsid("<CLEAN>")
    try:
        assert fingerprint_package(package) != before
    finally:
        loadout.pylons.clear()
        loadout.pylons.update(original)
    assert fingerprint_package(package) == before

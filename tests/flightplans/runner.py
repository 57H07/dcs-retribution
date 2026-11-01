"""Generates the reference game, plans the scenarios and writes the results.

Run by the test in a child process with a fixed ``PYTHONHASHSEED`` (see
``README.md``)::

    PYTHONHASHSEED=0 python -m tests.flightplans.runner <output dir>

Writes ``fingerprints.json`` (scenario -> fingerprint) and ``game.liberation``
(the planned game, pickled like a save) into the output directory.
"""

from __future__ import annotations

import json
import pickle
import sys
import tempfile
from pathlib import Path

from game import persistency
from tests.flightplans.fingerprint import fingerprint_package
from tests.flightplans.referencegame import (
    generate_reference_game,
    repository_payloads_only,
)
from tests.flightplans.scenarios import plan_reference_packages

FINGERPRINTS_FILE = "fingerprints.json"
SAVE_FILE = "game.liberation"


def run(output_dir: Path) -> None:
    with tempfile.TemporaryDirectory() as saved_games:
        # Same stub as tests/conftest.py: no DCS install or user folder involved.
        persistency._dcs_saved_game_folder = saved_games
        with repository_payloads_only(Path(saved_games) / "no_user_payloads"):
            game = generate_reference_game()
            packages = plan_reference_packages(game)
            fingerprints = {
                name: fingerprint_package(package)
                for name, package in packages.items()
            }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / FINGERPRINTS_FILE).write_text(
        json.dumps(fingerprints, ensure_ascii=False), encoding="utf-8"
    )
    # Like persistency.save_game: the landmap is static data, not saved.
    game.theater.landmap = None
    with (output_dir / SAVE_FILE).open("wb") as save:
        pickle.dump(game, save)


if __name__ == "__main__":
    run(Path(sys.argv[1]))

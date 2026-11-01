"""Deterministic reference game for the flight-plan non-regression harness (W16).

The game is generated from a campaign shipped in ``resources/campaigns/`` through
the engine path only (``Campaign`` -> ``GameGenerator`` -> ``Game.begin_turn_0``),
the same sequence as ``qt_ui.main.create_game`` minus the Qt and DCS-install
specific steps. Generation takes a few seconds, which is why no save is committed.
"""

from __future__ import annotations

import random
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from dcs.payloads import PayloadDirectories
from dcs.unittype import FlyingType
from faker import Faker

from game import Game
from game.campaignloader.campaign import DEFAULT_BUDGET, Campaign
from game.factions import FACTIONS
from game.settings import Settings
from game.theater.start_generator import GameGenerator, GeneratorSettings, ModSettings

REFERENCE_SEED = 130

_REPO = Path(__file__).resolve().parents[2]
REFERENCE_CAMPAIGN = _REPO / "resources" / "campaigns" / "golan_heights_lite.yaml"
CUSTOMIZED_PAYLOADS = _REPO / "resources" / "customized_payloads"
BLUE_FACTION = "Israel 2000"
RED_FACTION = "Syria 2011"
START_DATE = datetime(2010, 6, 1)

_PAYLOAD_DIRECTORY_ATTRS = ("fallback", "_dcs", "_mod", "_user", "preferred")
_MISSING = object()


def seed_all(seed: int) -> None:
    """Seeds every RNG the engine draws from: :mod:`random` and Faker (pilot
    names), which keeps its own generator. numpy's is only used at mission
    generation (``rebelliongenerator``), outside this harness."""
    random.seed(seed)
    Faker.seed(seed)


def _flying_types() -> Iterator[type[FlyingType]]:
    pending: list[type[FlyingType]] = [FlyingType]
    while pending:
        cls = pending.pop()
        yield cls
        pending.extend(cls.__subclasses__())


@contextmanager
def repository_payloads_only(missing_dir: Path) -> Iterator[None]:
    """Loads payloads from ``resources/customized_payloads`` only.

    The app also reads the DCS install, its mods and the user's saved games
    (``qt_ui.main.inject_custom_payloads``), which differ between machines and
    would make default loadouts machine-dependent. pydcs caches payloads per
    aircraft class, so the caches are reset on entry and restored on exit.

    ``missing_dir`` must not contain payloads; it stands in for the user folder.
    """
    saved_dirs = {a: getattr(PayloadDirectories, a) for a in _PAYLOAD_DIRECTORY_ATTRS}
    saved_payloads: dict[type[FlyingType], Any] = {
        cls: cls.__dict__.get("payloads", _MISSING) for cls in _flying_types()
    }
    saved_cache = FlyingType._payload_cache

    def reset_caches() -> None:
        # An empty cache makes pydcs scan the payload directories again.
        FlyingType._payload_cache = {}
        for cls in saved_payloads:
            cls.payloads = None

    PayloadDirectories.preferred = None
    PayloadDirectories._user = missing_dir
    PayloadDirectories._dcs = []
    PayloadDirectories._mod = []
    PayloadDirectories.fallback = CUSTOMIZED_PAYLOADS
    reset_caches()
    try:
        yield
    finally:
        for attr, value in saved_dirs.items():
            setattr(PayloadDirectories, attr, value)
        for cls, payloads in saved_payloads.items():
            if payloads is _MISSING:
                if "payloads" in cls.__dict__:
                    delattr(cls, "payloads")
            else:
                cls.payloads = payloads
        FlyingType._payload_cache = saved_cache


def generate_reference_game() -> Game:
    """Generates the reference game (turn 0, nothing planned yet).

    Seeds :mod:`random` itself so the result does not depend on what ran before.
    """
    seed_all(REFERENCE_SEED)
    campaign = Campaign.from_file(REFERENCE_CAMPAIGN)
    theater = campaign.load_theater(advanced_iads=False)
    generator = GameGenerator(
        FACTIONS[BLUE_FACTION],
        FACTIONS[RED_FACTION],
        theater,
        campaign.load_air_wing_config(theater),
        Settings(),
        GeneratorSettings(
            start_date=START_DATE,
            start_time=campaign.recommended_start_time,
            player_budget=DEFAULT_BUDGET,
            enemy_budget=DEFAULT_BUDGET,
            inverted=False,
            advanced_iads=False,
            no_carrier=False,
            no_lha=False,
            no_player_navy=False,
            no_enemy_navy=False,
            tgo_config=campaign.load_ground_forces_config(),
            carrier_config=campaign.load_carrier_config(),
            squadrons_start_full=True,
        ),
        ModSettings(),
    )
    game = generator.generate()
    game.begin_turn_0(squadrons_start_full=True)
    return game

"""Tools menu actions (WEB-08.2).

Neither needs a file dialog: layouts are read from the install folders and the
Pretense mission is written to the missions folder, so both are plain commands.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from game import persistency
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game


def import_layouts() -> int:
    """Re-import every TGO layout from the layout folders; returns their count."""
    from game.layout import LAYOUTS

    LAYOUTS.initialize_locations_to_check()
    LAYOUTS.import_templates()
    return sum(1 for _ in LAYOUTS.layouts)


def _keep_pre_pretense_backup() -> None:
    """Copy the backup the generator saved before touching the campaign."""
    folder = persistency.pre_pretense_backups_dir()
    backup = folder / ".pre-pretense-backup.retribution"
    if backup.exists():
        stamp = datetime.now().strftime("%Y-%d-%mT%H_%M_%S")
        target = folder / f"pre-pretense-backup_{stamp}.retribution"
        target.write_bytes(backup.read_bytes())


def generate_pretense_campaign(game: Game, on_restored: Callable[[Game], None]) -> Path:
    """Write a Pretense mission of the running campaign; returns its path.

    The generation alters the campaign, so the generator goes on with a copy taken
    beforehand: `on_restored` receives it, to make it the running campaign.

    On failure, the campaign backup taken before generation is kept with a
    timestamp and the error becomes a `CommandError`.
    """
    from game.pretense.pretensemissiongenerator import PretenseMissionGenerator

    output = persistency.mission_path_for("pretense_campaign.miz")
    try:
        generator = PretenseMissionGenerator(game, game.conditions.start_time)
        generator.generate_miz(output)
    except Exception as error:
        logging.exception("Could not generate the Pretense campaign")
        _keep_pre_pretense_backup()
        raise CommandError(
            f"Could not generate the Pretense campaign: {error}", status_code=500
        ) from error
    on_restored(generator.game)
    return output

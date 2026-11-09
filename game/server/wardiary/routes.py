"""The war diary (#193): its entries, and its export as one HTML page."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends

from game import Game, persistency
from game.commands import CommandError
from game.gamelock import game_lock, locked, locks_game_itself
from game.native import FileOutcome, NativeBridge, one_dialog
from game.wardiary import export_html
from .models import WarDiaryJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext
from ..native.models import FileActionResultJs
from ..native.routes import require_bridge

router: APIRouter = APIRouter(prefix="/war-diary")

NO_CAMPAIGN = "No campaign is loaded."


@router.get("", operation_id="get_war_diary", response_model=WarDiaryJs | None)
@locked
def get_war_diary(game: Game | None = Depends(GameContext.get)) -> WarDiaryJs | None:
    """One entry per accepted mission result, newest first; null without a campaign."""
    if game is None:
        return None
    return WarDiaryJs.from_game(game)


def _file_name(campaign: str) -> str:
    name = re.sub(r'[<>:"/\|?*]', "", campaign).strip() or "Campaign"
    return f"War diary - {name}.html"


@router.post(
    "/export",
    operation_id="export_war_diary",
    response_model=FileActionResultJs,
    responses=command_error_responses(NO_CAMPAIGN),
)
@locks_game_itself
def export_war_diary(
    bridge: NativeBridge = Depends(require_bridge),
) -> FileActionResultJs:
    """Asks where to save the whole diary as one HTML page, then writes it."""
    with game_lock():
        game = GameContext.get()
        if game is None:
            raise CommandError(NO_CAMPAIGN)
        campaign = game.campaign_name or "Campaign"
        page = export_html(campaign, list(game.war_diary), game.war_diary_since_turn)
        start = persistency.retribution_dir() / _file_name(campaign)
    with one_dialog():
        path = bridge.choose_save_file(
            "Export the war diary", str(start), "Web page (*.html)"
        )
    if not path:
        return FileActionResultJs(outcome=FileOutcome.CANCELLED, path=None)
    try:
        persistency.write_atomically(
            Path(path), lambda f: f.write(page.encode("utf-8"))
        )
    except OSError as error:
        raise CommandError(
            f"The war diary could not be written: {error}", status_code=500
        ) from error
    return FileActionResultJs(outcome=FileOutcome.SAVED, path=path)

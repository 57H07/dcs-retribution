"""Production & repairs screen (issue #182)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from game import Game
from game.commands.production import run_production_action
from game.gamelock import locked
from game.server import EventStream
from .models import ProductionJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext

router: APIRouter = APIRouter(prefix="/production")


@router.get("/", operation_id="get_production", response_model=ProductionJs | None)
@locked
def get_production(
    game: Game | None = Depends(GameContext.get),
) -> ProductionJs | None:
    """What is in progress for the player and what waits; null without a campaign."""
    return None if game is None else ProductionJs.for_game(game)


@router.post(
    "/items/{item_id}/action",
    operation_id="run_production_action",
    response_model=ProductionJs,
    responses=command_error_responses(
        "the item is gone or has no action, not enough budget, or refused by the "
        "command it runs"
    ),
)
@locked
def run_action(item_id: str, game: Game = Depends(GameContext.require)) -> ProductionJs:
    """Runs the command of one item: the same as on its base, site or transfer."""
    with EventStream.event_context() as events:
        item = run_production_action(game, item_id, events)
    if item.action is not None and item.action.reloads_sim:
        GameContext.reload_sim()
    return ProductionJs.for_game(game)

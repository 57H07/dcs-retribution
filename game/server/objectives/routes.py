"""The campaign objectives (#194): optional goals that only grant rewards."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from game import Game
from game.gamelock import locked
from .models import CampaignObjectivesJs
from ..dependencies import GameContext

router: APIRouter = APIRouter(prefix="/objectives")


@router.get(
    "", operation_id="get_objectives", response_model=CampaignObjectivesJs | None
)
@locked
def get_objectives(
    game: Game | None = Depends(GameContext.get),
) -> CampaignObjectivesJs | None:
    """The campaign's objectives and their state; null without a campaign."""
    if game is None:
        return None
    return CampaignObjectivesJs.from_game(game)

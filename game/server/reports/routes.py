from fastapi import APIRouter, Depends

from game import Game
from game.gamelock import locked
from game.server import GameContext
from .models import FinancesJs, IntelJs, StatsJs

router: APIRouter = APIRouter(prefix="/reports")


@router.get("/intel", operation_id="get_intel_report", response_model=IntelJs | None)
@locked
def intel(game: Game | None = Depends(GameContext.get)) -> IntelJs | None:
    """Aircraft and ground units of each coalition, by base; null without a
    campaign."""
    if game is None:
        return None
    return IntelJs.from_game(game)


@router.get("/stats", operation_id="get_stats_report", response_model=StatsJs | None)
@locked
def stats(game: Game | None = Depends(GameContext.get)) -> StatsJs | None:
    """Force counts of both coalitions at each turn; null without a campaign."""
    if game is None:
        return None
    return StatsJs.from_game(game)


@router.get(
    "/finances", operation_id="get_finances_report", response_model=FinancesJs | None
)
@locked
def finances(game: Game | None = Depends(GameContext.get)) -> FinancesJs | None:
    """Income breakdown and balance of each coalition; null without a campaign."""
    if game is None:
        return None
    return FinancesJs.from_game(game)

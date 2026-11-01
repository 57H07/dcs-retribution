from fastapi import APIRouter, Depends

from game import Game
from game.gamelock import locked
from game.squadrons.career import careers
from game.theater.player import Player
from .models import CareerJs
from ..dependencies import GameContext

router: APIRouter = APIRouter(prefix="/careers")


@router.get("/", operation_id="list_careers", response_model=list[CareerJs] | None)
@locked
def list_careers(game: Game | None = Depends(GameContext.get)) -> list[CareerJs] | None:
    """Careers of the player pilots, living first; null without a campaign."""
    if game is None:
        return None
    air_wing = game.coalition_for(Player.BLUE).air_wing
    return [CareerJs.from_career(c) for c in careers(air_wing)]

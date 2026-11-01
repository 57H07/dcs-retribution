from fastapi import APIRouter, Depends

from game import Game
from game.commands import CommandError
from game.commands.tools import generate_pretense_campaign, import_layouts
from game.gamelock import locked
from .models import LayoutImportJs, PretenseCampaignJs
from ..commanderrors import command_error_responses
from ..dependencies import GameContext

router: APIRouter = APIRouter(prefix="/tools")


@router.post(
    "/import-layouts",
    operation_id="import_layouts",
    response_model=LayoutImportJs,
)
@locked
def post_import_layouts() -> LayoutImportJs:
    """Re-imports the TGO layouts from the layout folders (a developer tool).

    Takes a few seconds; answers once done. Works without a campaign.
    """
    return LayoutImportJs(count=import_layouts())


@router.post(
    "/pretense-campaign",
    operation_id="generate_pretense_campaign",
    response_model=PretenseCampaignJs,
    responses=command_error_responses(
        "No campaign is loaded (409), or the generation failed (500)"
    ),
)
@locked
def post_pretense_campaign(
    game: Game | None = Depends(GameContext.get),
) -> PretenseCampaignJs:
    """Writes a Pretense mission of the running campaign to the missions folder."""
    if game is None:
        raise CommandError("No campaign is loaded.")
    return PretenseCampaignJs(path=str(generate_pretense_campaign(game)))

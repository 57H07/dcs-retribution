"""Native bridge over HTTP (WEB-00.7, W7): file and folder dialogs, folders, links,
quit.

The file routes answer once the player has closed the dialog: the request itself
carries the result back (saved path, or cancelled). They run on a worker thread and
hold the game lock only to read and write the campaign, never while the dialog
waits (`game.native.files`).
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from game.gamelock import locked, locks_game_itself
from game.native import (
    ExternalLink,
    NativeBridge,
    NativeContext,
    NativeFolder,
    choose_folder,
    open_game,
    save_game,
    save_game_as,
)
from .models import FileActionResultJs, FolderPickRequestJs, FolderPickResultJs
from ..commanderrors import CommandErrorJs, command_error_responses
from ..dependencies import GameContext

router: APIRouter = APIRouter(prefix="/native")

_FILE_ERRORS = {
    **command_error_responses(
        "when no campaign is loaded, another file dialog is open, the campaign "
        "changed during the dialog or the save file is incompatible"
    ),
    500: {"model": CommandErrorJs, "description": "when the file cannot be written"},
}


def require_bridge() -> NativeBridge:
    bridge = NativeContext.get()
    if bridge is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The native shell is not available.",
        )
    return bridge


@router.post(
    "/save",
    operation_id="save_game",
    response_model=FileActionResultJs,
    responses=_FILE_ERRORS,
)
@locks_game_itself
def save(bridge: NativeBridge = Depends(require_bridge)) -> FileActionResultJs:
    """Saves to the current save file, or asks for one when the campaign has none."""
    return FileActionResultJs.from_result(save_game(bridge, GameContext.get))


@router.post(
    "/save-as",
    operation_id="save_game_as",
    response_model=FileActionResultJs,
    responses=_FILE_ERRORS,
)
@locks_game_itself
def save_as(bridge: NativeBridge = Depends(require_bridge)) -> FileActionResultJs:
    return FileActionResultJs.from_result(save_game_as(bridge, GameContext.get))


@router.post(
    "/open",
    operation_id="open_game",
    response_model=FileActionResultJs,
    responses=_FILE_ERRORS,
)
@locks_game_itself
def open_save(bridge: NativeBridge = Depends(require_bridge)) -> FileActionResultJs:
    """Asks for a save file and loads it; the new campaign arrives as events."""
    return FileActionResultJs.from_result(open_game(bridge, GameContext.get))


@router.post(
    "/pick-folder",
    operation_id="pick_folder",
    response_model=FolderPickResultJs,
    responses=command_error_responses("when another file dialog is open"),
)
@locks_game_itself
def pick_folder(
    request: FolderPickRequestJs, bridge: NativeBridge = Depends(require_bridge)
) -> FolderPickResultJs:
    """Asks for a folder and answers once the player closed the dialog.

    Does not touch the campaign, so it never takes the game lock.
    """
    return FolderPickResultJs(
        path=choose_folder(bridge, request.purpose, request.start)
    )


@router.post(
    "/new-game",
    operation_id="open_new_game_wizard",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def new_game(bridge: NativeBridge = Depends(require_bridge)) -> None:
    """Opens the new campaign wizard without waiting for it."""
    bridge.open_new_game()


@router.post(
    "/open-folder/{folder}",
    operation_id="open_native_folder",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def open_folder(
    folder: NativeFolder, bridge: NativeBridge = Depends(require_bridge)
) -> None:
    bridge.open_folder(folder.path())


@router.post(
    "/open-link/{link}",
    operation_id="open_external_link",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def open_link(
    link: ExternalLink, bridge: NativeBridge = Depends(require_bridge)
) -> None:
    """Opens a Help page in the system browser (the web view cannot)."""
    bridge.open_url(link.url)


@router.post(
    "/quit",
    operation_id="quit_application",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@locked
def quit_application(bridge: NativeBridge = Depends(require_bridge)) -> None:
    """Closes the application; the shell asks whether to save first."""
    bridge.quit()

"""Waiting for the mission result (WEB-05.1): status, manual load, abort, accept.

`POST /game/mission` starts the wait; the status changes are published on the event
stream (`mission_result_updated`), so the waiting screen refetches
`GET /game/mission/result`. Nothing here holds the game lock while waiting for DCS
or for the player: the watch thread takes it only to read a new state.json, and the
manual load only after its file dialog closed.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Response, status

from game import Game
from game.commands import (
    CommandError,
    MissionResultStatus,
    abort_mission,
    accept_results,
)
from game.gamelock import game_lock, locked, locks_game_itself
from game.native import NativeBridge, one_dialog
from .models import MissionResultJs
from .waiter import MissionResultContext
from ..commanderrors import command_error_responses
from ..dependencies import GameContext, QtCallbacks, QtContext
from ..eventstream import EventStream
from ..game.models import CampaignStateJs, TurnJs
from ..native.routes import require_bridge

router: APIRouter = APIRouter(prefix="/game/mission/result")

STATE_FILE_FILTER = "DCS mission state (*.json)"


def _require_game(game: Game | None) -> Game:
    if game is None:
        raise CommandError("No campaign is loaded.")
    return game


@router.get("", operation_id="get_mission_result", response_model=MissionResultJs)
@locked
def mission_result() -> MissionResultJs:
    """The mission waiting for its result: detection of state.json, losses so far."""
    return MissionResultJs.from_snapshot(MissionResultContext.get().snapshot())


@router.post(
    "/file",
    operation_id="load_mission_result_file",
    response_model=MissionResultJs,
    responses=command_error_responses(
        "No campaign is loaded, no mission is waiting, another file dialog is open "
        "or the file cannot be read."
    ),
)
@locks_game_itself
def load_file(bridge: NativeBridge = Depends(require_bridge)) -> MissionResultJs:
    """ "Load state.json": asks for a state.json and takes it as the final result.

    Answers once the dialog is closed; a cancelled dialog changes nothing.
    """
    waiter = MissionResultContext.get()
    snapshot = waiter.snapshot()
    if snapshot.status is MissionResultStatus.IDLE:
        raise CommandError("No mission is waiting for its result.")
    with one_dialog():
        path = bridge.choose_file(
            "Select the state.json of the mission",
            str(snapshot.state_path.parent),
            STATE_FILE_FILTER,
        )
    with game_lock():
        if path:
            _require_game(GameContext.get())
            waiter.load(GameContext.get_sim(), Path(path))
        return MissionResultJs.from_snapshot(waiter.snapshot())


@router.post(
    "/cancel",
    operation_id="abort_mission",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("No campaign is loaded."),
)
@locked
def cancel(qt: QtCallbacks | None = Depends(QtContext.get_optional)) -> None:
    """ "Abort mission": stops waiting and goes back to planning, as in Qt."""
    game = _require_game(GameContext.get())
    MissionResultContext.get().stop()
    EventStream.put_nowait(abort_mission(game, GameContext.get_sim()))
    if qt is not None and qt.game_changed is not None:
        qt.game_changed()


@router.post(
    "/accept",
    operation_id="accept_mission_result",
    response_model=TurnJs,
    responses=command_error_responses(
        "No campaign is loaded, no result was received or the mission is not over."
    ),
)
@locked
def accept(qt: QtCallbacks | None = Depends(QtContext.get_optional)) -> TurnJs:
    """ "Accept results": applies the mission result and starts the next turn.

    The Qt debriefing window then shows the report (until WEB-05.2).
    """
    game = _require_game(GameContext.get())
    waiter = MissionResultContext.get()
    debriefing = waiter.final_result()
    accept_results(game, GameContext.get_sim(), debriefing)
    waiter.stop()
    if qt is not None and qt.results_accepted is not None:
        qt.results_accepted(debriefing)
    return TurnJs(
        turn=game.turn,
        campaign_state=CampaignStateJs.from_turn_state(game.check_win_loss()),
    )

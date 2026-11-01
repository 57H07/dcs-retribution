"""Waiting for the mission result (WEB-05.1): status, manual load, abort, accept;
and its after-action report (WEB-05.2).

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
    accept_and_report,
)
from game.debriefingreport import build_report
from game.gamelock import game_lock, locked, locks_game_itself
from game.native import NativeBridge, one_dialog
from .models import (
    AfterActionReportJs,
    DebriefingJs,
    DebriefingStatusJs,
    MissionResultJs,
)
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


@router.get("/report", operation_id="get_mission_report", response_model=DebriefingJs)
@locked
def report() -> DebriefingJs:
    """The after-action report: of the result waiting to be accepted, else of the
    last result accepted since the application started."""
    waiter = MissionResultContext.get()
    snapshot = waiter.snapshot()
    if snapshot.debriefing is not None and GameContext.get() is not None:
        return DebriefingJs(
            status=DebriefingStatusJs.PENDING,
            can_accept=snapshot.mission_ended,
            report=AfterActionReportJs.from_report(build_report(snapshot.debriefing)),
        )
    last = waiter.last_report()
    if last is not None:
        return DebriefingJs(
            status=DebriefingStatusJs.ACCEPTED,
            can_accept=False,
            report=AfterActionReportJs.from_report(last),
        )
    return DebriefingJs(status=DebriefingStatusJs.NONE, can_accept=False, report=None)


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

    Same `accept_results` as the Qt waiting window; the report of the applied
    result is then served by `GET /game/mission/result/report` (status
    "accepted"). The Qt widgets refresh and the campaign end is checked as after
    any turn (`QtCallbacks.turn_passed`), as closing the Qt debriefing did.
    """
    game = _require_game(GameContext.get())
    waiter = MissionResultContext.get()
    debriefing = waiter.final_result()
    report = accept_and_report(game, GameContext.get_sim(), debriefing)
    waiter.finish(report)
    state = game.check_win_loss()
    if qt is not None and qt.turn_passed is not None:
        qt.turn_passed(state)
    return TurnJs(
        turn=game.turn,
        campaign_state=CampaignStateJs.from_turn_state(state),
    )

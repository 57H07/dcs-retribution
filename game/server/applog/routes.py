from fastapi import APIRouter, Query

from game.applog import log_tail
from game.gamelock import locked, locks_game_itself
from .models import AboutJs, LogTailJs

router: APIRouter = APIRouter()

#: Most lines `GET /logs` sends at once.
MAX_LOG_LINES = 5000


@router.get("/logs", operation_id="get_logs", response_model=LogTailJs)
@locks_game_itself  # Touches no Game: the log stays readable during a long command.
def get_logs(
    lines: int = Query(default=1000, ge=1, le=MAX_LOG_LINES),
) -> LogTailJs:
    """The last `lines` lines of the application log; works without a campaign."""
    tail = log_tail(lines)
    if tail is None:
        return LogTailJs(lines=[], total=0, available=False)
    shown, total = tail
    return LogTailJs(lines=shown, total=total, available=True)


@router.get("/about", operation_id="get_about", response_model=AboutJs)
@locked
def get_about() -> AboutJs:
    """Version and credits of DCS Retribution."""
    return AboutJs.current()

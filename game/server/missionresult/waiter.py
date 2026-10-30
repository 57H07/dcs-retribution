"""The mission waiting for its result, for the API routes (WEB-05.1)."""

from __future__ import annotations

from game.commands import MissionResultWaiter
from game.sim import GameUpdateEvents
from ..eventstream import EventStream


def _publish() -> None:
    EventStream.put_nowait(GameUpdateEvents().update_mission_result())


class MissionResultContext:
    """One waiter per application: the web UI waits for one mission at a time."""

    _waiter: MissionResultWaiter | None = None

    @classmethod
    def get(cls) -> MissionResultWaiter:
        if cls._waiter is None:
            cls._waiter = MissionResultWaiter(_publish)
        return cls._waiter

    @classmethod
    def set(cls, waiter: MissionResultWaiter | None) -> None:
        """Replace the waiter (tests)."""
        cls._waiter = waiter

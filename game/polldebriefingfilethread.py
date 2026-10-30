from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from threading import Event, Thread
from typing import Callable, TYPE_CHECKING

from game.gamelock import game_lock

if TYPE_CHECKING:
    from game.debriefing import Debriefing
    from game.sim import MissionSimulation


#: How often (seconds) we check state.json. DCS' export hook rewrites the
#: file every second once the mission has ended, so a short interval keeps
#: end-of-mission detection responsive without burning CPU.
POLL_INTERVAL_SECONDS = 2

#: The file DCS' export hook writes, relative to the working directory.
STATE_FILE = Path("state.json")

#: Errors raised by reading a state.json that DCS is still writing.
STATE_FILE_ERRORS = (json.JSONDecodeError, OSError, ValueError, KeyError)


class PollDebriefingFileThread(Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition.

    Shared by the Qt waiting window and the web waiting screen (WEB-05.1). The game
    lock is held only while a new state.json is read, never while waiting.
    """

    def __init__(
        self,
        callback: Callable[[Debriefing], None],
        mission_sim: MissionSimulation,
        on_error: Callable[[Exception], None] | None = None,
        state_path: Path = STATE_FILE,
        poll_interval: float = POLL_INTERVAL_SECONDS,
    ) -> None:
        super().__init__(daemon=True)
        self._stop_event = Event()
        self.callback = callback
        self.mission_sim = mission_sim
        self.on_error = on_error
        self.state_path = state_path
        self.poll_interval = poll_interval

    def stop(self) -> None:
        self._stop_event.set()

    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def run(self) -> None:
        # Treat any state.json newer than this mission's .miz as the current
        # mission's result; an older file is a stale leftover from a previous
        # mission and is ignored until DCS rewrites it.
        last_modified = self.mission_sim.miz_generated_at
        logging.info(
            "Watching %s for writes after mission launch (mtime > %s)",
            self.state_path,
            last_modified,
        )
        while not self.stopped():
            try:
                if (
                    os.path.isfile(self.state_path)
                    and os.path.getmtime(self.state_path) > last_modified
                ):
                    modified = os.path.getmtime(self.state_path)
                    with game_lock():
                        debriefing = self.mission_sim.debrief_current_state(
                            self.state_path
                        )
                    if self.stopped():
                        break
                    self.callback(debriefing)
                    last_modified = modified
                    if debriefing.state_data.mission_ended:
                        logging.info("Mission end detected; stopping poll")
                        break
            except STATE_FILE_ERRORS as error:
                logging.error(
                    "Failed to read state.json (likely read while DCS was "
                    "still writing it); will retry in %ss.",
                    self.poll_interval,
                    exc_info=True,
                )
                if self.on_error is not None:
                    self.on_error(error)
            self._stop_event.wait(self.poll_interval)

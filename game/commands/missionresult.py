"""Waiting for the result of a mission flown in DCS (WEB-05.1).

Extracted from `qt_ui/windows/QWaitingForMissionResultWindow.py` so that the Qt
window and the web waiting screen share the same rules: watch `state.json` (with
`PollDebriefingFileThread`), load a file by hand, abort the mission, accept the
results.

Threading: the watch runs on its own thread and takes the game lock only while it
reads a new `state.json`. `MissionResultWaiter` keeps its state behind a small lock
of its own, so that reading the status never waits for the game lock, and the game
lock is never held while waiting for DCS.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, TYPE_CHECKING

from game.ato.flightstate import Uninitialized
from game.polldebriefingfilethread import STATE_FILE, STATE_FILE_ERRORS
from game.profiling import logged_duration
from game.sim.gameupdateevents import GameUpdateEvents
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.debriefing import Debriefing


class Stoppable(Protocol):
    def stop(self) -> None: ...


class ResultSim(Protocol):
    """The part of the simulation the mission result needs (`SimController`)."""

    def wait_for_debriefing(
        self,
        callback: Callable[[Debriefing], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> Stoppable: ...

    def debrief_current_state(
        self, state_path: Path, force_end: bool = False
    ) -> Debriefing: ...

    def process_results(self, debriefing: Debriefing) -> None: ...

    def set_game(self, game: Game | None) -> None: ...


class MissionResultStatus(Enum):
    #: No mission is waiting for its result.
    IDLE = "idle"
    #: The mission was generated; no state.json newer than it was read yet.
    WAITING = "waiting"
    #: A state.json was read: the mission is being played, or is over.
    DETECTED = "detected"
    #: The last read of state.json failed; the watch retries.
    ERROR = "error"


@dataclass(frozen=True)
class MissionResultSnapshot:
    status: MissionResultStatus
    miz_path: Path | None
    state_path: Path
    debriefing: Debriefing | None
    error: str | None

    @property
    def mission_ended(self) -> bool:
        return self.debriefing is not None and self.debriefing.state_data.mission_ended


class MissionResultWaiter:
    """The mission waiting for its result, shared by the API routes.

    `on_change` is called (without any lock held) whenever the status changes, from
    the calling thread or the watch thread: it must only publish, never block.
    """

    def __init__(
        self, on_change: Callable[[], None], state_path: Path = STATE_FILE
    ) -> None:
        self._on_change = on_change
        self._state_path = state_path
        self._lock = threading.Lock()
        self._status = MissionResultStatus.IDLE
        self._miz_path: Path | None = None
        self._debriefing: Debriefing | None = None
        self._error: str | None = None
        self._watch: Stoppable | None = None
        # Bumped on every start/stop: a late callback of a stopped watch is ignored.
        self._generation = 0

    def snapshot(self) -> MissionResultSnapshot:
        with self._lock:
            return MissionResultSnapshot(
                self._status,
                self._miz_path,
                self._state_path.absolute(),
                self._debriefing,
                self._error,
            )

    def start(self, sim: ResultSim, miz_path: Path) -> None:
        """Watch state.json for the result of the mission just written."""
        with self._lock:
            self._stop_watch()
            self._generation += 1
            generation = self._generation
            self._status = MissionResultStatus.WAITING
            self._miz_path = miz_path
            self._debriefing = None
            self._error = None
        watch = sim.wait_for_debriefing(
            lambda debriefing: self._detected(generation, debriefing),
            lambda error: self._failed(generation, error),
        )
        with self._lock:
            current = generation == self._generation
            if current:
                self._watch = watch
        if not current:
            # Stopped or restarted while the watch was starting.
            watch.stop()
        self._on_change()

    def stop(self) -> None:
        """Stop watching and forget the mission (aborted or results accepted)."""
        with self._lock:
            self._stop_watch()
            self._generation += 1
            self._status = MissionResultStatus.IDLE
            self._miz_path = None
            self._debriefing = None
            self._error = None
        self._on_change()

    def load(self, sim: ResultSim, path: Path) -> Debriefing:
        """Use a state.json picked by hand as the final result ("Manually submit").

        The caller holds the game lock. The watch stops: the file wins over DCS.

        Raises:
            CommandError: no mission is waiting, or the file cannot be read.
        """
        with self._lock:
            if self._status is MissionResultStatus.IDLE:
                raise CommandError("No mission is waiting for its result.")
        try:
            debriefing = sim.debrief_current_state(path, force_end=True)
        except STATE_FILE_ERRORS as error:
            logging.exception("Could not read %s", path)
            raise CommandError(f"Could not read {path.name}: {error}") from error
        with self._lock:
            self._stop_watch()
            self._generation += 1
            self._status = MissionResultStatus.DETECTED
            self._debriefing = debriefing
            self._error = None
        self._on_change()
        return debriefing

    def final_result(self) -> Debriefing:
        """The result to accept: only once the mission is over.

        Raises:
            CommandError: no result yet, or the mission is still being played.
        """
        snapshot = self.snapshot()
        if snapshot.debriefing is None:
            raise CommandError("No mission result has been received yet.")
        if not snapshot.mission_ended:
            raise CommandError("The mission is still being played.")
        return snapshot.debriefing

    def _stop_watch(self) -> None:
        if self._watch is not None:
            self._watch.stop()
            self._watch = None

    def _detected(self, generation: int, debriefing: Debriefing) -> None:
        with self._lock:
            if generation != self._generation:
                return
            self._status = MissionResultStatus.DETECTED
            self._debriefing = debriefing
            self._error = None
        self._on_change()

    def _failed(self, generation: int, error: Exception) -> None:
        with self._lock:
            if generation != self._generation:
                return
            self._status = MissionResultStatus.ERROR
            self._error = f"Could not read {self._state_path.name}: {error}"
        self._on_change()


def abort_mission(game: Game, sim: ResultSim) -> GameUpdateEvents:
    """ "Abort mission": back to planning as if the mission was never generated.

    Restarts the turn simulation, resets every flight to its planned state and frees
    the parking slots. Returns the events to publish. The caller holds the game lock.
    """
    sim.set_game(game)
    events = GameUpdateEvents()
    for flight in game.db.flights.objects.values():
        flight.state = Uninitialized(flight, game.settings)
        events.update_flight(flight)
    for cp in game.theater.controlpoints:
        cp.release_parking_slots()
    return events


def accept_results(game: Game, sim: ResultSim, debriefing: Debriefing) -> None:
    """ "Accept results": apply the mission result and start the next turn.

    `Game.pass_turn` publishes `new_turn`. The caller holds the game lock.
    """
    with logged_duration("Turn processing"):
        sim.process_results(debriefing)
        game.pass_turn()

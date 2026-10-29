from collections.abc import Iterator
from contextlib import contextmanager
from threading import RLock, Timer, current_thread
from typing import Callable, Optional

from game.gamelock import game_lock
from .simspeedsetting import SimSpeedSetting


class GameLoopTimer:
    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self.simulation_speed = SimSpeedSetting.PAUSED
        self._timer: Optional[Timer] = None
        # Reentrant to allow a single thread nested use of `locked_pause`.
        # Lock order: the game lock (`game.gamelock`) is always taken before this one.
        self._timer_lock = RLock()

    def set_speed(self, simulation_speed: SimSpeedSetting) -> None:
        with self._timer_lock:
            self._set_speed(simulation_speed)

    def stop(self) -> None:
        with self._timer_lock:
            self._stop()

    @contextmanager
    def locked_pause(self) -> Iterator[None]:
        # NB: This must be a locked _pause_ and not a locked speed, because nested use
        # of this method is allowed. That's okay if all nested callers set the same
        # speed (paused), but not okay if a parent locks a speed and a child locks
        # another speed. That's okay though, because we're unlikely to ever want to lock
        # any speed but paused.
        with self._timer_lock:
            old_speed = self.simulation_speed
            self._stop()
            try:
                yield
            finally:
                self._set_speed(old_speed)

    def _set_speed(self, simulation_speed: SimSpeedSetting) -> None:
        self._stop()
        self.simulation_speed = simulation_speed
        self._recreate_timer()

    def _stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()

    def _recreate_timer(self) -> None:
        self._stop()
        factor = self.simulation_speed.speed_factor
        if not factor:
            self._timer = None
            return None
        self._timer = Timer(1 / factor, self._tick)
        self._timer.start()

    def _tick(self) -> None:
        # The tick runs under the global game lock (WEB-00.4) so that it never
        # interleaves with API commands or Qt actions. While this thread waited for
        # the lock, the timer may have been stopped or replaced (pause, speed change,
        # fast forward): a cancelled timer must neither tick nor reschedule.
        timer = current_thread()
        with game_lock():
            if isinstance(timer, Timer) and timer.finished.is_set():
                return
            self.callback()
        with self._timer_lock:
            if isinstance(timer, Timer) and timer.finished.is_set():
                return
            self._recreate_timer()

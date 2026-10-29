"""WEB-00.4: serialized Game access (global lock) and thread-safe event stream."""

from __future__ import annotations

import asyncio
import inspect
import threading
import time
from asyncio import Queue
from collections.abc import Callable, Iterator
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute

from game.gamelock import _GAME_LOCK, game_lock, locked
from game.server.app import app
from game.server.controlpoints.routes import cancel_travel
from game.server.eventstream import EventStream
from game.sim import GameUpdateEvents
from game.sim.gameloop import GameLoop
from game.sim.gameupdatecallbacks import GameUpdateCallbacks
from game.sim.simspeedsetting import SimSpeedSetting

COUNTERS = 40
COMMAND_THREADS = 4
COMMANDS_PER_THREAD = 40


class _SharedState:
    """Stands in for Game: consistent only when every counter has the same value.

    A sim tick bumps the counters one by one, yielding the GIL in between, so any
    command running at the same time as a tick sees them unequal.
    """

    def __init__(self) -> None:
        self.counters = [0] * COUNTERS
        self.ticking = False
        self.errors: list[str] = []
        self.log: list[str] = []

    def check(self, who: str) -> None:
        if self.ticking:
            self.errors.append(f"{who} ran during a sim tick")
        if len(set(self.counters)) != 1:
            self.errors.append(f"{who} saw inconsistent counters {self.counters}")


class _ControlPoint:
    """Minimal mobile, player-owned control point for the cancel-travel route."""

    def __init__(self, state: _SharedState) -> None:
        self.id = uuid4()
        self.moveable = True
        self.captured = SimpleNamespace(is_blue=True)
        self._state = state
        self._target: Any = object()

    @property
    def target_position(self) -> Any:
        return self._target

    @target_position.setter
    def target_position(self, value: Any) -> None:
        self._state.check("cancel-travel route")
        self._state.log.append("command")
        self._target = value


class _Sim:
    """Fake MissionSimulation whose tick mutates the shared state non-atomically."""

    def __init__(self, state: _SharedState, complete_after: int | None) -> None:
        self.state = state
        self.complete_after = complete_after
        self.ticks = 0
        self.time = datetime(2000, 1, 1)

    def begin_simulation(self) -> None:
        pass

    def tick(
        self, events: GameUpdateEvents, _method: Any, force_continue: bool
    ) -> GameUpdateEvents:
        state = self.state
        if state.ticking:
            state.errors.append("two sim ticks overlapped")
        state.ticking = True
        for i in range(COUNTERS):
            state.counters[i] += 1
            if i % 8 == 0:
                time.sleep(0)  # Let other threads run mid-tick.
        state.ticking = False
        state.log.append("tick")
        self.ticks += 1
        if self.complete_after is not None and self.ticks >= self.complete_after:
            events.complete_simulation()
        return events


def _game_loop(
    state: _SharedState, complete_after: int | None = None
) -> tuple[GameLoop, _Sim]:
    game: Any = SimpleNamespace(
        conditions=SimpleNamespace(start_time=datetime(2000, 1, 1)),
        settings=SimpleNamespace(combat_resolution_method=None),
    )
    loop = GameLoop(game, GameUpdateCallbacks(lambda: None, lambda _events: None))
    sim = _Sim(state, complete_after)
    loop.sim = sim  # type: ignore[assignment]
    return loop, sim


def _fake_game(cp: _ControlPoint) -> Any:
    def find(cp_id: UUID) -> _ControlPoint | None:
        cp._state.check("control point lookup")
        return cp if cp_id == cp.id else None

    return SimpleNamespace(theater=SimpleNamespace(find_control_point_by_id=find))


@pytest.fixture(autouse=True)
def fresh_event_stream(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(EventStream, "_queue", Queue())
    monkeypatch.setattr(EventStream, "_loop", None)
    yield


def _run_threads(targets: list[Callable[[], None]]) -> list[BaseException]:
    errors: list[BaseException] = []
    start = threading.Barrier(len(targets))

    def wrap(target: Callable[[], None]) -> Callable[[], None]:
        def run() -> None:
            try:
                start.wait()
                target()
            except BaseException as ex:  # pragma: no cover - reported below
                errors.append(ex)

        return run

    threads = [threading.Thread(target=wrap(t)) for t in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive(), "deadlock: a thread did not finish"
    return errors


def _command_worker(state: _SharedState, cp: _ControlPoint) -> Callable[[], None]:
    game = _fake_game(cp)

    def run() -> None:
        for i in range(COMMANDS_PER_THREAD):
            # The real route function, as FastAPI calls it from its threadpool.
            cancel_travel(cp.id, game=game)
            if i % 4 == 0:
                time.sleep(0.0005)

    return run


def test_concurrent_commands_during_sim_ticks() -> None:
    state = _SharedState()
    loop, sim = _game_loop(state)
    cp = _ControlPoint(state)

    def qt_action() -> None:
        # A Qt-side mutation, through the same path qt_ui/models.py uses.
        for _ in range(COMMANDS_PER_THREAD):
            with loop.paused_sim():
                state.check("Qt action")
                state.log.append("qt")
            time.sleep(0.0005)

    def wait_for_ticks() -> None:
        # On a loaded machine the commands can all finish before the timer
        # first fires; keep the sim running until it has ticked a few times.
        deadline = time.monotonic() + 10
        while sim.ticks < 3 and time.monotonic() < deadline:
            time.sleep(0.001)

    loop.set_simulation_speed(SimSpeedSetting.X1000)
    try:
        errors = _run_threads(
            [_command_worker(state, cp) for _ in range(COMMAND_THREADS)]
            + [qt_action, wait_for_ticks]
        )
    finally:
        loop.pause()

    assert errors == []
    with game_lock():
        assert state.errors == []
        assert sim.ticks > 0, "the sim never ticked during the test"
        assert state.log.count("command") == COMMAND_THREADS * COMMANDS_PER_THREAD
        assert state.log.count("qt") == COMMANDS_PER_THREAD
        assert set(state.counters) == {sim.ticks}
    assert cp.target_position is None
    # Every command published its event to the stream.
    assert EventStream._queue.qsize() == COMMAND_THREADS * COMMANDS_PER_THREAD


def test_fast_forward_and_commands_never_interleave() -> None:
    state = _SharedState()
    fast_forward_ticks = 200
    loop, sim = _game_loop(state, complete_after=fast_forward_ticks)
    cp = _ControlPoint(state)

    errors = _run_threads(
        [_command_worker(state, cp) for _ in range(COMMAND_THREADS)]
        + [loop.run_to_first_contact]
    )

    assert errors == []
    assert state.errors == []
    assert sim.ticks == fast_forward_ticks
    # The whole fast forward is one uninterrupted run of ticks.
    ticks = "".join("t" if entry == "tick" else "c" for entry in state.log)
    assert "t" * fast_forward_ticks in ticks
    assert ticks.count("c") == COMMAND_THREADS * COMMANDS_PER_THREAD


def test_cancelled_timer_tick_does_not_run() -> None:
    state = _SharedState()
    loop, sim = _game_loop(state)
    loop.start()
    with game_lock():
        loop.set_simulation_speed(SimSpeedSetting.X1000)
        time.sleep(0.02)  # The timer fires and blocks on the game lock.
        loop.pause()
    time.sleep(0.02)
    assert sim.ticks == 0


def test_every_api_route_takes_the_game_lock() -> None:
    # Routes that lock only part of their body on purpose.
    partially_locked = {"get_offline_basemap_image"}
    unlocked = [
        route.name
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.name not in partially_locked
        and not getattr(route.endpoint, "takes_game_lock", False)
        and not getattr(route.endpoint, "locks_game_itself", False)
    ]
    assert unlocked == []


def _lock_is_free_for_other_threads() -> bool:
    result: list[bool] = []

    def try_acquire() -> None:
        acquired = _GAME_LOCK.acquire(blocking=False)
        if acquired:
            _GAME_LOCK.release()
        result.append(acquired)

    thread = threading.Thread(target=try_acquire)
    thread.start()
    thread.join()
    return result[0]


def test_locked_holds_the_lock_and_keeps_the_signature() -> None:
    @locked
    def command(value: int, *, game: str = "g") -> bool:
        """Doc."""
        return _lock_is_free_for_other_threads()

    assert _lock_is_free_for_other_threads()
    assert command(1) is False
    assert command.__name__ == "command"
    assert command.__doc__ == "Doc."
    assert list(inspect.signature(command).parameters) == ["value", "game"]


def test_event_stream_delivers_events_from_many_threads() -> None:
    producers = 4
    per_producer = 200
    received: list[GameUpdateEvents] = []
    loop = asyncio.new_event_loop()
    consumer_ready = threading.Event()

    async def consume() -> None:
        consumer_ready.set()
        while len(received) < producers * per_producer:
            received.append(await EventStream.get())

    consumer = threading.Thread(target=lambda: loop.run_until_complete(consume()))
    consumer.start()
    assert consumer_ready.wait(timeout=5)
    # Wait until the consumer has bound the stream to its loop.
    deadline = time.monotonic() + 5
    while EventStream._loop is not loop and time.monotonic() < deadline:
        time.sleep(0.001)

    sent: dict[int, list[GameUpdateEvents]] = {
        p: [GameUpdateEvents() for _ in range(per_producer)] for p in range(producers)
    }

    def produce(p: int) -> Callable[[], None]:
        def run() -> None:
            for events in sent[p]:
                EventStream.put_nowait(events)

        return run

    try:
        errors = _run_threads([produce(p) for p in range(producers)])
        consumer.join(timeout=10)
        assert not consumer.is_alive(), "events were lost: the consumer starved"
    finally:
        if consumer.is_alive():
            loop.call_soon_threadsafe(loop.stop)
            consumer.join(timeout=5)
        loop.close()

    assert errors == []
    assert len(received) == producers * per_producer
    # Each producer's events arrive in the order it published them.
    for p in range(producers):
        mine = [e for e in received if any(e is s for s in sent[p])]
        assert [id(e) for e in mine] == [id(e) for e in sent[p]]


def test_event_stream_works_without_a_running_loop() -> None:
    EventStream.put_nowait(GameUpdateEvents())
    EventStream.put_nowait(GameUpdateEvents())
    assert EventStream._queue.qsize() == 2
    EventStream.drain()
    assert EventStream._queue.empty()


def test_event_stream_falls_back_when_the_loop_is_closed() -> None:
    loop = asyncio.new_event_loop()
    EventStream._loop = loop
    loop.close()
    EventStream.put_nowait(GameUpdateEvents().shut_down())
    assert EventStream._queue.qsize() == 1

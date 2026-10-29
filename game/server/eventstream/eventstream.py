from __future__ import annotations

import asyncio
import threading
from asyncio import AbstractEventLoop, Queue
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Callable, Optional

from game.sim import GameUpdateEvents


class EventStream:
    """Hands game update events from any thread to the /eventstream websocket.

    Producers live on several threads (Qt main thread, API worker threads, the sim
    timer thread) while the consumer awaits on the server's asyncio loop. An
    `asyncio.Queue` is not thread-safe, so once the consumer has bound the queue to
    its loop, puts from other threads are marshalled onto that loop with
    `call_soon_threadsafe`. Before that (no server running yet, or in tests) nothing
    can be waiting on the queue, so puts go straight in.
    """

    _queue: Queue[GameUpdateEvents] = Queue()
    _loop: Optional[AbstractEventLoop] = None
    # Guards `_loop` together with direct puts, so that no put can slip in directly
    # while the consumer is binding the queue to its loop.
    _lock = threading.Lock()

    @classmethod
    def _target_loop(cls) -> Optional[AbstractEventLoop]:
        """The loop to marshal onto, or None to touch the queue directly.

        Must be called with `_lock` held.
        """
        loop = cls._loop
        if loop is None or loop.is_closed():
            return None
        try:
            if asyncio.get_running_loop() is loop:
                return None
        except RuntimeError:
            pass
        return loop

    @classmethod
    def _run_on_loop(cls, callback: Callable[..., None], *args: object) -> None:
        """Run callback on the consumer's loop, or right here if there is none.

        Must be called with `_lock` held.
        """
        if (loop := cls._target_loop()) is not None:
            try:
                loop.call_soon_threadsafe(callback, *args)
                return
            except RuntimeError:
                # The loop closed under us (server shutting down): nobody is
                # waiting on the queue any more.
                pass
        callback(*args)

    @classmethod
    def _put_now(cls, events: GameUpdateEvents) -> None:
        cls._queue.put_nowait(events)

    @classmethod
    def _drain_now(cls) -> None:
        while not cls._queue.empty():
            cls._queue.get_nowait()
            cls._queue.task_done()

    @classmethod
    def drain(cls) -> None:
        with cls._lock:
            cls._run_on_loop(cls._drain_now)

    @classmethod
    async def put(cls, events: GameUpdateEvents) -> None:
        cls.put_nowait(events)

    @classmethod
    def put_nowait(cls, events: GameUpdateEvents) -> None:
        """Publish events. Safe to call from any thread; never blocks.

        The queue has infinite size so this should never need to block anyway.
        """
        with cls._lock:
            cls._run_on_loop(cls._put_now, events)

    @classmethod
    def _bind_to_running_loop(cls) -> None:
        loop = asyncio.get_running_loop()
        with cls._lock:
            if cls._loop is loop:
                return
            if cls._loop is not None:
                # A new server loop (e.g. a restarted server): an asyncio.Queue
                # stays bound to the first loop that waited on it, so move the
                # pending events to a fresh queue.
                pending: Queue[GameUpdateEvents] = Queue()
                while not cls._queue.empty():
                    pending.put_nowait(cls._queue.get_nowait())
                cls._queue = pending
            cls._loop = loop

    @classmethod
    async def get(cls) -> GameUpdateEvents:
        cls._bind_to_running_loop()
        events = await cls._queue.get()
        cls._queue.task_done()
        return events

    @staticmethod
    @contextmanager
    def event_context() -> Iterator[GameUpdateEvents]:
        events = GameUpdateEvents()
        yield events
        EventStream.put_nowait(events)

"""Global lock serializing every access to the loaded `Game` (WEB-00.4, W2).

`Game` is not thread-safe, yet it is touched from several threads: FastAPI runs the
sync API routes in a worker threadpool, the simulation ticks on a `threading.Timer`
and the Qt main thread passes turns and processes mission results. Every one of those
code paths takes this single re-entrant lock for the duration of its access, so that
they never interleave.

Rules for callers:

* Take the lock with `with game_lock():` (or decorate a route with `@locked`).
* Never wait on another thread while holding it (no modal Qt dialog, no blocking
  queued signal, no `join()`), otherwise that thread may need the lock and deadlock.
* Lock order: take the game lock *before* the sim timer lock
  (`GameLoopTimer._timer_lock`), never the other way around.
"""

from __future__ import annotations

import functools
from collections.abc import Iterator
from contextlib import contextmanager
from threading import RLock
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

_GAME_LOCK = RLock()


@contextmanager
def game_lock() -> Iterator[None]:
    """Hold the global game lock for the duration of the block (re-entrant)."""
    with _GAME_LOCK:
        yield


def locked(func: Callable[P, T]) -> Callable[P, T]:
    """Decorate a sync function (e.g. an API route) to run under the game lock.

    `functools.wraps` keeps the signature visible to FastAPI, which unwraps the
    function to resolve its parameters and dependencies.

    The lock cannot be a FastAPI yield-dependency instead: FastAPI may enter and exit
    a sync dependency on different threadpool threads, and an `RLock` must be released
    by the thread that acquired it.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with _GAME_LOCK:
            return func(*args, **kwargs)

    # Lets tests check that every API route is serialized.
    setattr(wrapper, "takes_game_lock", True)
    return wrapper

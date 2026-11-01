"""The application log kept in memory for the logs screen (WEB-08.2).

`resources/default_logging.yaml` adds `HookableInMemoryHandler` to the root
logger; the web logs screen reads its tail through `GET /logs`, and the Qt logs
window hooks into it for live updates.
"""

from __future__ import annotations

import logging
import typing


class HookableInMemoryHandler(logging.Handler):
    """Hookable in-memory logging handler for the logs screens."""

    _log: str
    _hook: typing.Optional[typing.Callable[[str], None]]

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._log = ""
        self._hook = None

    @property
    def log(self) -> str:
        return self._log

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self._log += msg + "\n"
        if self._hook is not None:
            self._hook(msg)

    def write(self, m: str) -> None:
        pass

    def clearLog(self) -> None:
        self._log = ""

    def setHook(self, hook: typing.Callable[[str], None]) -> None:
        self._hook = hook

    def clearHook(self) -> None:
        self._hook = None


def in_memory_handler() -> HookableInMemoryHandler | None:
    """The in-memory handler of the root logger, if logging set one up."""
    for handler in logging.getLogger().handlers:
        if isinstance(handler, HookableInMemoryHandler):
            return handler
    return None


def log_tail(max_lines: int) -> tuple[list[str], int] | None:
    """The last `max_lines` lines of the log and the total line count.

    None when logging has no in-memory handler (custom logging configuration).
    """
    handler = in_memory_handler()
    if handler is None:
        return None
    lines = handler.log.splitlines()
    tail = lines[-max_lines:] if max_lines > 0 else []
    return tail, len(lines)

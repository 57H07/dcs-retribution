"""The map asks for the game on every launch, with or without a campaign."""

import asyncio
import json
from collections.abc import MutableMapping
from types import SimpleNamespace
from typing import Any

import pytest

from game.server import GameContext
from game.server.app import app


def _get(path: str) -> tuple[int, Any]:
    """Send one GET through the whole ASGI app (routing, lock, response model)."""
    messages: list[MutableMapping[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(body)


def test_game_state_is_null_without_a_campaign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    assert _get("/game/") == (200, None)

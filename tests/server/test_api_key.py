"""WEB-00.6: commands and the event stream require the API key of this launch."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator, MutableMapping
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from fastapi.routing import APIRoute

from game.server import GameContext
from game.server.app import app
from game.server.dependencies import QtContext
from game.server.eventstream.routes import manager
from game.server.security import COMMAND_METHODS, ApiKeyManager
from game.server.settings import ServerSettings

KEY = "test-launch-key"


@pytest.fixture(autouse=True)
def launch_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(ApiKeyManager, "_key", KEY)
    yield


def _scope(
    kind: str, method: str, path: str, headers: dict[str, str], query: str = ""
) -> dict[str, Any]:
    return {
        "type": kind,
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "ws" if kind == "websocket" else "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": query.encode(),
        "headers": [(b"host", b"testserver")]
        + [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "subprotocols": [],
    }


def _request(method: str, path: str, api_key: Optional[str] = None) -> tuple[int, Any]:
    """Send one HTTP request through the whole ASGI app."""
    messages: list[MutableMapping[str, Any]] = []
    headers = {} if api_key is None else {"X-API-Key": api_key}

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(message)

    asyncio.run(app(_scope("http", method, path, headers), receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(body) if body else None


def _open_event_stream(query: str) -> list[MutableMapping[str, Any]]:
    """Open /eventstream and return what the server sends before it waits."""
    messages: list[MutableMapping[str, Any]] = []
    sent_connect = False

    async def receive() -> dict[str, Any]:
        nonlocal sent_connect
        if not sent_connect:
            sent_connect = True
            return {"type": "websocket.connect"}
        await asyncio.sleep(3600)
        return {"type": "websocket.disconnect", "code": 1000}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(message)

    async def run() -> None:
        task = asyncio.create_task(
            app(_scope("websocket", "GET", "/eventstream", {}, query), receive, send)
        )
        # The accepted stream then waits for events forever: give it time to
        # accept or refuse, then stop it.
        for _ in range(50):
            if messages or task.done():
                break
            await asyncio.sleep(0.01)
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    asyncio.run(run())
    return messages


@pytest.fixture
def no_campaign(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    monkeypatch.setattr(QtContext, "_callbacks", None)


# --- commands -----------------------------------------------------------------


def test_command_without_key_is_a_401(no_campaign: None) -> None:
    assert _request("POST", "/game/turn/pass") == (
        401,
        {"detail": "Missing or invalid API key."},
    )


def test_command_with_a_wrong_key_is_a_401(no_campaign: None) -> None:
    status, _ = _request("POST", "/game/turn/pass", api_key="not-the-key")
    assert status == 401


def test_command_with_the_key_reaches_the_route(no_campaign: None) -> None:
    # Past the key check: the route itself refuses (no campaign is loaded).
    assert _request("POST", "/game/turn/pass", api_key=KEY) == (
        409,
        {"detail": "No campaign is loaded."},
    )


def _command_routes() -> list[tuple[str, str]]:
    return sorted(
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
        if method in COMMAND_METHODS
    )


def test_there_are_commands_to_protect() -> None:
    assert ("POST", "/game/turn/pass") in _command_routes()
    assert ("PUT", "/control-points/{cp_id}/destination") in _command_routes()


@pytest.mark.parametrize("method,path", _command_routes())
def test_every_command_route_requires_the_key(method: str, path: str) -> None:
    concrete = path.replace("{waypoint_idx}", "0")
    while "{" in concrete:
        start = concrete.index("{")
        concrete = (
            concrete[:start]
            + "00000000-0000-0000-0000-000000000000"
            + concrete[concrete.index("}") + 1 :]
        )
    status, _ = _request(method, concrete)
    assert status == 401


def test_reads_do_not_need_the_key() -> None:
    status, _ = _request("GET", "/openapi.json")
    assert status == 200


# --- event stream -------------------------------------------------------------


def test_event_stream_without_key_is_refused() -> None:
    messages = _open_event_stream("")
    assert messages[0]["type"] == "websocket.close"
    assert messages[0]["code"] == 1008


def test_event_stream_with_a_wrong_key_is_refused() -> None:
    messages = _open_event_stream("apiKey=wrong")
    assert messages[0]["type"] == "websocket.close"


def test_event_stream_with_the_key_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep the test connection out of the real broadcast list.
    monkeypatch.setattr(manager, "active_connections", [])
    messages = _open_event_stream(f"apiKey={KEY}")
    assert messages[0]["type"] == "websocket.accept"


# --- key ----------------------------------------------------------------------


def test_key_is_random_per_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ApiKeyManager, "_key", None)
    first = ApiKeyManager.key()
    assert len(first) >= 32
    assert ApiKeyManager.key() == first
    monkeypatch.setattr(ApiKeyManager, "_key", None)
    assert ApiKeyManager.key() != first


def test_key_can_be_fixed_for_a_standalone_dev_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ApiKeyManager, "_key", None)
    monkeypatch.setenv("SERVER_API_KEY", "dev-key")
    ServerSettings.get.cache_clear()
    try:
        assert ApiKeyManager.key() == "dev-key"
    finally:
        ServerSettings.get.cache_clear()


def test_wrong_key_is_not_valid() -> None:
    assert ApiKeyManager.is_valid(KEY)
    assert not ApiKeyManager.is_valid(None)
    assert not ApiKeyManager.is_valid("")
    assert not ApiKeyManager.is_valid(KEY + "x")

"""WEB-00.5: command conventions, shown on the example command POST /game/turn/pass."""

from __future__ import annotations

import asyncio
import json
from collections.abc import MutableMapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from game.commands import CommandError, skip_turn
from game.game import Game, TurnState
from game.server import GameContext
from game.server.app import app
from game.server.dependencies import QtCallbacks, QtContext
from game.server.eventstream import EventStream
from game.server.openapischema import DEFAULT_OUTPUT, openapi_schema, render
from game.sim import GameUpdateEvents


class _FakeGame:
    """Stands in for Game: counts turns and reports a scripted campaign state."""

    def __init__(self, state_after: TurnState = TurnState.CONTINUE) -> None:
        self.turn = 1
        self.state = TurnState.CONTINUE
        self.state_after = state_after
        self.passes: list[bool] = []

    def check_win_loss(self) -> TurnState:
        return self.state

    def pass_turn(self, no_action: bool = False) -> None:
        self.passes.append(no_action)
        self.turn += 1
        self.state = self.state_after


def _qt_callbacks(received: list[TurnState]) -> QtCallbacks:
    def ignore(_: Any) -> None:
        pass

    return QtCallbacks(ignore, ignore, ignore, ignore, turn_passed=received.append)


@pytest.fixture
def loaded_game(monkeypatch: pytest.MonkeyPatch) -> _FakeGame:
    game = _FakeGame()
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=game), raising=False
    )
    monkeypatch.setattr(QtContext, "_callbacks", None)
    return game


def _post(path: str) -> tuple[int, Any]:
    """Send one POST through the whole ASGI app (routing, lock, errors, JSON)."""
    messages: list[MutableMapping[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
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


# --- business side: game.commands -------------------------------------------


def test_skip_turn_passes_the_turn_without_action() -> None:
    game = _FakeGame()
    assert skip_turn(game) is TurnState.CONTINUE  # type: ignore[arg-type]
    assert game.passes == [True]
    assert game.turn == 2


def test_skip_turn_reports_the_campaign_state_after_the_turn() -> None:
    game = _FakeGame(state_after=TurnState.WIN)
    assert skip_turn(game) is TurnState.WIN  # type: ignore[arg-type]


def test_skip_turn_refuses_once_the_campaign_is_over() -> None:
    game = _FakeGame()
    game.state = TurnState.LOSS
    with pytest.raises(CommandError) as exc:
        skip_turn(game)  # type: ignore[arg-type]
    assert exc.value.status_code == 409
    assert "over" in exc.value.message
    assert game.passes == []


def test_skip_turn_publishes_a_new_turn_event(monkeypatch: pytest.MonkeyPatch) -> None:
    """Open web screens reload on `new_turn`: the real Game.pass_turn must send it."""
    game = Game.__new__(Game)
    monkeypatch.setattr(game, "check_win_loss", lambda: TurnState.CONTINUE)
    monkeypatch.setattr(game, "finish_turn", lambda events, no_action: None)
    monkeypatch.setattr(game, "initialize_turn", lambda events: events.begin_new_turn())
    monkeypatch.setattr("game.game.persistency.autosave", lambda g: None)
    published: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", published.append)

    skip_turn(game)

    assert [events.new_turn for events in published] == [True]


# --- HTTP side: POST /game/turn/pass ----------------------------------------


def test_pass_turn_route_returns_the_new_turn(loaded_game: _FakeGame) -> None:
    status, body = _post("/game/turn/pass")
    assert status == 200
    assert body == {"turn": 2, "campaign_state": "continue"}
    assert loaded_game.passes == [True]


def test_pass_turn_route_reports_victory(
    loaded_game: _FakeGame,
) -> None:
    loaded_game.state_after = TurnState.WIN
    assert _post("/game/turn/pass") == (200, {"turn": 2, "campaign_state": "win"})


def test_pass_turn_route_refreshes_qt(
    loaded_game: _FakeGame, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[TurnState] = []
    monkeypatch.setattr(QtContext, "_callbacks", _qt_callbacks(received))
    _post("/game/turn/pass")
    assert received == [TurnState.CONTINUE]


def test_business_error_is_a_409_with_a_readable_message(
    loaded_game: _FakeGame,
) -> None:
    loaded_game.state = TurnState.WIN
    status, body = _post("/game/turn/pass")
    assert status == 409
    assert body == {"detail": "The campaign is over: no further turn can be played."}
    assert loaded_game.passes == []


def test_pass_turn_without_a_campaign_is_a_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=None), raising=False
    )
    assert _post("/game/turn/pass") == (409, {"detail": "No campaign is loaded."})


def test_command_error_can_choose_its_status() -> None:
    assert CommandError("nope", status_code=422).status_code == 422
    assert CommandError("nope").status_code == 409


# --- offline client generation ----------------------------------------------


def test_openapi_documents_the_command_and_its_errors() -> None:
    operation = openapi_schema()["paths"]["/game/turn/pass"]["post"]
    assert operation["operationId"] == "pass_turn"
    assert set(operation["responses"]) == {"200", "409"}
    error_schema = operation["responses"]["409"]["content"]["application/json"]
    assert error_schema["schema"]["$ref"].endswith("/CommandErrorJs")


def test_openapi_schema_has_no_tuple_enums() -> None:
    """Codegen chokes on enums whose values are arrays (formerly TgoJs.task)."""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.get("enum", []):
                assert not isinstance(value, list), node
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(openapi_schema())


def test_required_nullable_fields_become_optional() -> None:
    schemas = openapi_schema()["components"]["schemas"]
    tgo = schemas["TgoJs"]
    assert "destination" not in tgo["required"]
    assert "anyOf" not in tgo["properties"]["destination"]


def test_committed_openapi_json_is_up_to_date() -> None:
    """Regenerate with `python -m game.server.openapischema`, then
    `npm run regenerate-api` in client/ (see docs/dev/api-commands.md)."""
    committed = Path(DEFAULT_OUTPUT).read_text(encoding="utf-8")
    assert committed.replace("\r\n", "\n") == render(openapi_schema())

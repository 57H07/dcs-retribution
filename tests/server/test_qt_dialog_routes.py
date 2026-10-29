"""WEB-00.3: the web shell opens the Qt screens it does not have yet via /qt/*."""

from __future__ import annotations

import asyncio
import json
from collections.abc import MutableMapping
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from game.gamelock import _GAME_LOCK
from game.server import GameContext
from game.server.app import app
from game.server.dependencies import QtCallbacks, QtContext
from game.server.qt.models import QtDialog
from game.server.security import ApiKeyManager


class _Recorder:
    """Qt callbacks that record what they were asked to open, and lock ownership."""

    def __init__(self) -> None:
        self.dialogs: list[QtDialog] = []
        self.packages: list[Any] = []
        self.lock_held: list[bool] = []

    def _held(self) -> None:
        self.lock_held.append(_GAME_LOCK._is_owned())  # type: ignore[attr-defined]

    def open_dialog(self, dialog: QtDialog) -> None:
        self._held()
        self.dialogs.append(dialog)

    def edit_package(self, package: Any) -> None:
        self.packages.append(package)

    def callbacks(self) -> QtCallbacks:
        def ignore(_: Any) -> None:
            pass

        return QtCallbacks(
            ignore,
            ignore,
            ignore,
            ignore,
            open_dialog=self.open_dialog,
            edit_package=self.edit_package,
        )


def _set_game(monkeypatch: pytest.MonkeyPatch, game: Any) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=game), raising=False
    )


@pytest.fixture
def qt(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    recorder = _Recorder()
    monkeypatch.setattr(QtContext, "_callbacks", recorder.callbacks())
    return recorder


def _post(path: str, api_key: str | None = None) -> tuple[int, Any]:
    """Send one POST through the whole ASGI app (key, routing, lock, errors)."""
    messages: list[MutableMapping[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(message)

    key = ApiKeyManager.key() if api_key is None else api_key
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
        "headers": [(b"host", b"testserver"), (b"x-api-key", key.encode())],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(body) if body else None


@pytest.mark.parametrize("dialog", list(QtDialog))
def test_every_dialog_opens_with_a_campaign(
    dialog: QtDialog, qt: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(turn=3))
    assert _post(f"/qt/dialogs/{dialog.value}") == (204, None)
    assert qt.dialogs == [dialog]
    # Queued while the route held the game lock (the callback only emits a signal).
    assert qt.lock_held == [True]


def test_dialogs_needing_a_campaign_are_refused_without_one(
    qt: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, None)
    assert _post("/qt/dialogs/stats") == (409, {"detail": "No campaign is loaded."})
    assert _post("/qt/dialogs/preferences") == (204, None)
    assert qt.dialogs == [QtDialog.PREFERENCES]


def test_menu_actions_without_a_campaign() -> None:
    assert not QtDialog.PREFERENCES.needs_game
    assert not QtDialog.LOGS.needs_game
    assert QtDialog.STATS.needs_game
    assert QtDialog.AIR_WING.needs_game


def test_take_off_is_refused_before_the_campaign_begins(
    qt: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(turn=0))
    status, body = _post("/qt/dialogs/take-off")
    assert status == 409
    assert "Begin the campaign" in body["detail"]
    assert qt.dialogs == []


def test_unknown_dialog_is_rejected(
    qt: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(turn=3))
    status, _ = _post("/qt/dialogs/self-destruct")
    assert status == 422
    assert qt.dialogs == []


def test_dialogs_need_the_api_key(
    qt: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(turn=3))
    status, _ = _post("/qt/dialogs/stats", api_key="wrong")
    assert status == 401
    assert qt.dialogs == []


def test_without_a_qt_window_the_route_answers_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def ignore(_: Any) -> None:
        pass

    monkeypatch.setattr(
        QtContext, "_callbacks", QtCallbacks(ignore, ignore, ignore, ignore)
    )
    _set_game(monkeypatch, SimpleNamespace(turn=3))
    assert _post("/qt/dialogs/stats")[0] == 503


def test_edit_package_opens_the_package_of_the_flight(
    qt: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = object()
    flight_id = uuid4()
    flights = {flight_id: SimpleNamespace(package=package)}
    _set_game(
        monkeypatch,
        SimpleNamespace(
            db=SimpleNamespace(flights=SimpleNamespace(get=flights.__getitem__))
        ),
    )
    assert _post(f"/qt/edit-package/flight/{flight_id}") == (204, None)
    assert qt.packages == [package]

    status, body = _post(f"/qt/edit-package/flight/{uuid4()}")
    assert status == 404
    assert "no flight" in body["detail"]
    assert qt.packages == [package]


@pytest.mark.parametrize(
    "dialog", ["new-game", "open-game", "save-game", "save-game-as", "quit"]
)
def test_file_actions_moved_to_the_native_bridge(
    dialog: str, qt: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(turn=3))
    assert _post(f"/qt/dialogs/{dialog}")[0] == 422
    assert _post("/qt/links/github")[0] == 404
    assert qt.dialogs == []

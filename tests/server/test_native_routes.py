"""WEB-00.7: native bridge over HTTP (file dialogs, folders, links, quit)."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import game
from game import persistency
from game.gamelock import _GAME_LOCK
from game.native import ExternalLink, NativeBridge, NativeContext, NativeFolder
from game.native import files
from game.server import GameContext
from tests.server.test_qt_dialog_routes import _post


def _lock_is_free() -> bool:
    """True when neither this thread nor any other holds the game lock."""
    if _GAME_LOCK._is_owned():  # type: ignore[attr-defined]
        return False
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


class FakeBridge(NativeBridge):
    """Answers the dialogs with a scripted path and records every call."""

    def __init__(self, answer: str | None = None) -> None:
        self.answer = answer
        self.asked: list[tuple[str, str]] = []
        self.lock_free_while_asking: list[bool] = []
        self.loaded: list[tuple[Any, str]] = []
        self.saved: list[str] = []
        self.calls: list[Any] = []
        self.during_dialog: Any = None

    def _ask(self, kind: str, start: str) -> str | None:
        self.asked.append((kind, start))
        self.lock_free_while_asking.append(_lock_is_free())
        if self.during_dialog is not None:
            self.during_dialog()
        return self.answer

    def choose_open_path(self, start: str) -> str | None:
        return self._ask("open", start)

    def choose_save_path(self, start: str) -> str | None:
        return self._ask("save", start)

    def game_loaded(self, game: Any, path: str) -> None:
        self.loaded.append((game, path))

    def game_saved(self, path: str) -> None:
        self.saved.append(path)

    def open_new_game(self) -> None:
        self.calls.append("new-game")

    def open_folder(self, path: Path) -> None:
        self.calls.append(path)

    def open_url(self, url: str) -> None:
        self.calls.append(url)

    def quit(self) -> None:
        self.calls.append("quit")


@pytest.fixture
def bridge(monkeypatch: pytest.MonkeyPatch) -> FakeBridge:
    fake = FakeBridge()
    monkeypatch.setattr(NativeContext, "_bridge", fake)
    return fake


@pytest.fixture
def written(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stubs persistency.save_game, recording the path of each write."""
    paths: list[str] = []

    def save_game(game: Any) -> bool:
        paths.append(game.savepath)
        return True

    monkeypatch.setattr(persistency, "save_game", save_game)
    return paths


def _set_game(monkeypatch: pytest.MonkeyPatch, current: Any) -> SimpleNamespace:
    model = SimpleNamespace(game=current)
    monkeypatch.setattr(GameContext, "_game_model", model, raising=False)
    return model


def test_save_with_a_known_path_writes_without_a_dialog(
    bridge: FakeBridge, written: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(savepath="C:/saves/a.retribution"))
    assert _post("/native/save") == (
        200,
        {"outcome": "saved", "path": "C:/saves/a.retribution"},
    )
    assert bridge.asked == []
    assert written == ["C:/saves/a.retribution"]
    assert bridge.saved == ["C:/saves/a.retribution"]


def test_save_without_a_path_asks_without_holding_the_lock(
    bridge: FakeBridge, written: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    current = SimpleNamespace(savepath=None)
    _set_game(monkeypatch, current)
    bridge.answer = "C:/saves/new.retribution"
    assert _post("/native/save") == (
        200,
        {"outcome": "saved", "path": "C:/saves/new.retribution"},
    )
    assert bridge.asked == [("save", str(persistency.save_dir()))]
    assert bridge.lock_free_while_asking == [True]
    assert current.savepath == "C:/saves/new.retribution"
    assert written == ["C:/saves/new.retribution"]
    assert bridge.saved == ["C:/saves/new.retribution"]


def test_save_as_always_asks_from_the_current_file(
    bridge: FakeBridge, written: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(savepath="C:/saves/a.retribution"))
    bridge.answer = "C:/saves/b.retribution"
    assert _post("/native/save-as") == (
        200,
        {"outcome": "saved", "path": "C:/saves/b.retribution"},
    )
    assert bridge.asked == [("save", "C:/saves/a.retribution")]
    assert bridge.lock_free_while_asking == [True]
    assert written == ["C:/saves/b.retribution"]


def test_cancelled_save_as_writes_nothing(
    bridge: FakeBridge, written: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    current = SimpleNamespace(savepath="C:/saves/a.retribution")
    _set_game(monkeypatch, current)
    assert _post("/native/save-as") == (200, {"outcome": "cancelled", "path": None})
    assert written == []
    assert bridge.saved == []
    assert current.savepath == "C:/saves/a.retribution"


def test_failed_save_keeps_the_previous_path(
    bridge: FakeBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = SimpleNamespace(savepath="C:/saves/a.retribution")
    _set_game(monkeypatch, current)
    monkeypatch.setattr(persistency, "save_game", lambda game: False)
    bridge.answer = "Z:/readonly/b.retribution"
    status, body = _post("/native/save-as")
    assert status == 500
    assert body == {
        "detail": "Could not save the campaign to Z:/readonly/b.retribution."
    }
    assert current.savepath == "C:/saves/a.retribution"
    assert bridge.saved == []


def test_save_needs_a_campaign(
    bridge: FakeBridge, written: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, None)
    assert _post("/native/save") == (409, {"detail": "No campaign is loaded."})
    assert _post("/native/save-as") == (409, {"detail": "No campaign is loaded."})
    assert bridge.asked == []


def test_save_as_refuses_when_the_campaign_changed_during_the_dialog(
    bridge: FakeBridge, written: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    model = _set_game(monkeypatch, SimpleNamespace(savepath=None))
    bridge.answer = "C:/saves/b.retribution"
    bridge.during_dialog = lambda: setattr(model, "game", SimpleNamespace())
    status, body = _post("/native/save-as")
    assert status == 409
    assert "nothing was saved" in body["detail"]
    assert written == []


def test_open_loads_migrates_and_hands_the_game_to_the_shell(
    bridge: FakeBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(savepath="C:/saves/a.retribution"))
    loaded = SimpleNamespace(savepath="C:/saves/old.liberation")
    migrated: list[tuple[Any, bool]] = []
    monkeypatch.setattr(persistency, "load_game", lambda path: loaded)
    monkeypatch.setattr(
        game, "Migrator", lambda g, is_liberation: migrated.append((g, is_liberation))
    )
    bridge.answer = "C:/saves/old.liberation"
    assert _post("/native/open") == (
        200,
        {"outcome": "opened", "path": "C:/saves/old.liberation"},
    )
    assert bridge.asked == [("open", "C:/saves/a.retribution")]
    assert bridge.lock_free_while_asking == [True]
    assert migrated == [(loaded, True)]
    assert bridge.loaded == [(loaded, "C:/saves/old.liberation")]


def test_open_works_without_a_campaign_and_can_be_cancelled(
    bridge: FakeBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, None)
    assert _post("/native/open") == (200, {"outcome": "cancelled", "path": None})
    assert bridge.asked == [("open", str(persistency.save_dir()))]
    assert bridge.loaded == []


def test_open_reports_an_incompatible_save(
    bridge: FakeBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, None)
    bridge.answer = "C:/saves/broken.retribution"
    monkeypatch.setattr(persistency, "load_game", lambda path: None)
    status, body = _post("/native/open")
    assert status == 409
    assert body["detail"].startswith("Incompatible save file")

    def fail(g: Any, is_liberation: bool) -> None:
        raise ValueError("unknown faction")

    monkeypatch.setattr(persistency, "load_game", lambda path: SimpleNamespace())
    monkeypatch.setattr(game, "Migrator", fail)
    status, body = _post("/native/open")
    assert status == 409
    assert body["detail"].startswith("Incompatible save file")
    assert bridge.loaded == []


def test_only_one_file_dialog_at_a_time(
    bridge: FakeBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(savepath=None))
    with files._DIALOG:
        assert _post("/native/open") == (
            409,
            {"detail": "A file dialog is already open."},
        )
    assert bridge.asked == []
    # The guard is released after a dialog, even a cancelled one.
    assert _post("/native/open") == (200, {"outcome": "cancelled", "path": None})
    assert _post("/native/save-as") == (200, {"outcome": "cancelled", "path": None})


def test_new_game_quit_folders_and_links(
    bridge: FakeBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, None)
    assert _post("/native/new-game") == (204, None)
    assert _post("/native/quit") == (204, None)
    assert _post("/native/open-folder/saves") == (204, None)
    assert _post("/native/open-link/discord") == (204, None)
    assert bridge.calls == [
        "new-game",
        "quit",
        persistency.save_dir(),
        ExternalLink.DISCORD.url,
    ]
    assert _post("/native/open-link/elsewhere")[0] == 422


@pytest.mark.parametrize("link", list(ExternalLink))
def test_every_link_opens_an_https_page(link: ExternalLink, bridge: FakeBridge) -> None:
    assert _post(f"/native/open-link/{link.value}") == (204, None)
    assert bridge.calls == [link.url]
    assert link.url.startswith("https://")


def test_missions_folder_is_created(bridge: FakeBridge) -> None:
    assert _post("/native/open-folder/missions") == (204, None)
    assert bridge.calls == [NativeFolder.MISSIONS.path()]
    assert NativeFolder.MISSIONS.path().is_dir()


@pytest.mark.parametrize(
    "path", ["/native/save", "/native/open", "/native/quit", "/native/new-game"]
)
def test_native_routes_need_a_shell_and_the_api_key(
    path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_game(monkeypatch, SimpleNamespace(savepath="C:/saves/a.retribution"))
    monkeypatch.setattr(NativeContext, "_bridge", None)
    assert _post(path) == (503, {"detail": "The native shell is not available."})
    monkeypatch.setattr(NativeContext, "_bridge", FakeBridge())
    assert _post(path, api_key="wrong")[0] == 401

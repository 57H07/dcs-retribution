"""WEB-05.1: waiting for the mission result (state.json watch, load, abort, accept)."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from game.commands import (
    CommandError,
    MissionResultStatus,
    MissionResultWaiter,
    abort_mission,
    accept_results,
)
from game.commands import missionresult as missionresult_module
from game.debriefing import SideLossCounts
from game.game import TurnState
from game.native import NativeContext
from game.polldebriefingfilethread import PollDebriefingFileThread
from game.server import GameContext
from game.server.dependencies import QtCallbacks, QtContext
from game.server.eventstream import EventStream
from game.server.eventstream.models import GameUpdateEventsJs
from game.server.missionresult import MissionResultContext
from game.sim import GameUpdateEvents
from tests.server.test_command_view_commands import _request
from tests.server.test_native_routes import FakeBridge, _lock_is_free

MIZ = Path("M") / "retribution_nextturn.miz"


# --- fakes -------------------------------------------------------------------


def _counts(aircraft: int) -> SideLossCounts:
    return SideLossCounts(aircraft, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def _debriefing(data: dict[str, Any]) -> Any:
    return SimpleNamespace(
        state_data=SimpleNamespace(mission_ended=data.get("mission_ended", False)),
        player_country="Ukraine",
        enemy_country="Russia",
        loss_counts=lambda player: _counts(2 if player.is_blue else 5),
        data=data,
    )


class _MissionSim:
    """Stands in for MissionSimulation, as the poll thread sees it."""

    def __init__(self) -> None:
        # The .miz was written 100 s ago; older state.json files are stale.
        self.miz_generated_at = time.time() - 100
        self.lock_held: list[bool] = []

    def debrief_current_state(self, path: Path, force_end: bool = False) -> Any:
        self.lock_held.append(_lock_held_here())
        data = json.loads(path.read_text())
        if force_end:
            data["mission_ended"] = True
        return _debriefing(data)


def _lock_held_here() -> bool:
    from game.gamelock import _GAME_LOCK

    return bool(_GAME_LOCK._is_owned())  # type: ignore[attr-defined]


class _Sim:
    """Stands in for SimController: real poll thread on a temporary state.json."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self.mission = _MissionSim()
        self.watches: list[PollDebriefingFileThread] = []
        self.calls: list[Any] = []

    def wait_for_debriefing(
        self,
        callback: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> PollDebriefingFileThread:
        thread = PollDebriefingFileThread(
            callback,
            cast(Any, self.mission),
            on_error,
            state_path=self.state_path,
            poll_interval=0.01,
        )
        thread.start()
        self.watches.append(thread)
        return thread

    def debrief_current_state(self, state_path: Path, force_end: bool = False) -> Any:
        self.calls.append(("debrief", state_path, force_end))
        return self.mission.debrief_current_state(state_path, force_end)

    def process_results(self, debriefing: Any) -> None:
        self.calls.append(("process", debriefing.data))

    def set_game(self, game: Any) -> None:
        self.calls.append("set_game")


def _write_state(path: Path, data: dict[str, Any] | str, age: float = 0) -> None:
    """Write state.json with an increasing mtime (`age` seconds in the past)."""
    path.write_text(data if isinstance(data, str) else json.dumps(data))
    stamp = time.time() - age
    os.utime(path, (stamp, stamp))


def _wait_until(condition: Callable[[], bool], timeout: float = 5) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("condition not met in time")
        time.sleep(0.01)


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "state.json"


@pytest.fixture
def sim(state_path: Path) -> Iterator[_Sim]:
    fake = _Sim(state_path)
    yield fake
    for watch in fake.watches:
        watch.stop()
        watch.join(timeout=5)


@pytest.fixture
def changes() -> list[MissionResultStatus]:
    return []


@pytest.fixture
def waiter(
    state_path: Path, changes: list[MissionResultStatus]
) -> Iterator[MissionResultWaiter]:
    def on_change() -> None:
        changes.append(result.snapshot().status)

    result = MissionResultWaiter(on_change, state_path)
    MissionResultContext.set(result)
    yield result
    result.stop()
    MissionResultContext.set(None)


# --- game.commands.missionresult ---------------------------------------------


def test_detection_follows_state_json(
    waiter: MissionResultWaiter, sim: _Sim, state_path: Path
) -> None:
    assert waiter.snapshot().status is MissionResultStatus.IDLE

    # A state.json older than the mission is a leftover: still waiting.
    _write_state(state_path, {"mission_ended": True}, age=200)
    waiter.start(sim, MIZ)
    time.sleep(0.1)
    snapshot = waiter.snapshot()
    assert snapshot.status is MissionResultStatus.WAITING
    assert snapshot.miz_path == MIZ
    assert snapshot.state_path == state_path.absolute()
    assert snapshot.debriefing is None

    # DCS writes the state of the mission being played.
    _write_state(state_path, {"mission_ended": False}, age=50)
    _wait_until(lambda: waiter.snapshot().status is MissionResultStatus.DETECTED)
    assert not waiter.snapshot().mission_ended
    with pytest.raises(CommandError, match="still being played"):
        waiter.final_result()

    # Read while DCS is still writing it: parse error, the watch retries.
    _write_state(state_path, '{"mission_ended": tr', age=40)
    _wait_until(lambda: waiter.snapshot().status is MissionResultStatus.ERROR)
    assert "state.json" in (waiter.snapshot().error or "")

    # The mission is over: detected, and the watch stops on its own.
    _write_state(state_path, {"mission_ended": True}, age=30)
    _wait_until(lambda: waiter.snapshot().mission_ended)
    snapshot = waiter.snapshot()
    assert snapshot.status is MissionResultStatus.DETECTED
    assert snapshot.error is None
    sim.watches[0].join(timeout=5)
    assert not sim.watches[0].is_alive()
    assert waiter.final_result() is snapshot.debriefing


def test_the_game_lock_is_only_held_to_read_state_json(
    waiter: MissionResultWaiter, sim: _Sim, state_path: Path
) -> None:
    waiter.start(sim, MIZ)
    for _ in range(5):
        assert _lock_is_free()
        time.sleep(0.02)
    _write_state(state_path, {"mission_ended": True})
    _wait_until(lambda: waiter.snapshot().mission_ended)
    assert sim.mission.lock_held == [True]


def test_status_changes_are_published(
    waiter: MissionResultWaiter,
    sim: _Sim,
    state_path: Path,
    changes: list[MissionResultStatus],
) -> None:
    waiter.start(sim, MIZ)
    _write_state(state_path, {"mission_ended": True})
    _wait_until(lambda: MissionResultStatus.DETECTED in changes)
    waiter.stop()
    assert changes == [
        MissionResultStatus.WAITING,
        MissionResultStatus.DETECTED,
        MissionResultStatus.IDLE,
    ]


def test_stop_ends_the_watch_and_ignores_late_results(
    waiter: MissionResultWaiter, sim: _Sim, state_path: Path
) -> None:
    waiter.start(sim, MIZ)
    waiter.stop()
    sim.watches[0].join(timeout=5)
    assert not sim.watches[0].is_alive()
    _write_state(state_path, {"mission_ended": True})
    time.sleep(0.1)
    assert waiter.snapshot().status is MissionResultStatus.IDLE


def test_a_new_mission_replaces_the_previous_watch(
    waiter: MissionResultWaiter, sim: _Sim
) -> None:
    waiter.start(sim, MIZ)
    waiter.start(sim, Path("other.miz"))
    sim.watches[0].join(timeout=5)
    assert not sim.watches[0].is_alive()
    assert sim.watches[1].is_alive()
    assert waiter.snapshot().miz_path == Path("other.miz")


def test_load_takes_a_file_as_the_final_result(
    waiter: MissionResultWaiter, sim: _Sim, tmp_path: Path
) -> None:
    with pytest.raises(CommandError, match="No mission is waiting"):
        waiter.load(sim, tmp_path / "picked.json")

    picked = tmp_path / "picked.json"
    _write_state(picked, {"mission_ended": False, "kills": 3})
    waiter.start(sim, MIZ)
    debriefing = waiter.load(sim, picked)
    assert sim.calls == [("debrief", picked, True)]
    assert debriefing.state_data.mission_ended
    assert waiter.snapshot().status is MissionResultStatus.DETECTED
    sim.watches[0].join(timeout=5)
    assert not sim.watches[0].is_alive()


def test_load_reports_an_unreadable_file(
    waiter: MissionResultWaiter, sim: _Sim, tmp_path: Path
) -> None:
    picked = tmp_path / "broken.json"
    picked.write_text("{not json")
    waiter.start(sim, MIZ)
    with pytest.raises(CommandError, match="Could not read broken.json"):
        waiter.load(sim, picked)
    assert waiter.snapshot().status is MissionResultStatus.WAITING


class _Flight:
    def __init__(self) -> None:
        self.state: Any = "in flight"


def _game() -> Any:
    flights = [_Flight() for _ in range(2)]
    released: list[str] = []
    return SimpleNamespace(
        db=SimpleNamespace(flights=SimpleNamespace(objects=dict(enumerate(flights)))),
        settings="settings",
        theater=SimpleNamespace(
            controlpoints=[
                SimpleNamespace(release_parking_slots=lambda: released.append("cp"))
            ]
        ),
        released=released,
        turn=4,
        pass_turn=lambda: None,
        check_win_loss=lambda: TurnState.CONTINUE,
    )


@pytest.fixture
def fake_uninitialized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        missionresult_module,
        "Uninitialized",
        lambda flight, settings: ("planned", settings),
    )


def test_abort_resets_flights_and_parking(sim: _Sim, fake_uninitialized: None) -> None:
    game = _game()
    events = abort_mission(game, sim)
    assert sim.calls == ["set_game"]
    flights = list(game.db.flights.objects.values())
    assert [f.state for f in flights] == [("planned", "settings")] * 2
    assert events.updated_flights == set(flights)
    assert game.released == ["cp"]


def test_accept_processes_the_result_then_passes_the_turn(sim: _Sim) -> None:
    order: list[str] = []
    game = SimpleNamespace(pass_turn=lambda: order.append("pass_turn"))
    debriefing = _debriefing({"mission_ended": True})
    accept_results(cast(Any, game), sim, debriefing)
    assert sim.calls == [("process", {"mission_ended": True})]
    assert order == ["pass_turn"]


def test_mission_result_event_reaches_the_client() -> None:
    events = GameUpdateEvents().update_mission_result()
    assert not events.empty
    assert GameUpdateEventsJs.from_events(events, None).mission_result_updated


# --- HTTP side -----------------------------------------------------------------


class _Qt:
    def __init__(self) -> None:
        self.accepted: list[Any] = []
        self.game_changed = 0

    def callbacks(self) -> QtCallbacks:
        def ignore(_: Any) -> None:
            pass

        def changed() -> None:
            self.game_changed += 1

        return QtCallbacks(
            ignore,
            ignore,
            ignore,
            ignore,
            game_changed=changed,
            results_accepted=self.accepted.append,
        )


@pytest.fixture
def qt(monkeypatch: pytest.MonkeyPatch) -> _Qt:
    recorder = _Qt()
    monkeypatch.setattr(QtContext, "_callbacks", recorder.callbacks())
    return recorder


@pytest.fixture
def bridge(monkeypatch: pytest.MonkeyPatch) -> FakeBridge:
    fake = FakeBridge()
    monkeypatch.setattr(NativeContext, "_bridge", fake)
    return fake


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[GameUpdateEvents]:
    events: list[GameUpdateEvents] = []
    monkeypatch.setattr(EventStream, "put_nowait", events.append)
    return events


def _load_game(monkeypatch: pytest.MonkeyPatch, game: Any, sim: _Sim) -> None:
    monkeypatch.setattr(
        GameContext,
        "_game_model",
        SimpleNamespace(game=game, sim_controller=sim),
        raising=False,
    )


def test_status_route(
    monkeypatch: pytest.MonkeyPatch,
    waiter: MissionResultWaiter,
    sim: _Sim,
    state_path: Path,
) -> None:
    _load_game(monkeypatch, _game(), sim)
    status, body = _request("GET", "/game/mission/result")
    assert status == 200
    assert body["status"] == "idle"
    assert body["miz_path"] is None
    assert body["losses"] == []

    waiter.start(sim, MIZ)
    _write_state(state_path, {"mission_ended": True})
    _wait_until(lambda: waiter.snapshot().mission_ended)
    status, body = _request("GET", "/game/mission/result")
    assert body["status"] == "detected"
    assert body["miz_path"] == str(MIZ)
    assert body["state_path"] == str(state_path.absolute())
    assert body["mission_ended"] is True
    assert body["error"] is None
    assert (body["player_country"], body["enemy_country"]) == ("Ukraine", "Russia")
    assert body["losses"][0] == {"label": "Aircraft lost", "blue": 2, "red": 5}
    assert len(body["losses"]) == 11


def test_load_file_route_asks_without_holding_the_lock(
    monkeypatch: pytest.MonkeyPatch,
    waiter: MissionResultWaiter,
    sim: _Sim,
    bridge: FakeBridge,
    tmp_path: Path,
    state_path: Path,
) -> None:
    _load_game(monkeypatch, _game(), sim)
    status, body = _request("POST", "/game/mission/result/file")
    assert status == 409
    assert body["detail"] == "No mission is waiting for its result."
    assert bridge.asked == []

    waiter.start(sim, MIZ)
    picked = tmp_path / "picked.json"
    _write_state(picked, {"mission_ended": False})
    bridge.answer = str(picked)
    status, body = _request("POST", "/game/mission/result/file")
    assert status == 200
    assert bridge.asked == [("file", str(state_path.absolute().parent))]
    assert bridge.lock_free_while_asking == [True]
    assert body["status"] == "detected"
    assert body["mission_ended"] is True


def test_cancelled_load_changes_nothing(
    monkeypatch: pytest.MonkeyPatch,
    waiter: MissionResultWaiter,
    sim: _Sim,
    bridge: FakeBridge,
) -> None:
    _load_game(monkeypatch, _game(), sim)
    waiter.start(sim, MIZ)
    status, body = _request("POST", "/game/mission/result/file")
    assert status == 200
    assert body["status"] == "waiting"
    assert sim.calls == []


def test_load_of_a_broken_file_is_refused(
    monkeypatch: pytest.MonkeyPatch,
    waiter: MissionResultWaiter,
    sim: _Sim,
    bridge: FakeBridge,
    tmp_path: Path,
) -> None:
    _load_game(monkeypatch, _game(), sim)
    waiter.start(sim, MIZ)
    picked = tmp_path / "broken.json"
    picked.write_text("{")
    bridge.answer = str(picked)
    status, body = _request("POST", "/game/mission/result/file")
    assert status == 409
    assert body["detail"].startswith("Could not read broken.json")


def test_cancel_route_aborts_the_mission(
    monkeypatch: pytest.MonkeyPatch,
    waiter: MissionResultWaiter,
    sim: _Sim,
    qt: _Qt,
    published: list[GameUpdateEvents],
    fake_uninitialized: None,
) -> None:
    game = _game()
    _load_game(monkeypatch, game, sim)
    waiter.start(sim, MIZ)
    published.clear()
    assert _request("POST", "/game/mission/result/cancel") == (204, None)
    assert waiter.snapshot().status is MissionResultStatus.IDLE
    sim.watches[0].join(timeout=5)
    assert not sim.watches[0].is_alive()
    assert sim.calls == ["set_game"]
    assert game.released == ["cp"]
    assert qt.game_changed == 1
    assert len(published[-1].updated_flights) == 2


def test_cancel_route_needs_a_campaign(
    monkeypatch: pytest.MonkeyPatch, waiter: MissionResultWaiter, sim: _Sim
) -> None:
    _load_game(monkeypatch, None, sim)
    status, body = _request("POST", "/game/mission/result/cancel")
    assert status == 409
    assert body["detail"] == "No campaign is loaded."


def test_accept_route(
    monkeypatch: pytest.MonkeyPatch,
    waiter: MissionResultWaiter,
    sim: _Sim,
    qt: _Qt,
    state_path: Path,
) -> None:
    game = _game()
    _load_game(monkeypatch, game, sim)
    status, body = _request("POST", "/game/mission/result/accept")
    assert status == 409
    assert body["detail"] == "No mission result has been received yet."

    waiter.start(sim, MIZ)
    _write_state(state_path, {"mission_ended": False})
    _wait_until(lambda: waiter.snapshot().status is MissionResultStatus.DETECTED)
    status, body = _request("POST", "/game/mission/result/accept")
    assert status == 409
    assert body["detail"] == "The mission is still being played."

    _write_state(state_path, {"mission_ended": True}, age=-5)
    _wait_until(lambda: waiter.snapshot().mission_ended)
    status, body = _request("POST", "/game/mission/result/accept")
    assert status == 200
    assert body == {"turn": 4, "campaign_state": "continue"}
    assert ("process", {"mission_ended": True}) in sim.calls
    assert waiter.snapshot().status is MissionResultStatus.IDLE
    assert [d.data for d in qt.accepted] == [{"mission_ended": True}]


def test_routes_are_serialized_except_the_file_dialog() -> None:
    from game.server.missionresult import routes

    assert getattr(routes.mission_result, "takes_game_lock", False)
    assert getattr(routes.cancel, "takes_game_lock", False)
    assert getattr(routes.accept, "takes_game_lock", False)
    assert getattr(routes.load_file, "locks_game_itself", False)

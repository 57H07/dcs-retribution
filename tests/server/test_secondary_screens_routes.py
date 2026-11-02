"""WEB-08.2: transfers, notes, info panel, careers, logs, about and tools routes."""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator
from uuid import UUID, uuid4

import pytest

from game import VERSION, persistency
from game.applog import HookableInMemoryHandler, log_tail
from game.ato.flighttype import FlightType
from game.commands import CommandError
from game.commands import tools as tools_commands
from game.commands.notes import MAX_NOTES_LENGTH
from game.infos.information import Information
from game.server import GameContext
from game.squadrons.pilot import Award, AwardKind, LogbookEntry, Pilot
from game.theater.player import Player
from game.transfers import TransferOrder
from tests.server.test_command_view_commands import _request


@dataclass(frozen=True)
class _UnitType:
    display_name: str


class _Cp:
    def __init__(self, name: str, captured: Player = Player.BLUE) -> None:
        self.name = name
        self.captured = captured
        self.commissioned: list[dict[Any, int]] = []
        self.base = SimpleNamespace(commission_units=self.commissioned.append)


class _Transfers:
    """`PendingTransfers` as the commands use it."""

    def __init__(self, *transfers: Any) -> None:
        self.pending = list(transfers)
        self.cancelled: list[Any] = []

    def __iter__(self) -> Iterator[Any]:
        return iter(self.pending)

    def cancel_transfer(self, transfer: Any) -> None:
        self.pending.remove(transfer)
        self.cancelled.append(transfer)


def _transfer(units: dict[str, int], player: Player = Player.BLUE) -> Any:
    origin = _Cp("Incirlik", player)
    return SimpleNamespace(
        id=uuid4(),
        player=player,
        origin=origin,
        destination=_Cp("Hatay", player),
        position=origin,
        units={_UnitType(name): count for name, count in units.items()},
        size=sum(units.values()),
        description="Convoy to Hatay",
    )


class _Squadron:
    def __init__(self, *pilots: Pilot) -> None:
        self.current_roster = list(pilots)

    def __str__(self) -> str:
        return "VF-1 Wolfpack"


def _game(
    blue: _Transfers | None = None, red: _Transfers | None = None, **extra: Any
) -> Any:
    blue_coalition = SimpleNamespace(
        transfers=blue or _Transfers(),
        air_wing=extra.pop("air_wing", None),
    )
    red_coalition = SimpleNamespace(transfers=red or _Transfers())
    return SimpleNamespace(
        coalitions=[blue_coalition, red_coalition],
        coalition_for=lambda p: blue_coalition if p is Player.BLUE else red_coalition,
        **extra,
    )


def _load(monkeypatch: pytest.MonkeyPatch, game: Any) -> None:
    monkeypatch.setattr(
        GameContext, "_game_model", SimpleNamespace(game=game), raising=False
    )


# --- Transfers ------------------------------------------------------------------


def test_transfer_orders_have_a_stable_id_that_old_saves_get_on_load() -> None:
    origin, destination = _Cp("A"), _Cp("B")
    order = TransferOrder(origin, destination, {})  # type: ignore[arg-type]
    other = TransferOrder(origin, destination, {})  # type: ignore[arg-type]
    assert isinstance(order.id, UUID)
    assert order.id != other.id
    # Equality still means "same order", whatever the id.
    assert order == other

    state = dict(order.__dict__)
    del state["id"]
    old = TransferOrder.__new__(TransferOrder)
    old.__setstate__(state)
    assert isinstance(old.id, UUID)
    assert pickle.loads(pickle.dumps(order)).id == order.id


def test_list_transfers(
    monkeypatch: pytest.MonkeyPatch, sim_reloads: list[bool]
) -> None:
    _load(monkeypatch, None)
    assert _request("GET", "/transfers/") == (200, None)

    transfer = _transfer({"T-72B": 0, "M1A2 Abrams": 4, "M2A2 Bradley": 2})
    _load(
        monkeypatch, _game(_Transfers(transfer), _Transfers(_transfer({}, Player.RED)))
    )
    status, body = _request("GET", "/transfers/")
    assert status == 200
    assert body == [
        {
            "id": str(transfer.id),
            "origin": "Incirlik",
            "destination": "Hatay",
            "position": "Incirlik",
            "size": 6,
            "units": [
                {"name": "M1A2 Abrams", "count": 4},
                {"name": "M2A2 Bradley", "count": 2},
            ],
            "transport": "Convoy to Hatay",
        }
    ]


def test_cancel_transfer(
    monkeypatch: pytest.MonkeyPatch, sim_reloads: list[bool]
) -> None:
    transfer = _transfer({"M1A2 Abrams": 4})
    blue = _Transfers(transfer)
    _load(monkeypatch, _game(blue))

    assert _request("DELETE", f"/transfers/{transfer.id}") == (204, None)
    assert blue.cancelled == [transfer]
    assert len(sim_reloads) == 1

    status, body = _request("DELETE", f"/transfers/{transfer.id}")
    assert (status, body) == (404, {"detail": "This transfer is no longer pending."})


def test_enemy_transfers_cannot_be_cancelled(
    monkeypatch: pytest.MonkeyPatch, sim_reloads: list[bool]
) -> None:
    enemy = _transfer({"T-72B": 3}, Player.RED)
    red = _Transfers(enemy)
    _load(monkeypatch, _game(red=red))
    status, body = _request("DELETE", f"/transfers/{enemy.id}")
    assert (status, body) == (
        409,
        {"detail": "Only your own transfers can be cancelled."},
    )
    assert red.cancelled == []
    assert len(sim_reloads) == 0


def test_cancel_transfer_without_a_campaign(
    monkeypatch: pytest.MonkeyPatch, sim_reloads: list[bool]
) -> None:
    _load(monkeypatch, None)
    assert _request("DELETE", f"/transfers/{uuid4()}") == (
        409,
        {"detail": "No campaign is loaded."},
    )


# --- Notes and info panel ------------------------------------------------------


def test_notes_read_and_write(monkeypatch: pytest.MonkeyPatch) -> None:
    game = _game(notes="Bring tankers.")
    _load(monkeypatch, game)
    assert _request("GET", "/notes") == (200, {"text": "Bring tankers."})

    assert _request("PUT", "/notes", {"text": "SEAD first.\nThen strike."}) == (
        200,
        {"text": "SEAD first.\nThen strike."},
    )
    assert game.notes == "SEAD first.\nThen strike."

    status, body = _request("PUT", "/notes", {"text": "x" * (MAX_NOTES_LENGTH + 1)})
    assert status == 422
    assert "limited" in body["detail"]
    assert game.notes == "SEAD first.\nThen strike."


def test_notes_of_old_saves_and_without_a_campaign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load(monkeypatch, _game())  # no notes attribute: a save made before notes
    assert _request("GET", "/notes") == (200, {"text": ""})
    _load(monkeypatch, None)
    assert _request("GET", "/notes") == (200, None)
    assert _request("PUT", "/notes", {"text": "x"}) == (
        409,
        {"detail": "No campaign is loaded."},
    )


def test_informations_newest_first(monkeypatch: pytest.MonkeyPatch) -> None:
    first = Information("Base captured", "Hatay is ours", turn=1)
    second = Information("Budget", "Income 20M", turn=2)
    first.timestamp = datetime(2026, 10, 1, 12, 0)
    second.timestamp = datetime(2026, 10, 1, 12, 5)
    _load(monkeypatch, _game(informations=[first, second]))
    status, body = _request("GET", "/informations")
    assert status == 200
    assert [(i["turn"], i["title"], i["text"]) for i in body] == [
        (2, "Budget", "Income 20M"),
        (1, "Base captured", "Hatay is ours"),
    ]
    assert body[0]["timestamp"].startswith("2026-10-01T12:05")


# --- Careers -------------------------------------------------------------------


def test_careers(monkeypatch: pytest.MonkeyPatch) -> None:
    pilot = Pilot("Maverick", player=True)
    pilot.record.log_sortie(
        LogbookEntry(
            turn=1,
            date=datetime(2026, 6, 1, 8, 30),
            squadron="VF-1",
            aircraft="F-14B",
            task=FlightType.BARCAP,
            combat=True,
            flight_time=timedelta(hours=1, minutes=5),
            ejected=True,
        ),
        keep_history=True,
    )
    pilot.record.awards.append(
        Award(AwardKind.Rank, "Lieutenant", 1, datetime(2026, 6, 1, 8, 30))
    )
    ai_pilot = Pilot("Goose")
    air_wing = SimpleNamespace(iter_squadrons=lambda: [_Squadron(pilot, ai_pilot)])
    _load(monkeypatch, _game(air_wing=air_wing))

    status, body = _request("GET", "/careers/")
    assert status == 200
    assert len(body) == 1
    career = body[0]
    assert career["pilot"] == "Maverick"
    assert career["squadron"] == "VF-1 Wolfpack"
    assert career["rank"] == "Lieutenant"
    assert career["alive"] is True
    assert {"label": "Sorties", "value": "1"} in career["totals"]
    assert career["awards"][0]["date"] == "2026-06-01 08:30"
    assert career["history"][0]["loss"] == "Ejected"
    assert career["history"][0]["flight_time"] == "1:05"
    assert career["history"][0]["task"] == "BARCAP"

    _load(monkeypatch, None)
    assert _request("GET", "/careers/") == (200, None)


# --- Logs and about ------------------------------------------------------------


@pytest.fixture
def memory_log(monkeypatch: pytest.MonkeyPatch) -> HookableInMemoryHandler:
    handler = HookableInMemoryHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    monkeypatch.setattr(logging.getLogger(), "handlers", [handler])
    return handler


def test_logs_read_the_tail_without_a_campaign(
    monkeypatch: pytest.MonkeyPatch, memory_log: HookableInMemoryHandler
) -> None:
    _load(monkeypatch, None)
    for n in range(3):
        memory_log.handle(logging.makeLogRecord({"msg": f"line {n}"}))
    assert _request("GET", "/logs") == (
        200,
        {"lines": ["line 0", "line 1", "line 2"], "total": 3, "available": True},
    )
    assert log_tail(2) == (["line 1", "line 2"], 3)


def test_logs_without_an_in_memory_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging.getLogger(), "handlers", [])
    assert _request("GET", "/logs") == (
        200,
        {"lines": [], "total": 0, "available": False},
    )


def test_logs_are_read_only() -> None:
    assert _request("DELETE", "/logs")[0] == 405


def test_qt_keeps_the_handler_name_of_custom_logging_files() -> None:
    from qt_ui.logging_handler import HookableInMemoryHandler as QtHandler

    assert QtHandler is HookableInMemoryHandler


def test_about() -> None:
    status, body = _request("GET", "/about")
    assert status == 200
    assert body["version"] == VERSION
    assert "Khopa" in body["contributors"]
    assert body["special_thanks"][0] == {
        "name": "rp-",
        "reason": "for the pydcs framework",
    }
    assert all(a["url"].startswith("https://") for a in body["attributions"])


# --- Tools ---------------------------------------------------------------------


def test_import_layouts(monkeypatch: pytest.MonkeyPatch) -> None:
    _load(monkeypatch, None)
    monkeypatch.setattr("game.server.tools.routes.import_layouts", lambda: 42)
    assert _request("POST", "/tools/import-layouts") == (200, {"count": 42})


def test_pretense_campaign_route(monkeypatch: pytest.MonkeyPatch) -> None:
    game = _game()
    _load(monkeypatch, game)
    generated: list[Any] = []

    def generate(g: Any, on_restored: Any) -> Path:
        generated.append(g)
        return Path("missions/pretense_campaign.miz")

    monkeypatch.setattr("game.server.tools.routes.generate_pretense_campaign", generate)
    status, body = _request("POST", "/tools/pretense-campaign")
    assert status == 200
    assert Path(body["path"]) == Path("missions/pretense_campaign.miz")
    assert generated == [game]

    _load(monkeypatch, None)
    assert _request("POST", "/tools/pretense-campaign") == (
        409,
        {"detail": "No campaign is loaded."},
    )


def test_failed_pretense_generation_keeps_the_backup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import game.pretense.pretensemissiongenerator as generator

    (tmp_path / ".pre-pretense-backup.retribution").write_bytes(b"campaign")
    monkeypatch.setattr(persistency, "pre_pretense_backups_dir", lambda: tmp_path)
    monkeypatch.setattr(persistency, "mission_path_for", lambda name: tmp_path / name)

    class _Failing:
        def __init__(self, game: Any, time: Any) -> None:
            pass

        def generate_miz(self, output: Path) -> None:
            raise RuntimeError("no airfields")

    monkeypatch.setattr(generator, "PretenseMissionGenerator", _Failing)
    game = SimpleNamespace(conditions=SimpleNamespace(start_time=datetime.now()))
    with pytest.raises(CommandError, match="no airfields"):
        tools_commands.generate_pretense_campaign(
            game, lambda _: None  # type: ignore[arg-type]
        )
    backups = list(tmp_path.glob("pre-pretense-backup_*.retribution"))
    assert [b.read_bytes() for b in backups] == [b"campaign"]

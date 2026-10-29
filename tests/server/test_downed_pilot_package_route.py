from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException

from game.server.qt.routes import new_downed_pilot_package
from game.theater.player import Player


def _downed(player: Player) -> Any:
    return SimpleNamespace(is_friendly=lambda to_player: to_player == player)


def _game(downed: Any) -> Any:
    return SimpleNamespace(
        db=SimpleNamespace(downed_pilots=SimpleNamespace(get=lambda _id: downed))
    )


def test_friendly_downed_pilot_opens_package_dialog() -> None:
    opened: list[Any] = []
    downed = _downed(Player.BLUE)
    qt = SimpleNamespace(create_new_package=opened.append)
    new_downed_pilot_package(uuid4(), _game(downed), qt)  # type: ignore[arg-type]
    assert opened == [downed]


def test_enemy_downed_pilot_is_refused() -> None:
    opened: list[Any] = []
    qt = SimpleNamespace(create_new_package=opened.append)
    with pytest.raises(HTTPException) as error:
        new_downed_pilot_package(
            uuid4(), _game(_downed(Player.RED)), qt  # type: ignore[arg-type]
        )
    assert error.value.status_code == 400
    assert opened == []

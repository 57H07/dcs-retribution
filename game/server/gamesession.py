"""Which campaign the application runs (WEB-09.1).

The shell calls these at startup and when a campaign is opened or created; the
Pretense route when it swaps the campaign for its restored copy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.gamelock import game_lock
from game.sim import GameUpdateEvents
from game.sim.simcontroller import SimController
from .dependencies import GameContext, GameModel
from .eventstream import EventStream
from .missionresult.waiter import MissionResultContext

if TYPE_CHECKING:
    from game import Game


def start_session() -> None:
    """Sets up the empty model: to do before any request reaches the server."""
    GameContext.set_model(GameModel(None, SimController(None, EventStream.put_nowait)))


def activate_game(game: Game) -> None:
    """Makes `game` the running campaign and tells the web UI."""
    with game_lock():
        GameContext.set_game(game)
        GameContext.reload_sim()
        # A mission result belongs to the campaign that generated it.
        MissionResultContext.get().reset()
        EventStream.drain()
        EventStream.put_nowait(GameUpdateEvents().game_loaded(game))

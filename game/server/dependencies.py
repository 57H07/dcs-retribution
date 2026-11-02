from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game
    from game.sim.simcontroller import SimController


@dataclass
class GameModel:
    """The running campaign, or None, and its turn simulation."""

    game: Game | None
    sim_controller: SimController


class GameContext:
    _game_model: GameModel

    @classmethod
    def set_model(cls, game_model: GameModel) -> None:
        cls._game_model = game_model

    @classmethod
    def set_game(cls, game: Game | None) -> None:
        cls._game_model.game = game

    @classmethod
    def get(cls) -> Game | None:
        return cls._game_model.game

    @classmethod
    def require(cls) -> Game:
        if cls._game_model.game is None:
            raise RuntimeError("GameContext has no Game set")
        return cls._game_model.game

    @classmethod
    def get_sim(cls) -> SimController:
        """The turn simulation (sim speed, fast forward, mission generation)."""
        return cls._game_model.sim_controller

    @classmethod
    def reload_sim(cls) -> None:
        """Starts a new simulation of the campaign, paused.

        A simulation belongs to one turn and to the flights planned when it was
        created: call this after a command passed the turn or changed the game in
        depth (a cheat, an expensive setting). Safe with the game lock held.
        """
        cls.get_sim().set_game(cls._game_model.game)


class UiOptions:
    """Command-line options of the shell the web client needs (`qt_ui.main`)."""

    show_sim_speed_controls: bool = False

    @classmethod
    def set(cls, show_sim_speed_controls: bool) -> None:
        cls.show_sim_speed_controls = show_sim_speed_controls

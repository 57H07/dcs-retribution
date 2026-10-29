from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from game.theater import ControlPoint, MissionTarget, TheaterGroundObject

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight, Package
    from game.game import TurnState
    from game.server.qt.models import QtDialog, QtLink
    from qt_ui.models import GameModel
    from qt_ui.simcontroller import SimController


class GameContext:
    _game_model: GameModel

    @classmethod
    def set_model(cls, game_model: GameModel) -> None:
        cls._game_model = game_model

    @classmethod
    def get(cls) -> Game | None:
        return cls._game_model.game

    @classmethod
    def require(cls) -> Game:
        if cls._game_model.game is None:
            raise RuntimeError("GameContext has no Game set")
        return cls._game_model.game

    @classmethod
    def get_model(cls) -> GameModel:
        return cls._game_model

    @classmethod
    def get_sim(cls) -> SimController:
        """The turn simulation (sim speed, fast forward, mission generation)."""
        return cls._game_model.sim_controller


class UiOptions:
    """Command-line options of the UI the web client needs (`qt_ui.uiflags`)."""

    show_sim_speed_controls: bool = False

    @classmethod
    def set(cls, show_sim_speed_controls: bool) -> None:
        cls.show_sim_speed_controls = show_sim_speed_controls


class QtCallbacks:
    def __init__(
        self,
        create_new_package: Callable[[MissionTarget], None],
        show_tgo_info: Callable[[TheaterGroundObject], None],
        show_control_point_info: Callable[[ControlPoint], None],
        select_flight: Callable[[Flight], None],
        turn_passed: Callable[[TurnState], None] | None = None,
        open_dialog: Callable[[QtDialog], None] | None = None,
        open_link: Callable[[QtLink], None] | None = None,
        edit_package: Callable[[Package], None] | None = None,
        mission_generated: Callable[[], None] | None = None,
    ) -> None:
        self.create_new_package = create_new_package
        self.show_tgo_info = show_tgo_info
        self.show_control_point_info = show_control_point_info
        self.select_flight = select_flight
        # Refreshes the Qt widgets after an API command passed the turn. Called from
        # an API worker thread with the game lock held: it must only queue work onto
        # the Qt main thread (emit a signal), never block on it.
        self.turn_passed = turn_passed
        # Open a not-yet-migrated Qt screen, an external link or the package editor
        # for the web UI (WEB-00.3). Same contract as turn_passed: emit a signal.
        self.open_dialog = open_dialog
        self.open_link = open_link
        self.edit_package = edit_package
        # Opens the Qt window waiting for the mission result once the web UI took
        # off (WEB-01.1), until WEB-05.1 migrates it. Same contract: emit a signal.
        self.mission_generated = mission_generated


class QtContext:
    _callbacks: QtCallbacks | None = None

    @classmethod
    def set_callbacks(cls, callbacks: QtCallbacks) -> None:
        cls._callbacks = callbacks

    @classmethod
    def get(cls) -> QtCallbacks:
        if cls._callbacks is None:
            raise RuntimeError("QtContext has no callbacks set")
        return cls._callbacks

    @classmethod
    def get_optional(cls) -> QtCallbacks | None:
        """The Qt callbacks, or None when no Qt window is running (tests)."""
        return cls._callbacks

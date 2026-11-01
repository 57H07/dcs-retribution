from collections.abc import Callable

from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout

from game import Game
from game.commands.cheats import cheat_move_front_line
from game.commands.frontline import enemies_at_front
from game.gamelock import game_lock
from game.server import EventStream
from game.theater import ControlPoint
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.basemenu.ground_forces.QGroundForcesStrategySelector import (
    QGroundForcesStrategySelector,
)


class QGroundForcesStrategy(QGroupBox):
    def __init__(self, cp: ControlPoint, game: Game):
        super(QGroundForcesStrategy, self).__init__("Frontline operations :")
        self.cp = cp
        self.game = game
        self.init_ui()

    def init_ui(self):
        def make_cheat_callback(
            enemy_point: ControlPoint, advance: bool
        ) -> Callable[[], None]:
            def cheat() -> None:
                self.cheat_alter_front_line(enemy_point, advance)

            return cheat

        layout = QVBoxLayout()
        for enemy_cp in enemies_at_front(self.cp):
            layout.addWidget(QLabel(enemy_cp.name))
            layout.addWidget(QGroundForcesStrategySelector(self.cp, enemy_cp))
            if self.game.settings.enable_frontline_cheats:
                advance_button = QPushButton("CHEAT: Advance")
                advance_button.setProperty("style", "btn-danger")
                layout.addWidget(advance_button)
                advance_button.clicked.connect(
                    make_cheat_callback(enemy_cp, advance=True)
                )

                retreat_button = QPushButton("CHEAT: Retreat")
                retreat_button.setProperty("style", "btn-danger")
                layout.addWidget(retreat_button)
                retreat_button.clicked.connect(
                    make_cheat_callback(enemy_cp, advance=False)
                )

        layout.addStretch()
        self.setLayout(layout)

    def cheat_alter_front_line(self, enemy_point: ControlPoint, advance: bool) -> None:
        # Same rules as the web base screen (WEB-02.3).
        with game_lock(), EventStream.event_context() as events:
            cheat_move_front_line(self.game, self.cp, enemy_point, advance, events)
        GameUpdateSignal.get_instance().updateGame(self.game)

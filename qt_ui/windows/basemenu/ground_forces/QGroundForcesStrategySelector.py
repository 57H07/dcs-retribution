from PySide6.QtWidgets import QComboBox

from game.commands.frontline import front_line_stance, set_front_line_stance
from game.gamelock import game_lock
from game.server import EventStream
from game.theater import CombatStance, ControlPoint


class QGroundForcesStrategySelector(QComboBox):
    def __init__(self, cp: ControlPoint, enemy_cp: ControlPoint):
        super(QGroundForcesStrategySelector, self).__init__()
        self.cp = cp
        self.enemy_cp = enemy_cp

        current = front_line_stance(self.cp, enemy_cp)
        self.cp.stances[enemy_cp.id] = current

        for i, stance in enumerate(CombatStance):
            self.addItem(stance.name, userData=stance)
            if current == stance:
                self.setCurrentIndex(i)

        self.currentTextChanged.connect(self.on_change)

    def on_change(self):
        # Same rules as the web base screen (WEB-02.3).
        with game_lock(), EventStream.event_context() as events:
            set_front_line_stance(
                self.cp, self.enemy_cp, self.currentData().name, events
            )

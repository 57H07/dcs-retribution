from PySide6.QtGui import QStandardItem, QStandardItemModel

from game import Game
from game.commands.flightroute import (
    predefined_waypoints,
    select_predefined_waypoints,
)
from game.theater.player import Player
from qt_ui.widgets.combos.QFilteredComboBox import QFilteredComboBox


class QPredefinedWaypointSelectionComboBox(QFilteredComboBox):
    def __init__(
        self,
        game: Game,
        parent=None,
        include_targets=True,
        include_airbases=True,
        include_frontlines=True,
        include_units=True,
        include_enemy=True,
        include_friendly=True,
    ):
        super(QPredefinedWaypointSelectionComboBox, self).__init__(parent)
        self.game = game
        self.include_targets = include_targets
        self.include_airbases = include_airbases
        self.include_frontlines = include_frontlines
        self.include_units = include_units
        self.include_enemy = include_enemy
        self.include_friendly = include_friendly
        self.find_possible_waypoints()

    def get_selected_waypoints(self, include_all_from_same_location=False):
        return select_predefined_waypoints(
            self.wpts, self.currentText(), include_all_from_same_location
        )

    def find_possible_waypoints(self):
        self.wpts = predefined_waypoints(
            self.game,
            Player.BLUE,
            include_frontlines=self.include_frontlines,
            include_airbases=self.include_airbases,
            include_enemy=self.include_enemy,
            include_friendly=self.include_friendly,
        )
        model = QStandardItemModel()
        for i, wpt in enumerate(self.wpts):
            model.setItem(i, 0, QStandardItem(wpt.pretty_name))
        self.setModel(model)

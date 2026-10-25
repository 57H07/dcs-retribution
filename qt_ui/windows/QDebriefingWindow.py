import logging
from typing import Callable, Dict, TypeVar

from PySide6.QtGui import QIcon, QPixmap, QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from game.debriefing import DamagedUnitReport, Debriefing
from game.theater import Player
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal

T = TypeVar("T")


class LossGrid(QGridLayout):
    def __init__(self, debriefing: Debriefing, player: Player) -> None:
        super().__init__()

        self.add_loss_rows(
            debriefing.air_losses.by_type(player), lambda u: u.display_name
        )
        self.add_loss_rows(
            debriefing.front_line_losses_by_type(player), lambda u: str(u)
        )
        self.add_loss_rows(
            debriefing.motorpool_losses_by_type(player),
            lambda u: f"{u} from motorpool",
        )
        self.add_loss_rows(
            debriefing.convoy_losses_by_type(player), lambda u: f"{u} from convoy"
        )
        self.add_loss_rows(
            debriefing.cargo_ship_losses_by_type(player),
            lambda u: f"{u} from cargo ship",
        )
        self.add_loss_rows(
            debriefing.airlift_losses_by_type(player), lambda u: f"{u} from airlift"
        )
        self.add_loss_rows(debriefing.ground_object_losses_by_type(player), lambda u: u)
        self.add_loss_rows(debriefing.scenery_losses_by_type(player), lambda u: u)

        # TODO: Display dead ground object units and runways.

    def add_loss_rows(self, losses: Dict[T, int], make_name: Callable[[T], str]):
        for unit_type, count in losses.items():
            row = self.rowCount()
            try:
                name = make_name(unit_type)
            except AttributeError:
                logging.exception(f"Could not make unit name for {unit_type}")
                name = unit_type.id
            self.addWidget(QLabel(name), row, 0)
            self.addWidget(QLabel(str(count)), row, 1)


class ScrollingCasualtyReportContainer(QGroupBox):
    def __init__(self, debriefing: Debriefing, player: Player) -> None:
        country = (
            debriefing.player_country if player.is_blue else debriefing.enemy_country
        )
        super().__init__(f"{country}'s lost units:")
        scroll_content = QWidget()
        scroll_content.setLayout(LossGrid(debriefing, player))
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_content)
        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        self.setLayout(layout)


class DamagedUnitsContainer(QGroupBox):
    """The "Damaged units" section (PER-01.4): units that survived the mission
    damaged, with what their damage costs."""

    HEADERS = ["Side", "Type", "Damage", "Unavailability"]

    def __init__(self, debriefing: Debriefing, reports: list[DamagedUnitReport]):
        super().__init__("Damaged units:")
        grid = QGridLayout()
        for column, header in enumerate(self.HEADERS):
            grid.addWidget(QLabel(f"<b>{header}</b>"), 0, column)
        for row, report in enumerate(reports, 1):
            side = (
                debriefing.player_country
                if report.player.is_blue
                else debriefing.enemy_country
            )
            grid.addWidget(QLabel(side), row, 0)
            grid.addWidget(QLabel(report.unit_type), row, 1)
            grid.addWidget(QLabel(f"{report.damage_percent} %"), row, 2)
            grid.addWidget(QLabel(report.unavailability), row, 3)
        scroll_content = QWidget()
        scroll_content.setLayout(grid)
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_content)
        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        self.setLayout(layout)


class QDebriefingWindow(QDialog):
    def __init__(self, debriefing: Debriefing):
        super(QDebriefingWindow, self).__init__()
        self.debriefing = debriefing

        self.setModal(True)
        self.setWindowTitle("Debriefing")
        self.setMinimumSize(300, 200)
        self.setWindowIcon(QIcon("./resources/icon.png"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel(self)
        header.setGeometry(0, 0, 655, 106)
        pixmap = QPixmap("./resources/ui/debriefing.png")
        header.setPixmap(pixmap)
        layout.addWidget(header)

        title = QLabel("<b>Casualty report</b>")
        layout.addWidget(title)

        player_lost_units = ScrollingCasualtyReportContainer(
            debriefing, player=Player.BLUE
        )
        layout.addWidget(player_lost_units)

        enemy_lost_units = ScrollingCasualtyReportContainer(
            debriefing, player=Player.RED
        )
        layout.addWidget(enemy_lost_units, 1)

        damaged_units = debriefing.damaged_unit_reports()
        if damaged_units:
            layout.addWidget(DamagedUnitsContainer(debriefing, damaged_units), 1)

        okay = QPushButton("Okay")
        okay.clicked.connect(self.close)
        layout.addWidget(okay)

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
        state = self.debriefing.game.check_win_loss()
        GameUpdateSignal.get_instance().gameStateChanged(state)

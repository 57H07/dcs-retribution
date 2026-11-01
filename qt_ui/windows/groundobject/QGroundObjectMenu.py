import logging

from PySide6.QtGui import QTransform
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QSpinBox,
    QWidget,
    QCheckBox,
)
from game.commands import (
    CommandError,
    disband_ground_object,
    repair_ground_unit,
    resale_value,
    rotate_ground_object,
    set_hidden_on_mfd,
)
from game.config import REWARDS
from game.data.building_data import FORTIFICATION_BUILDINGS
from game.gamelock import game_lock
from game.server import EventStream
from game.theater import ControlPoint, TheaterGroundObject, Player
from game.theater.grounddamage import accelerated_repair_cost
from game.theater.theatergroup import TheaterUnit
from game.theater.theatergroundobject import (
    BuildingGroundObject,
)
from game.utils import Heading
from qt_ui.models import GameModel
from qt_ui.uiconstants import EVENT_ICONS, ICONS
from qt_ui.widgets.QBudgetBox import QBudgetBox
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.groundobject.QBuildingInfo import QBuildingInfo
from qt_ui.windows.groundobject.QGroundObjectBuyMenu import QGroundObjectBuyMenu


class HeadingIndicator(QLabel):
    def __init__(self, initial_heading: Heading, parent: QWidget) -> None:
        super().__init__(parent)
        self.set_heading(initial_heading)
        self.setFixedSize(32, 32)

    def set_heading(self, heading: Heading) -> None:
        self.setPixmap(
            ICONS["heading"].transformed(QTransform().rotate(heading.degrees))
        )


class SamIndicator(QLabel):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setPixmap(ICONS["blue-sam"])


class QGroundObjectMenu(QDialog):
    def __init__(
        self,
        parent,
        ground_object: TheaterGroundObject,
        cp: ControlPoint,
        gm: GameModel,
    ):
        super().__init__(parent)
        self.setMinimumWidth(350)
        self.ground_object = ground_object
        self.cp = cp
        self.game_model = gm
        self.game = gm.game
        self.setWindowTitle(
            f"Location - {self.ground_object.obj_name} ({self.cp.name})"
        )
        self.setWindowIcon(EVENT_ICONS["capture"])
        self.intelBox = QGroupBox("Units :")
        self.buildingBox = QGroupBox("Buildings :")
        self.orientationBox = QGroupBox("Orientation :")
        self.intelLayout = QGridLayout()
        self.buildingsLayout = QGridLayout()
        self.sell_all_button = None
        self.total_value = 0
        self.init_ui()

    def init_ui(self):
        self.mainLayout = QVBoxLayout()
        self.budget = QBudgetBox(self.game)
        self.budget.setGame(self.game)

        self.doLayout()

        if isinstance(self.ground_object, BuildingGroundObject):
            self.mainLayout.addWidget(self.buildingBox)
            if self.cp.captured.is_blue:
                self.mainLayout.addWidget(self.financesBox)
        else:
            self.mainLayout.addWidget(self.intelBox)
            self.mainLayout.addWidget(self.orientationBox)
            if self.ground_object.is_iads and self.cp.is_friendly(to_player=Player.RED):
                self.mainLayout.addWidget(self.hiddenBox)

        self.actionLayout = QHBoxLayout()

        self.sell_all_button = QPushButton("Disband (+" + str(self.total_value) + "M)")
        self.sell_all_button.clicked.connect(self.sell_all)
        self.sell_all_button.setProperty("style", "btn-danger")

        self.buy_replace = QPushButton("Buy/Replace")
        self.buy_replace.clicked.connect(self.buy_group)
        self.buy_replace.setProperty("style", "btn-success")

        if self.ground_object.purchasable:
            # if not purchasable but is_iads => naval unit
            if self.total_value > 0:
                self.actionLayout.addWidget(self.sell_all_button)
            self.actionLayout.addWidget(self.buy_replace)

        if self.show_buy_sell_actions and self.ground_object.purchasable:
            # if not purchasable but is_iads => naval unit
            self.mainLayout.addLayout(self.actionLayout)
        self.setLayout(self.mainLayout)

    @property
    def show_buy_sell_actions(self) -> bool:
        if self.cp.captured.is_neutral:
            return False
        buysell_allowed = self.game.settings.enable_enemy_buy_sell
        buysell_allowed |= self.cp.captured.is_blue
        return buysell_allowed

    def doLayout(self):
        self.update_total_value()
        self.intelBox = QGroupBox("Units :")
        self.intelLayout = QGridLayout()
        i = 0
        for g in self.ground_object.groups:
            for unit in g.units:
                self.intelLayout.addWidget(
                    QLabel(f"<b>Unit {str(unit.display_name)}</b>"), i, 0
                )

                if not unit.alive and unit.repairable:
                    if unit.repair_turns_remaining is not None:
                        repair_label = QLabel(
                            "Repairing (" f"{unit.repair_turns_remaining} turns)"
                        )
                        self.intelLayout.addWidget(repair_label, i, 1)
                    elif self.cp.captured.is_blue:
                        price = unit.unit_type.price if unit.unit_type else 0
                        repair = QPushButton(f"Repair [{price}M]")
                        repair.setProperty("style", "btn-success")
                        repair.clicked.connect(
                            lambda checked=False, u=unit, p=price: self.repair_unit(
                                u, p
                            )
                        )
                        self.intelLayout.addWidget(repair, i, 1)
                    else:
                        self.intelLayout.addWidget(QLabel("Destroyed"), i, 1)
                elif unit.inoperative:
                    turns = unit.inoperative_turns_remaining(self.game.turn)
                    if (
                        self.cp.captured.is_blue
                        and self.game.settings.persistent_damage_paid_ground_repair
                    ):
                        price = accelerated_repair_cost(unit)
                        repair = QPushButton(
                            f"Repair now ({turns} turns left) [{price}M]"
                        )
                        repair.setProperty("style", "btn-success")
                        repair.clicked.connect(
                            lambda checked=False, u=unit, p=price: (
                                self.repair_inoperative_unit(u, p)
                            )
                        )
                        self.intelLayout.addWidget(repair, i, 1)
                    else:
                        self.intelLayout.addWidget(
                            QLabel(f"Inoperative ({turns} turns)"), i, 1
                        )
                i += 1

        stretch = QVBoxLayout()
        stretch.addStretch()
        self.intelLayout.addLayout(stretch, i, 0)

        self.buildingBox = QGroupBox("Buildings :")
        self.buildingsLayout = QGridLayout()

        j = 0
        total_income = 0
        received_income = 0
        for static in self.ground_object.statics:
            if static not in FORTIFICATION_BUILDINGS:
                self.buildingsLayout.addWidget(
                    QBuildingInfo(static, self.ground_object, self.repair_building),
                    j / 3,
                    j % 3,
                )
                j = j + 1

            if self.ground_object.category in REWARDS.keys():
                total_income += REWARDS[self.ground_object.category]
                if static.alive:
                    received_income += REWARDS[self.ground_object.category]
            else:
                logging.warning(self.ground_object.category + " not in REWARDS")

        self.financesBox = QGroupBox("Finances: ")
        self.financesBoxLayout = QGridLayout()
        self.financesBoxLayout.addWidget(
            QLabel("Available: " + str(total_income) + "M"), 2, 1
        )
        self.financesBoxLayout.addWidget(
            QLabel("Receiving: " + str(received_income) + "M"), 2, 2
        )

        # Orientation Box
        self.orientationBox = QGroupBox("Orientation :")
        self.orientationBoxLayout = QHBoxLayout()

        self.heading_image = HeadingIndicator(self.ground_object.heading, self)
        self.orientationBoxLayout.addWidget(self.heading_image)
        self.headingLabel = QLabel("Heading:")
        self.orientationBoxLayout.addWidget(self.headingLabel)
        self.headingSelector = QSpinBox()
        self.headingSelector.setRange(0, 359)
        self.headingSelector.setWrapping(True)
        self.headingSelector.setSingleStep(5)
        self.headingSelector.setValue(self.ground_object.heading.degrees)
        self.headingSelector.valueChanged.connect(
            lambda degrees: self.rotate_tgo(Heading(degrees))
        )
        self.orientationBoxLayout.addWidget(self.headingSelector)
        can_adjust_heading = self.cp.is_friendly(
            to_player=Player.BLUE if self.game_model.is_ownfor else Player.RED
        )
        if can_adjust_heading:
            self.head_to_conflict_button = QPushButton("Head to conflict")
            heading = (
                self.game.theater.heading_to_conflict_from(self.ground_object.position)
                or self.ground_object.heading
            )
            self.head_to_conflict_button.clicked.connect(
                lambda: self.headingSelector.setValue(heading.degrees)
            )
            self.orientationBoxLayout.addWidget(self.head_to_conflict_button)
        else:
            self.headingSelector.setEnabled(False)

        # Hidden Box
        self.hiddenBox = QGroupBox()
        self.hiddenBoxLayout = QHBoxLayout()
        self.hiddenBoxLayout.addWidget(SamIndicator(self))
        self.hiddenBoxLayout.addWidget(QLabel("Hidden on MFD:"))
        self.hiddenCheckBox = QCheckBox()
        self.hiddenCheckBox.setChecked(self.ground_object.hide_on_mfd)
        self.hiddenCheckBox.stateChanged.connect(self.update_hidden_on_mfd)
        self.hiddenBoxLayout.addWidget(self.hiddenCheckBox)

        # Set the layouts
        self.financesBox.setLayout(self.financesBoxLayout)
        self.buildingBox.setLayout(self.buildingsLayout)
        self.intelBox.setLayout(self.intelLayout)
        self.orientationBox.setLayout(self.orientationBoxLayout)
        self.hiddenBox.setLayout(self.hiddenBoxLayout)

    def update_hidden_on_mfd(self, state: bool) -> None:
        with game_lock(), EventStream.event_context() as events:
            set_hidden_on_mfd(self.ground_object, bool(state), events)

    def do_refresh_layout(self):
        try:
            for i in reversed(range(self.mainLayout.count())):
                item = self.mainLayout.itemAt(i)
                if item is not None and item.widget() is not None:
                    item.widget().setParent(None)
            self.sell_all_button.setParent(None)
            self.buy_replace.setParent(None)
            self.actionLayout.setParent(None)

            self.doLayout()
            if isinstance(self.ground_object, BuildingGroundObject):
                self.mainLayout.addWidget(self.buildingBox)
            else:
                self.mainLayout.addWidget(self.intelBox)
                self.mainLayout.addWidget(self.orientationBox)

            self.actionLayout = QHBoxLayout()
            if self.total_value > 0:
                self.actionLayout.addWidget(self.sell_all_button)
            self.actionLayout.addWidget(self.buy_replace)

            if self.show_buy_sell_actions and self.ground_object.purchasable:
                self.mainLayout.addLayout(self.actionLayout)
        except Exception as e:
            logging.exception(e)
        self.update_total_value()

    def update_total_value(self):
        if not self.ground_object.purchasable:
            return
        self.total_value = resale_value(self.ground_object)
        if self.sell_all_button is not None:
            self.sell_all_button.setText("Disband (+$" + str(self.total_value) + "M)")

    def repair_unit(self, unit, price):
        self._repair(unit)

    def repair_building(self, unit, price):
        self._repair(unit)

    def repair_inoperative_unit(self, unit: TheaterUnit, price: int) -> None:
        self._repair(unit)

    def _repair(self, unit: TheaterUnit) -> None:
        try:
            with game_lock(), EventStream.event_context() as events:
                repair_ground_unit(self.game, self.ground_object, unit.id, events)
        except CommandError as refusal:
            logging.info(refusal.message)
        self.update_game()

    def rotate_tgo(self, heading: Heading) -> None:
        player = Player.BLUE if self.game_model.is_ownfor else Player.RED
        with game_lock(), EventStream.event_context() as events:
            rotate_ground_object(self.ground_object, heading, events, player)
        self.heading_image.set_heading(heading)

    def sell_all(self):
        with game_lock(), EventStream.event_context() as events:
            disband_ground_object(self.game, self.ground_object, events)
        self.update_game()

    def buy_group(self) -> None:
        self.subwindow = QGroundObjectBuyMenu(
            self, self.ground_object, self.game, self.total_value
        )
        if self.subwindow.exec():
            self.update_game()

    def update_game(self) -> None:
        """The commands published their changes: refreshes the Qt widgets."""
        GameUpdateSignal.get_instance().updateGame(self.game)
        # Refresh the dialog
        self.do_refresh_layout()

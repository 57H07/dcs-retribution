from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, Dict, Optional, Type

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    QApplication,
)
from dcs.unittype import UnitType

from game import Game
from game.dcs.groundunittype import GroundUnitType
from game.squadrons import Squadron
from game.theater import ControlPoint, Player
from game.theater.ctldzones import (
    ctld_zone_unavailable_reason,
    default_zones_enabled,
)
from game.transfers import (
    PlayerAirliftError,
    TransferOrder,
    airlift_squadrons,
    max_airlift_capacity,
    player_airlift_problem,
)
from qt_ui.models import GameModel
from qt_ui.widgets.QLabeledWidget import QLabeledWidget


class TransferDestinationComboBox(QComboBox):
    def __init__(self, game: Game, origin: ControlPoint) -> None:
        super().__init__()
        self.game = game
        self.origin = origin

        for cp in self.game.theater.controlpoints:
            if (
                cp != self.origin
                and cp.is_friendly(to_player=Player.BLUE)
                and cp.can_deploy_ground_units
            ):
                self.addItem(cp.name, cp)
        self.model().sort(0)
        self.setCurrentIndex(0)


class UnitTransferList(QFrame):
    def __init__(self, cp: ControlPoint, game_model: GameModel):
        super().__init__(self)
        self.cp = cp
        self.game_model = game_model

        self.bought_amount_labels = {}
        self.existing_units_labels = {}

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        scroll_content = QWidget()
        task_box_layout = QGridLayout()
        scroll_content.setLayout(task_box_layout)

        units_column = sorted(cp.base.armor, key=lambda u: u.display_name)

        count = 0
        for count, unit_type in enumerate(units_column):
            self.add_purchase_row(unit_type, task_box_layout, count)
        stretch = QVBoxLayout()
        stretch.addStretch()
        task_box_layout.addLayout(stretch, count, 0)

        scroll_content.setLayout(task_box_layout)
        scroll = QScrollArea()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)


class TransferOptionsPanel(QVBoxLayout):
    def __init__(self, game: Game, origin: ControlPoint) -> None:
        super().__init__()

        self.source_combo_box = TransferDestinationComboBox(game, origin)
        self.transport_type = QComboBox()
        self.transport_type.addItem("Auto", "auto")
        self.transport_type.addItem("Airlift", "airlift")
        self.squadron = QComboBox()
        self.squadron.setToolTip(
            "Pick a squadron to create a Transport mission you can fly. "
            "AI-assigned lets the AI plan the airlift with auto-assignable squadrons."
        )
        self.addLayout(QLabeledWidget("Destination:", self.source_combo_box))
        self.addLayout(QLabeledWidget("Requested transport type:", self.transport_type))
        self.addLayout(QLabeledWidget("Transport squadron:", self.squadron))
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setVisible(False)
        self.addWidget(self.warning)

    @property
    def selected_squadron(self) -> Optional[Squadron]:
        if not self.request_airlift:
            return None
        return self.squadron.currentData()

    def show_warning(self, text: Optional[str]) -> None:
        self.warning.setText(text or "")
        self.warning.setVisible(bool(text))

    @property
    def changed(self):
        return self.source_combo_box.currentIndexChanged

    @property
    def current(self) -> ControlPoint:
        return self.source_combo_box.currentData()

    @property
    def request_airlift(self) -> bool:
        return self.transport_type.currentData() == "airlift"


class TransferControls(QGroupBox):
    def __init__(
        self,
        increase_text: str,
        on_increase: Callable[[TransferControls], None],
        decrease_text: str,
        on_decrease: Callable[[TransferControls], None],
        initial_amount: int = 0,
        disabled: bool = False,
    ) -> None:
        super().__init__()

        self.quantity = initial_amount

        self.setProperty("style", "buy-box")
        self.setMaximumHeight(36)
        self.setMinimumHeight(36)
        layout = QHBoxLayout()
        self.setLayout(layout)

        decrease = QPushButton(decrease_text)
        decrease.setProperty("style", "btn-sell")
        decrease.setDisabled(disabled)
        decrease.setMinimumSize(16, 16)
        decrease.setMaximumSize(16, 16)
        decrease.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        )
        decrease.clicked.connect(lambda: on_decrease(self))
        layout.addWidget(decrease)

        self.count_label = QLabel()
        self.count_label.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        )
        self.set_quantity(initial_amount)
        layout.addWidget(self.count_label)

        increase = QPushButton(increase_text)
        increase.setProperty("style", "btn-buy")
        increase.setDisabled(disabled)
        increase.setMinimumSize(16, 16)
        increase.setMaximumSize(16, 16)
        increase.clicked.connect(lambda: on_increase(self))
        increase.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        )
        layout.addWidget(increase)

    def set_quantity(self, quantity: int) -> None:
        self.quantity = quantity
        self.count_label.setText(f"<b>{self.quantity}</b>")


class ScrollingUnitTransferGrid(QFrame):
    transfer_quantity_changed = Signal()

    def __init__(self, cp: ControlPoint, game_model: GameModel) -> None:
        super().__init__()
        self.cp = cp
        self.game_model = game_model
        self.transfers: Dict[Type[UnitType, int]] = defaultdict(int)

        main_layout = QVBoxLayout()

        scroll_content = QWidget()
        task_box_layout = QGridLayout()

        unit_types = set(
            self.game_model.game.faction_for(player=Player.BLUE).ground_units
        )
        sorted_units = sorted(
            {u for u in unit_types if self.cp.base.total_units_of_type(u)},
            key=lambda u: u.display_name,
        )
        for row, unit_type in enumerate(sorted_units):
            self.add_unit_row(unit_type, task_box_layout, row)
        stretch = QVBoxLayout()
        stretch.addStretch()
        task_box_layout.addLayout(stretch, task_box_layout.count(), 0)

        scroll_content.setLayout(task_box_layout)
        scroll = QScrollArea()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def add_unit_row(
        self,
        unit_type: GroundUnitType,
        layout: QGridLayout,
        row: int,
    ) -> None:
        exist = QGroupBox()
        exist.setProperty("style", "buy-box")
        exist.setMaximumHeight(36)
        exist.setMinimumHeight(36)
        origin_inventory_layout = QHBoxLayout()
        exist.setLayout(origin_inventory_layout)

        origin_inventory = self.cp.base.total_units_of_type(unit_type)

        unit_name = QLabel(f"<b>{unit_type.display_name}</b>")
        unit_name.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        )

        origin_inventory_label = QLabel(str(origin_inventory))
        origin_inventory_label.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        )

        def increase(controls: TransferControls):
            nonlocal origin_inventory
            nonlocal origin_inventory_label
            if not origin_inventory:
                return

            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                amount = 10
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                amount = 5
            else:
                amount = 1

            self.transfers[unit_type] += min(origin_inventory, amount)
            origin_inventory -= min(origin_inventory, amount)
            controls.set_quantity(self.transfers[unit_type])
            origin_inventory_label.setText(str(origin_inventory))
            self.transfer_quantity_changed.emit()

        def decrease(controls: TransferControls):
            nonlocal origin_inventory
            nonlocal origin_inventory_label
            if not controls.quantity:
                return

            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                amount = 10
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                amount = 5
            else:
                amount = 1

            origin_inventory += min(self.transfers[unit_type], amount)
            self.transfers[unit_type] -= min(self.transfers[unit_type], amount)
            controls.set_quantity(self.transfers[unit_type])
            origin_inventory_label.setText(str(origin_inventory))
            self.transfer_quantity_changed.emit()

        transfer_controls = TransferControls("->", increase, "<-", decrease)

        origin_inventory_layout.addWidget(unit_name)
        origin_inventory_layout.addItem(
            QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        )
        origin_inventory_layout.addWidget(origin_inventory_label)
        origin_inventory_layout.addItem(
            QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        )

        layout.addWidget(exist, row, 1)
        layout.addWidget(transfer_controls, row, 2)


class NewUnitTransferDialog(QDialog):
    """Unit transfer order, or a player Transport mission when a squadron is picked.

    A Transport mission (TRN-01.2) is an airlift transfer flown by one flight of a
    squadron chosen by the player: delivery at the end of the turn, cargo lost with
    the aircraft, like any airlift.
    """

    def __init__(
        self,
        game_model: GameModel,
        origin: ControlPoint,
        parent=None,
        transport_mission: bool = False,
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        if transport_mission:
            self.setWindowTitle(f"New Transport mission from {origin.name}")
        else:
            self.setWindowTitle(f"New unit transfer from {origin.name}")

        self.game_model = game_model

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.dest_panel = TransferOptionsPanel(game_model.game, origin)
        layout.addLayout(self.dest_panel)

        self.transfer_panel = ScrollingUnitTransferGrid(origin, game_model)
        self.transfer_panel.transfer_quantity_changed.connect(self.update_state)
        layout.addWidget(self.transfer_panel)

        self.submit_button = QPushButton("Create Transfer Order", parent=self)
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setProperty("style", "start-button")
        self.submit_button.setDisabled(True)
        layout.addWidget(self.submit_button)

        if transport_mission:
            self.dest_panel.transport_type.setCurrentIndex(
                self.dest_panel.transport_type.findData("airlift")
            )
        self.refresh_squadrons(prefer_player_squadron=transport_mission)
        self.dest_panel.changed.connect(lambda: self.refresh_squadrons())
        self.dest_panel.transport_type.currentIndexChanged.connect(
            lambda: self.refresh_squadrons()
        )
        self.dest_panel.squadron.currentIndexChanged.connect(self.update_state)

    @property
    def selected_units(self) -> dict[GroundUnitType, int]:
        return {
            unit_type: count
            for unit_type, count in self.transfer_panel.transfers.items()
            if count
        }

    def draft_transfer(self) -> Optional[TransferOrder]:
        destination = self.dest_panel.current
        if destination is None:
            return None
        return TransferOrder(self.origin, destination, self.selected_units)

    def refresh_squadrons(self, prefer_player_squadron: bool = False) -> None:
        combo = self.dest_panel.squadron
        previous = combo.currentData()
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItem("AI-assigned", None)
            draft = self.draft_transfer()
            if draft is not None:
                air_wing = self.game_model.game.blue.air_wing
                for squadron in airlift_squadrons(air_wing, draft, draft.destination):
                    combo.addItem(
                        f"{squadron.name} - {squadron.aircraft.display_name} at "
                        f"{squadron.location.name} (up to "
                        f"{max_airlift_capacity(squadron)} units)",
                        squadron,
                    )
            index = combo.findData(previous) if previous is not None else -1
            if index < 0 and prefer_player_squadron and combo.count() > 1:
                index = 1
            combo.setCurrentIndex(max(index, 0))
            combo.setEnabled(self.dest_panel.request_airlift)
        finally:
            combo.blockSignals(False)
        self.update_state()

    def _no_squadron_warning(self, draft: TransferOrder) -> str:
        lines = [
            f"No Transport-capable squadron can fly between {draft.origin.name} and "
            f"{draft.destination.name} this turn (aircraft, pilots, base type or "
            "helicopter range)."
        ]
        settings = self.game_model.game.settings
        land = self.game_model.game.theater if default_zones_enabled(settings) else None
        for cp in (draft.origin, draft.destination):
            if (reason := ctld_zone_unavailable_reason(cp, land)) is not None:
                lines.append(reason)
        return "\n".join(lines)

    def update_state(self) -> None:
        has_units = bool(self.selected_units)
        squadron = self.dest_panel.selected_squadron
        draft = self.draft_transfer()
        warning: Optional[str] = None
        if squadron is not None:
            self.submit_button.setText("Create Transport Mission")
            if draft is not None and has_units:
                warning = player_airlift_problem(squadron, draft, draft.destination)
        else:
            self.submit_button.setText("Create Transfer Order")
            if (
                self.dest_panel.request_airlift
                and draft is not None
                and self.dest_panel.squadron.count() <= 1
            ):
                warning = self._no_squadron_warning(draft)
        self.dest_panel.show_warning(warning)
        blocked = squadron is not None and warning is not None
        self.submit_button.setDisabled(not has_units or blocked)

    def on_submit(self) -> None:
        destination = self.dest_panel.current
        transfers = self.selected_units
        for unit_type, count in transfers.items():
            logging.info(
                f"Transferring {count} {unit_type} from {self.origin} to "
                f"{destination}"
            )

        transfer = TransferOrder(
            origin=self.origin,
            destination=destination,
            units=transfers,
            request_airflift=self.dest_panel.request_airlift,
        )
        now = self.game_model.sim_controller.current_time_in_sim
        squadron = self.dest_panel.selected_squadron
        if squadron is not None:
            try:
                self.game_model.transfer_model.new_player_airlift(
                    transfer, squadron, now
                )
            except PlayerAirliftError as ex:
                QMessageBox.warning(self, "Cannot create Transport mission", str(ex))
                return
        else:
            self.game_model.transfer_model.new_transfer(transfer, now)
        # Airlifts add packages to the ATO behind the model's back.
        self.game_model.ato_model.replace_from_game(player=True)
        self.close()

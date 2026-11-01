import logging
from typing import Callable

from PySide6.QtCore import QItemSelection, QItemSelectionModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QVBoxLayout,
    QApplication,
    QInputDialog,
    QLineEdit,
    QMessageBox,
)

from game.ato.flighttype import FlightType
from game.commands import (
    AircraftPurchaseAdapter,
    CommandError,
    change_aircraft_order,
    TransferDestination,
    new_pilot_refusal,
    order_repair,
    rename_pilot,
    room_at_base,
    set_primary_task,
    squadron_repair_id,
    transfer_destinations,
    transfer_squadron,
)
from game.gamelock import game_lock
from game.server import EventStream
from game.sim import GameUpdateEvents
from game.squadrons import Pilot, Squadron
from game.squadrons.career import Career
from game.squadrons.pilot import PilotStatus
from game.theater import ParkingType
from qt_ui.delegates import TwoColumnRowDelegate
from qt_ui.models import AtoModel, SquadronModel
from qt_ui.simcontroller import SimController
from qt_ui.windows.CareerDialog import CareerDialog
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.widgets.combos.QSquadronLiverySelector import SquadronLiverySelector
from qt_ui.widgets.combos.primarytaskselector import PrimaryTaskSelector


class PilotDelegate(TwoColumnRowDelegate):
    def __init__(self, squadron_model: SquadronModel) -> None:
        super().__init__(rows=2, columns=2, font_size=12)
        self.squadron_model = squadron_model

    @staticmethod
    def pilot(index: QModelIndex) -> Pilot:
        return index.data(SquadronModel.PilotRole)

    def text_for(self, index: QModelIndex, row: int, column: int) -> str:
        pilot = self.pilot(index)
        if (row, column) == (0, 0):
            return self.squadron_model.data(index, Qt.ItemDataRole.DisplayRole)
        elif (row, column) == (0, 1):
            flown = pilot.record.missions_flown
            missions = "missions" if flown != 1 else "mission"
            return f"{flown} {missions} flown"
        elif (row, column) == (1, 0):
            who = "Player" if pilot.player else "AI"
            skill = self.squadron_model.squadron.pilot_skill(pilot)
            return f"{who} - Level: {skill.value}"
        elif (row, column) == (1, 1):
            # Dead pilots have their own list and active pilots need no label, so
            # surface any other state (on leave, downed awaiting CSAR, recovering).
            return pilot.status.value if pilot.status is not PilotStatus.Active else ""
        return ""


class PilotList(QListView):
    """List view for displaying a squadron's pilots."""

    def __init__(self, squadron_model: SquadronModel) -> None:
        super().__init__()
        self.squadron_model = squadron_model

        self.setItemDelegate(PilotDelegate(self.squadron_model))
        self.setModel(self.squadron_model)
        self.selectionModel().setCurrentIndex(
            self.squadron_model.index(0, 0, QModelIndex()),
            QItemSelectionModel.SelectionFlag.Select,
        )

        # self.setIconSize(QSize(91, 24))
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)


class AutoAssignedTaskControls(QVBoxLayout):
    def __init__(self, squadron_model: SquadronModel) -> None:
        super().__init__()
        self.squadron_model = squadron_model

        self.addWidget(QLabel("Auto-assignable mission types"))

        def make_callback(toggled_task: FlightType) -> Callable[[bool], None]:
            def callback(checked: bool) -> None:
                self.on_toggled(toggled_task, checked)

            return callback

        for task in FlightType:
            if self.squadron_model.squadron.capable_of(task):
                checkbox = QCheckBox(text=task.value)
                checkbox.setChecked(squadron_model.is_auto_assignable(task))
                checkbox.toggled.connect(make_callback(task))
                self.addWidget(checkbox)

        self.addStretch()

    def on_toggled(self, task: FlightType, checked: bool) -> None:
        self.squadron_model.set_auto_assignable(task, checked)


class SquadronDestinationComboBox(QComboBox):
    def __init__(self, squadron: Squadron) -> None:
        super().__init__()
        with game_lock():
            room = room_at_base(squadron)
            destinations = transfer_destinations(squadron)
        self.addItem(
            f"Remain at {squadron.location} (room for {room} more aircraft)",
            squadron.location,
        )
        self.setCurrentIndex(0)
        for idx, destination in enumerate(destinations, 1):
            cp = destination.control_point
            if destination.overflow:
                self._warn_about_overflow(destination.control_point.name, destination)
            if destination.refusal is None:
                text = f"Transfer to {cp} (room for {destination.room} more aircraft)"
            else:
                text = f"Transfer to {cp} not possible ({destination.refusal})"
            self.addItem(text, cp)
            if destination.refusal is not None:
                self.model().item(idx).setEnabled(False)
            if cp == squadron.destination:
                self.setCurrentIndex(idx)

    @staticmethod
    def _warn_about_overflow(name: str, destination: TransferDestination) -> None:
        overflow_msg = "".join(
            f"{s.name} - {s.aircraft.variant_id}<br/>" for s in destination.overflow
        )
        QMessageBox.warning(
            None,
            "Insufficient parking space detected!",
            f"Insufficient parking space was detected at {name}:<br/><br/>"
            f"{overflow_msg}<br/>"
            f"Consider moving these squadrons to different airfield "
            "to avoid possible air-starts.",
        )


class SquadronDialog(QDialog):
    """Dialog window showing a squadron."""

    def __init__(
        self,
        ato_model: AtoModel,
        squadron_model: SquadronModel,
        sim_controller: SimController,
        parent,
    ) -> None:
        super().__init__(parent)
        self.ato_model = ato_model
        self.squadron_model = squadron_model
        # The main list (and the action buttons) operate on living pilots only;
        # dead pilots get their own read-only list below.
        self.squadron_model.pilot_filter = "living"
        self.dead_squadron_model = SquadronModel(
            squadron_model.squadron, pilot_filter="dead"
        )
        self.sim_controller = sim_controller

        self.setMinimumSize(1000, 440)
        self.setWindowTitle(str(squadron_model.squadron))
        # TODO: self.setWindowIcon()

        layout = QVBoxLayout()
        self.setLayout(layout)

        columns = QHBoxLayout()
        layout.addLayout(columns)

        left_column = QVBoxLayout()
        columns.addLayout(left_column)

        left_column.addWidget(
            QLabel(f"Aircraft: {self.squadron_model.squadron.aircraft.display_name}")
        )

        left_column.addWidget(QLabel("Primary task"))
        self.primary_task_selector = PrimaryTaskSelector.for_squadron(
            self.squadron_model.squadron
        )
        self.primary_task_selector.currentIndexChanged.connect(
            self.on_task_index_changed
        )
        left_column.addWidget(self.primary_task_selector)

        left_column.addWidget(QLabel("Livery"))
        self.livery_selector = SquadronLiverySelector(self.squadron_model.squadron)
        left_column.addWidget(self.livery_selector)

        left_column.addWidget(QLabel("Aircraft inventory"))
        self.aircraft_stats_label = QLabel(self._aircraft_stats_text())
        left_column.addWidget(self.aircraft_stats_label)

        # Buying aircraft is only meaningful for the player's own squadrons.
        if self.squadron.player.is_blue:
            self.purchase_adapter: AircraftPurchaseAdapter = AircraftPurchaseAdapter(
                self.squadron.location
            )

            purchase_row = QHBoxLayout()
            self.sell_aircraft_button = QPushButton("-")
            self.sell_aircraft_button.setProperty("style", "btn-sell")
            self.sell_aircraft_button.setMaximumWidth(28)
            self.sell_aircraft_button.clicked.connect(self.sell_aircraft)
            purchase_row.addWidget(self.sell_aircraft_button)

            self.on_order_label = QLabel()
            purchase_row.addWidget(self.on_order_label)

            self.buy_aircraft_button = QPushButton("+")
            self.buy_aircraft_button.setProperty("style", "btn-buy")
            self.buy_aircraft_button.setMaximumWidth(28)
            self.buy_aircraft_button.clicked.connect(self.buy_aircraft)
            purchase_row.addWidget(self.buy_aircraft_button)

            self.price_label = QLabel()
            purchase_row.addWidget(self.price_label)
            purchase_row.addStretch()
            left_column.addLayout(purchase_row)

            self.parking_slots_label = QLabel()
            left_column.addWidget(self.parking_slots_label)

            self.repair_aircraft_button = QPushButton()
            self.repair_aircraft_button.setProperty("style", "btn-success")
            self.repair_aircraft_button.clicked.connect(self.repair_aircraft)
            left_column.addWidget(self.repair_aircraft_button)

            self._refresh_aircraft_controls()

        auto_assigned_tasks = AutoAssignedTaskControls(squadron_model)
        left_column.addLayout(auto_assigned_tasks)

        right_column = QVBoxLayout()
        columns.addLayout(right_column)

        right_column.addWidget(QLabel("Pilots"))
        self.pilot_list = PilotList(squadron_model)
        self.pilot_list.selectionModel().selectionChanged.connect(
            self.on_selection_changed
        )
        right_column.addWidget(self.pilot_list, stretch=3)

        right_column.addWidget(QLabel("Killed in action"))
        self.dead_pilot_list = PilotList(self.dead_squadron_model)
        right_column.addWidget(self.dead_pilot_list, stretch=1)
        self.dead_pilot_list.doubleClicked.connect(self.show_dead_pilot_career)

        button_panel = QHBoxLayout()

        self.transfer_destination = SquadronDestinationComboBox(squadron_model.squadron)
        self.transfer_destination.currentIndexChanged.connect(
            self.on_destination_changed
        )
        button_panel.addWidget(self.transfer_destination)

        button_panel.addStretch()
        layout.addLayout(button_panel)

        self.new_player_button = QPushButton("New player pilot")
        self.new_player_button.setProperty("style", "start-button")
        self.new_player_button.clicked.connect(self.create_player_pilot)
        self.reset_new_player_state()
        button_panel.addWidget(
            self.new_player_button, alignment=Qt.AlignmentFlag.AlignRight
        )

        self.career_button = QPushButton("Career")
        self.career_button.setProperty("style", "start-button")
        self.career_button.clicked.connect(self.show_selected_career)
        self.reset_career_state(self.pilot_list.currentIndex())
        button_panel.addWidget(
            self.career_button, alignment=Qt.AlignmentFlag.AlignRight
        )

        self.rename_button = QPushButton("Rename pilot")
        self.rename_button.setProperty("style", "start-button")
        self.rename_button.clicked.connect(self.rename_pilot)
        button_panel.addWidget(
            self.rename_button, alignment=Qt.AlignmentFlag.AlignRight
        )

        self.toggle_ai_button = QPushButton()
        self.reset_ai_toggle_state(self.pilot_list.currentIndex())
        self.toggle_ai_button.setProperty("style", "start-button")
        self.toggle_ai_button.clicked.connect(self.toggle_ai)
        button_panel.addWidget(
            self.toggle_ai_button, alignment=Qt.AlignmentFlag.AlignRight
        )

        self.toggle_leave_button = QPushButton()
        self.reset_leave_toggle_state(self.pilot_list.currentIndex())
        self.toggle_leave_button.setProperty("style", "start-button")
        self.toggle_leave_button.clicked.connect(self.toggle_leave)
        button_panel.addWidget(
            self.toggle_leave_button, alignment=Qt.AlignmentFlag.AlignRight
        )

    @property
    def squadron(self) -> Squadron:
        return self.squadron_model.squadron

    def _aircraft_stats_text(self) -> str:
        s = self.squadron
        text = (
            f"Initial: {s.initial_aircraft}\n"
            f"Current: {s.owned_aircraft}\n"
            f"Destroyed: {s.destroyed_aircraft}\n"
            f"Purchased: {s.purchased_aircraft}"
        )
        if s.aircraft_in_maintenance:
            text += (
                f"\nAvailable: {s.available_aircraft}\n"
                + s.maintenance_text.replace(", ", "\n")
            )
        return text

    @staticmethod
    def _purchase_amount() -> int:
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ShiftModifier:
            return 10
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            return 5
        return 1

    def _refresh_aircraft_controls(self) -> None:
        self.aircraft_stats_label.setText(self._aircraft_stats_text())
        self.on_order_label.setText(f"On order: {self.squadron.pending_deliveries}")
        self.price_label.setText(f"$ {self.purchase_adapter.price_of(self.squadron)} M")
        parking_type = ParkingType().from_squadron(self.squadron)
        free_slots = self.squadron.location.unclaimed_parking(parking_type)
        self.parking_slots_label.setText(
            f"{free_slots} additional parking "
            f"{'slot' if free_slots == 1 else 'slots'} available at "
            f"{self.squadron.location}"
        )
        can_buy = self.purchase_adapter.can_buy(self.squadron)
        self.buy_aircraft_button.setEnabled(can_buy)
        self.buy_aircraft_button.setToolTip(
            "Buy aircraft. Use Shift or Ctrl to buy 10 or 5 at once."
            if can_buy
            else "Cannot buy: insufficient budget, parking or squadron capacity."
        )
        can_sell = self.purchase_adapter.can_sell_or_cancel(self.squadron)
        self.sell_aircraft_button.setEnabled(can_sell)
        self.sell_aircraft_button.setToolTip(
            "Sell aircraft. Use Shift or Ctrl to sell 10 or 5 at once."
            if can_sell
            else "Cannot sell: no idle aircraft or pending orders."
        )
        self._refresh_repair_button()

    def _refresh_repair_button(self) -> None:
        """Paid accelerated repair of the aircraft in maintenance (PER-01.2), only
        offered when the setting allows it."""
        squadron = self.squadron
        settings = self.ato_model.game.settings
        if not (
            settings.expedited_aircraft_repair and squadron.aircraft_in_maintenance
        ):
            self.repair_aircraft_button.setVisible(False)
            return
        cost = squadron.expedited_repair_cost
        self.repair_aircraft_button.setVisible(True)
        self.repair_aircraft_button.setText(
            f"Repair {squadron.aircraft_in_maintenance} aircraft now [{cost}M]"
        )
        affordable = cost <= squadron.coalition.budget
        self.repair_aircraft_button.setEnabled(affordable)
        self.repair_aircraft_button.setToolTip(
            "Finish every repair of this squadron at once."
            if affordable
            else "Cannot repair: insufficient budget."
        )

    def repair_aircraft(self) -> None:
        game = self.ato_model.game
        self._command(
            "Could not repair aircraft",
            lambda events: order_repair(
                game,
                self.squadron.location,
                squadron_repair_id(self.squadron),
                events,
            ),
        )
        self._refresh_aircraft_controls()
        GameUpdateSignal.get_instance().updateBudget(game)

    def _command(
        self, failure: str, action: Callable[[GameUpdateEvents], object]
    ) -> bool:
        """Runs a command under the game lock; shows why it was refused."""
        try:
            with game_lock(), EventStream.event_context() as events:
                action(events)
        except CommandError as ex:
            QMessageBox.warning(
                self, failure, ex.message, QMessageBox.StandardButton.Ok
            )
            return False
        return True

    def _change_order(self, quantity: int, failure: str) -> None:
        # Same rules as the web base screen (WEB-02.2).
        try:
            with game_lock(), EventStream.event_context() as events:
                change_aircraft_order(
                    self.squadron.location, self.squadron, quantity, events
                )
        except CommandError as ex:
            QMessageBox.warning(
                self, failure, ex.message, QMessageBox.StandardButton.Ok
            )
        finally:
            self._refresh_aircraft_controls()
            GameUpdateSignal.get_instance().updateBudget(self.ato_model.game)

    def buy_aircraft(self) -> None:
        self._change_order(self._purchase_amount(), "Purchase failed")

    def sell_aircraft(self) -> None:
        self._change_order(-self._purchase_amount(), "Sale failed")

    def on_destination_changed(self, index: int) -> None:
        destination = self.transfer_destination.itemData(index)
        self._command(
            "Could not change squadron destination",
            lambda events: transfer_squadron(
                self.squadron,
                destination,
                self.sim_controller.current_time_in_sim,
                events,
            ),
        )
        self.ato_model.replace_from_game(player=True)

    def check_disabled_button_states(
        self, button: QPushButton, index: QModelIndex
    ) -> bool:
        if not index.isValid():
            button.setText("No pilot selected")
            button.setDisabled(True)
            return True
        pilot = self.squadron_model.pilot_at_index(index)
        if not pilot.alive:
            button.setText("Pilot is dead")
            button.setDisabled(True)
            return True
        return False

    def rename_pilot(self) -> None:
        index = self.pilot_list.currentIndex()
        if not index.isValid():
            logging.error("Cannot toggle player/AI: no pilot is selected")
            return
        p = self.squadron_model.pilot_at_index(index)
        text, ok = QInputDialog.getText(
            self, "Rename pilot", "New name: ", QLineEdit.EchoMode.Normal
        )
        if ok:
            self._command("Could not rename pilot", lambda _: rename_pilot(p, text))
            self.squadron_model.layoutChanged.emit()

    def reset_new_player_state(self) -> None:
        refusal = new_pilot_refusal(self.squadron)
        if refusal is not None:
            self.new_player_button.setDisabled(True)
            self.new_player_button.setToolTip(refusal)
        else:
            self.new_player_button.setEnabled(True)
            self.new_player_button.setToolTip(
                "Add your own pilot to the squadron. Their career starts now."
            )

    def create_player_pilot(self) -> None:
        name, ok = QInputDialog.getText(
            self, "New player pilot", "Pilot name: ", QLineEdit.EchoMode.Normal
        )
        name = name.strip()
        if ok and name:
            self._command(
                "Could not add pilot",
                lambda _: self.squadron_model.create_player_pilot(name),
            )
            self.reset_new_player_state()

    def reset_career_state(self, index: QModelIndex) -> None:
        pilot = self.squadron_model.pilot_at_index(index) if index.isValid() else None
        if pilot is not None and pilot.player:
            self.career_button.setEnabled(True)
            self.career_button.setToolTip(
                "Logbook, rank, decorations and mission history of this pilot."
            )
        else:
            self.career_button.setDisabled(True)
            self.career_button.setToolTip(
                "Select a player pilot to see their career. Double-click a "
                "fallen player pilot to see theirs."
            )

    def show_career(self, pilot: Pilot) -> None:
        if pilot.player:
            CareerDialog(Career(pilot, self.squadron), self).exec()

    def show_selected_career(self) -> None:
        index = self.pilot_list.currentIndex()
        if index.isValid():
            self.show_career(self.squadron_model.pilot_at_index(index))

    def show_dead_pilot_career(self, index: QModelIndex) -> None:
        self.show_career(self.dead_squadron_model.pilot_at_index(index))

    def toggle_ai(self) -> None:
        index = self.pilot_list.currentIndex()
        if not index.isValid():
            logging.error("Cannot toggle player/AI: no pilot is selected")
            return
        self._command(
            "Could not change pilot",
            lambda _: self.squadron_model.toggle_ai_state(index),
        )
        self.reset_career_state(self.pilot_list.currentIndex())

    def reset_ai_toggle_state(self, index: QModelIndex) -> None:
        if self.check_disabled_button_states(self.toggle_ai_button, index):
            return
        if not self.squadron_model.squadron.aircraft.flyable:
            self.toggle_ai_button.setText("Not flyable")
            self.toggle_ai_button.setDisabled(True)
            return
        self.toggle_ai_button.setEnabled(True)
        pilot = self.squadron_model.pilot_at_index(index)
        self.toggle_ai_button.setText(
            "Convert to AI" if pilot.player else "Convert to player"
        )

    def toggle_leave(self) -> None:
        index = self.pilot_list.currentIndex()
        if not index.isValid():
            logging.error("Cannot toggle on leave state: no pilot is selected")
            return
        self._command(
            "Could not change pilot",
            lambda _: self.squadron_model.toggle_leave_state(index),
        )
        self.reset_new_player_state()

    def reset_leave_toggle_state(self, index: QModelIndex) -> None:
        if self.check_disabled_button_states(self.toggle_leave_button, index):
            return
        pilot = self.squadron_model.pilot_at_index(index)
        # Leave only applies to active/on-leave pilots. Downed, recovering and captive
        # pilots cannot be toggled, so disable the button and label their state.
        if pilot.status not in (PilotStatus.Active, PilotStatus.OnLeave):
            self.toggle_leave_button.setEnabled(False)
            self.toggle_leave_button.setText(pilot.status.value)
            return
        self.toggle_leave_button.setEnabled(
            not pilot.on_leave or self.squadron_model.squadron.has_unfilled_pilot_slots
        )
        self.toggle_leave_button.setText(
            "Return from leave" if pilot.on_leave else "Send on leave"
        )

    def on_selection_changed(
        self, selected: QItemSelection, _deselected: QItemSelection
    ) -> None:
        index = selected.indexes()[0]
        self.reset_ai_toggle_state(index)
        self.reset_leave_toggle_state(index)
        self.reset_career_state(index)

    def on_task_index_changed(self, index: int) -> None:
        task = self.primary_task_selector.itemData(index)
        if task is None:
            raise RuntimeError("Selected task cannot be None")
        self._command(
            "Could not change primary task",
            lambda _: set_primary_task(self.squadron, task),
        )

from collections.abc import Iterator

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QPushButton,
    QInputDialog,
    QMessageBox,
    QWidget,
)

from game import Game
from game.ato.flight import Flight
from game.ato.flightmember import FlightMember
from game.commands import CommandError
from game.commands.flightpayload import backup_payload_file, save_member_payload
from game.data.weapons import Pylon
from game.gamelock import game_lock
from qt_ui.blocksignals import block_signals
from qt_ui.windows.mission.flight.payload.QPylonEditor import QPylonEditor


class QLoadoutEditor(QGroupBox):
    saved = Signal(str)

    def __init__(self, flight: Flight, flight_member: FlightMember, game: Game) -> None:
        super().__init__("Use custom loadout")
        self.flight = flight
        self.flight_member = flight_member
        self.game = game
        self.setCheckable(True)
        self.setChecked(flight_member.loadout.is_custom)

        vbox = QVBoxLayout(self)
        layout = QGridLayout(self)

        for i, pylon in enumerate(Pylon.iter_pylons(self.flight.unit_type)):
            label = QLabel(f"<b>{pylon.number}</b>")
            label.setSizePolicy(
                QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            )
            layout.addWidget(label, i, 0)
            layout.addWidget(QPylonEditor(game, flight, flight_member, pylon), i, 1)

        vbox.addLayout(layout)

        layout = QGridLayout(self)
        save_btn = QPushButton("Save Payload")
        save_btn.setProperty("style", "btn-danger")
        save_btn.setMaximumWidth(250)
        save_btn.clicked.connect(self._save_payload)
        layout.addWidget(save_btn, 0, 0)

        purge_btn = QPushButton("Create Backup")
        purge_btn.setProperty("style", "btn-success")
        purge_btn.setMaximumWidth(250)
        purge_btn.clicked.connect(self._backup_payloads)
        layout.addWidget(purge_btn, 0, 1)
        vbox.addLayout(layout)

        self.setLayout(vbox)

        for pylon_editor in self.iter_pylon_editors():
            pylon_editor.set_from(self.flight_member.loadout)

    def iter_pylon_editors(self) -> Iterator[QPylonEditor]:
        yield from self.findChildren(QPylonEditor)

    def set_flight_member(self, flight_member: FlightMember) -> None:
        self.flight_member = flight_member
        with block_signals(self):
            self.setChecked(self.flight_member.use_custom_loadout)
        for pylon_editor in self.iter_pylon_editors():
            pylon_editor.set_flight_member(flight_member)

    def _backup_payloads(self) -> None:
        with game_lock():
            backup_file = backup_payload_file(self.flight)
        if backup_file is None:
            return
        QMessageBox.information(
            QWidget(),
            "Backup Payload",
            f"Payload file for {self.flight.unit_type.dcs_unit_type.id} was backed up successfully.\n"
            f"Location: {backup_file}",
        )

    def _save_payload(self) -> None:
        payload_name_input = self._create_input_dialog()
        if not payload_name_input.exec():
            return
        payload_name = payload_name_input.textValue()
        try:
            with game_lock():
                payload_file = save_member_payload(
                    self.flight, self.flight_member, payload_name
                )
        except CommandError as ex:
            QMessageBox.critical(QWidget(), "Payload not saved", ex.message)
            return
        self.saved.emit(payload_name.strip())
        QMessageBox.information(
            QWidget(),
            "Payload Saved",
            f"Payload for {self.flight.unit_type.dcs_unit_type.id} was successfully saved.\n"
            f"Location: {payload_file}",
        )

    def _create_input_dialog(self):
        payload_name_input = QInputDialog()
        payload_name_input.setWindowTitle("Save payload")
        payload_name_input.setLabelText("Enter a name for the payload to be saved:")
        payload_name_input.setTextValue(f"Custom {self.flight.flight_type.name}")
        payload_name_input.setFixedWidth(500)
        return payload_name_input

    def reset_pylons(self) -> None:
        self.flight_member.use_custom_loadout = self.isChecked()
        if not self.isChecked():
            for pylon_editor in self.iter_pylon_editors():
                pylon_editor.set_from(self.flight_member.loadout)

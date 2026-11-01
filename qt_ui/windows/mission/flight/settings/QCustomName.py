from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLineEdit, QLabel, QMessageBox

from game.ato.flight import Flight
from game.commands import CommandError
from game.commands.flightsettings import set_flight_custom_name


class QFlightCustomName(QGroupBox):
    def __init__(self, flight: Flight):
        super(QFlightCustomName, self).__init__()

        self.flight = flight

        self.layout = QHBoxLayout()
        self.custom_name_label = QLabel(f"Custom Name:")
        self.custom_name_input = QLineEdit(flight.custom_name)
        self.custom_name_input.textChanged.connect(self.on_change)
        self.layout.addWidget(self.custom_name_label)
        self.layout.addWidget(self.custom_name_input)
        self.setLayout(self.layout)

    def on_change(self) -> None:
        try:
            set_flight_custom_name(self.flight, self.custom_name_input.text())
        except CommandError as ex:
            QMessageBox.critical(self, "Could not edit flight", str(ex))

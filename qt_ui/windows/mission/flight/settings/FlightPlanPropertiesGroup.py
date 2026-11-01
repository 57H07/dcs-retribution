from datetime import timedelta

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QTimeEdit,
    QHBoxLayout,
    QCheckBox,
)

from game import Game
from game.ato.flight import Flight
from game.commands import CommandError
from game.commands.flightsettings import (
    divert_options,
    set_flight_divert,
    set_flight_tot_offset,
)
from qt_ui.models import PackageModel
from qt_ui.widgets.QLabeledWidget import QLabeledWidget
from qt_ui.widgets.combos.QArrivalAirfieldSelector import QArrivalAirfieldSelector
from qt_ui.windows.mission.flight.waypoints.QFlightWaypointList import (
    QFlightWaypointList,
)


class FlightPlanPropertiesGroup(QGroupBox):
    def __init__(
        self,
        game: Game,
        package_model: PackageModel,
        flight: Flight,
        flight_wpt_list: QFlightWaypointList,
    ) -> None:
        super().__init__("Flight plan properties")
        self.game = game
        self.package_model = package_model
        self.flight = flight
        self.flight_wpt_list = flight_wpt_list

        layout = QVBoxLayout()

        self.departure_time = QLabel()
        layout.addLayout(
            QLabeledWidget(
                f"Departing from <b>{flight.departure.name}</b>", self.departure_time
            )
        )
        self.package_model.tot_changed.connect(self.update_departure_time)
        self.update_departure_time()

        tot_offset_layout = QHBoxLayout()
        layout.addLayout(tot_offset_layout)

        delay = int(self.flight.flight_plan.tot_offset.total_seconds())
        negative = delay < 0
        if negative:
            delay = -delay
        hours = delay // 3600
        minutes = delay // 60 % 60
        seconds = delay % 60

        tot_offset_layout.addWidget(QLabel("TOT Offset (minutes:seconds)"))
        tot_offset_layout.addStretch()
        self.negative_offset_checkbox = QCheckBox("Ahead of package")
        self.negative_offset_checkbox.setChecked(negative)
        self.negative_offset_checkbox.toggled.connect(self.toggle_negative_offset)
        tot_offset_layout.addWidget(self.negative_offset_checkbox)

        self.tot_offset_spinner = QTimeEdit(QTime(hours, minutes, seconds))
        self.tot_offset_spinner.setMaximumTime(QTime(59, 0))
        self.tot_offset_spinner.setDisplayFormat("mm:ss")
        self.tot_offset_spinner.timeChanged.connect(self.set_tot_offset)
        self.tot_offset_spinner.setToolTip("Flight TOT offset from package TOT")
        tot_offset_layout.addWidget(self.tot_offset_spinner)

        layout.addWidget(
            QLabel(
                "Determined based on the package TOT. Edit the "
                "package to adjust the TOT."
            )
        )

        arrival_label = QLabel(f"<b>{flight.arrival.name}</b>")
        layout.addLayout(QLabeledWidget("Arrival:", arrival_label))

        self.divert = QArrivalAirfieldSelector(
            divert_options(flight),
            flight.unit_type,
            "None",
        )
        self.divert.currentIndexChanged.connect(self.set_divert)
        if flight.divert is not None:
            self.divert.setCurrentText(flight.divert.name)
        layout.addLayout(QLabeledWidget("Divert:", self.divert))

        self.setLayout(layout)

    def update_departure_time(self) -> None:
        if not self.flight.package.flights:
            # This is theoretically impossible, but for some reason the dialog that owns
            # this object QEditFlightDialog does not dispose properly on close, so this
            # handler may be called for a flight whose package has been canceled, which
            # is an invalid state for calling anything in TotEstimator.
            return
        self.departure_time.setText(
            f"At {self.flight.flight_plan.startup_time():%H:%M:%S}"
        )
        self.flight_wpt_list.update_list()

    def set_divert(self, index: int) -> None:
        try:
            set_flight_divert(self.flight, self.divert.itemData(index))
        except CommandError as ex:
            QMessageBox.critical(
                self,
                "Could not update flight plan",
                str(ex),
                QMessageBox.StandardButton.Ok,
            )

    def _apply_tot_offset(self, offset: timedelta) -> None:
        try:
            set_flight_tot_offset(
                self.flight,
                offset,
                self.package_model.game_model.sim_controller.current_time_in_sim,
            )
        except CommandError as ex:
            QMessageBox.critical(self, "Could not edit flight", str(ex))
            return
        self.package_model.update_tot()
        self.update_departure_time()

    def set_tot_offset(self, offset: QTime) -> None:
        delta = timedelta(
            hours=offset.hour(), minutes=offset.minute(), seconds=offset.second()
        )
        if self.negative_offset_checkbox.isChecked():
            delta = -delta
        self._apply_tot_offset(delta)

    def toggle_negative_offset(self) -> None:
        self._apply_tot_offset(-self.flight.flight_plan.tot_offset)

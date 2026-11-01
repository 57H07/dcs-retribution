from PySide6.QtCore import QItemSelectionModel, QPoint, QModelIndex
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QHeaderView,
    QTableView,
    QStyledItemDelegate,
    QWidget,
    QStyleOptionViewItem,
    QDoubleSpinBox,
)

from game.ato.flight import Flight
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.package import Package
from game.commands.flightroute import MAX_ALTITUDE_FT, waypoint_times
from game.gamelock import game_lock
from game.utils import Distance
from qt_ui.windows.mission.flight.waypoints.QFlightWaypointItem import QWaypointItem

HEADER_LABELS = ["Name", "Alt (ft)", "Alt Type", "TOT/DEPART"]


class AltitudeEditorDelegate(QStyledItemDelegate):
    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QDoubleSpinBox:
        editor = QDoubleSpinBox(parent)
        editor.setMinimum(0)
        editor.setMaximum(MAX_ALTITUDE_FT)
        editor.setDecimals(0)
        editor.setSingleStep(1000)
        return editor


class QFlightWaypointList(QTableView):
    def __init__(self, package: Package, flight: Flight):
        super().__init__()
        self.package = package
        self.flight = flight

        self.model = QStandardItemModel(self)
        self.model.itemChanged.connect(self.on_changed)
        self.setModel(self.model)
        self.model.setHorizontalHeaderLabels(HEADER_LABELS)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.update_list()

        self.selectionModel().setCurrentIndex(
            self.indexAt(QPoint(1, 1)), QItemSelectionModel.SelectionFlag.Select
        )

        self.altitude_editor_delegate = AltitudeEditorDelegate(self)
        self.setItemDelegateForColumn(1, self.altitude_editor_delegate)

    def update_list(self) -> None:
        # ignore signals when updating list so on_changed does not fire
        self.model.blockSignals(True)
        try:
            # We need to keep just the row and rebuild the index later because the
            # QModelIndex will not be valid after the model is cleared.
            current_index = self.currentIndex().row()
            self.model.clear()

            self.model.setHorizontalHeaderLabels(HEADER_LABELS)

            waypoints = self.flight.flight_plan.waypoints
            times = waypoint_times(self.flight)
            for row, waypoint in enumerate(waypoints):
                self._add_waypoint_row(row, waypoint, str(times[row] or ""))
            self.selectionModel().setCurrentIndex(
                self.model.index(current_index, 0),
                QItemSelectionModel.SelectionFlag.Select,
            )
            self.model.setVerticalHeaderLabels([str(n) for n in range(len(waypoints))])
            self.verticalHeader().setMaximumWidth(25)

            self.resizeColumnsToContents()
            total_column_width = self.verticalHeader().width() + self.lineWidth()
            for i in range(0, self.model.columnCount()):
                total_column_width += self.columnWidth(i) + self.lineWidth()
            self.setFixedWidth(total_column_width)
        finally:
            # stop ignoring signals
            self.model.blockSignals(False)
            self.update(self.currentIndex())

    def _add_waypoint_row(
        self,
        row: int,
        waypoint: FlightWaypoint,
        tot: str,
    ) -> None:
        self.model.insertRow(self.model.rowCount())

        self.model.setItem(row, 0, QWaypointItem(waypoint, row))

        altitude = round(waypoint.alt.feet)
        altitude_item = QStandardItem(f"{altitude}")
        altitude_item.setEditable(True)
        self.model.setItem(row, 1, altitude_item)

        altitude_type = "AGL" if waypoint.alt_type == "RADIO" else "MSL"
        altitude_type_item = QStandardItem(f"{altitude_type}")
        altitude_type_item.setEditable(False)
        self.model.setItem(row, 2, altitude_type_item)

        tot_item = QStandardItem(tot)
        tot_item.setEditable(False)
        self.model.setItem(row, 3, tot_item)

    def on_changed(self) -> None:
        with game_lock():
            for i in range(self.model.rowCount()):
                # waypoints materializes a fresh list each access; resolve once per row
                # so the altitude and name edits land on the same waypoint object.
                waypoint = self.flight.flight_plan.waypoints[i]
                altitude_feet = float(self.model.item(i, 1).text())
                waypoint.alt = Distance.from_feet(altitude_feet)
                waypoint.apply_name_edit(self.model.item(i, 0).text())

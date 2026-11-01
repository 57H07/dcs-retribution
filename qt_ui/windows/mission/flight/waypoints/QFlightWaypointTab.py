from typing import Iterable, List, Optional

from PySide6.QtCore import Signal, Qt, QModelIndex
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from game import Game
from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.package import Package
from game.commands import CommandError
from game.commands.flightroute import (
    add_rtb_waypoint,
    default_bulk_altitude,
    delete_waypoint,
    deletion_degrades,
    insert_nav_after,
    recreate_route,
    set_en_route_altitude,
)
from game.gamelock import game_lock
from game.theater import Player
from qt_ui.windows.mission.flight.waypoints.QFlightWaypointList import (
    QFlightWaypointList,
)
from qt_ui.windows.mission.flight.waypoints.QPredefinedWaypointSelectionWindow import (
    QPredefinedWaypointSelectionWindow,
)


class QFlightWaypointTab(QFrame):
    loadout_changed = Signal()

    def __init__(self, game: Game, package: Package, flight: Flight):
        super(QFlightWaypointTab, self).__init__()
        self.game = game
        self.coalition = game.coalition_for(player=Player.BLUE)
        self.package = package
        self.flight = flight

        self.flight_waypoint_list: Optional[QFlightWaypointList] = None
        self.rtb_waypoint: Optional[QPushButton] = None
        self.delete_selected: Optional[QPushButton] = None
        self.add_nav_waypoint: Optional[QPushButton] = None
        self.open_fast_waypoint_button: Optional[QPushButton] = None
        self.recreate_buttons: List[QPushButton] = []
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        self.flight_waypoint_list = QFlightWaypointList(self.package, self.flight)
        layout.addWidget(self.flight_waypoint_list, 0, 0)

        rlayout = QVBoxLayout()
        layout.addLayout(rlayout, 0, 1)

        rlayout.addWidget(QLabel("<strong>Altitude :</strong>"))
        rlayout.addWidget(QLabel("<small>Set all en-route waypoints</small>"))
        bulk_alt_layout = QHBoxLayout()
        self.bulk_altitude = QSpinBox()
        self.bulk_altitude.setMinimum(0)
        self.bulk_altitude.setMaximum(40000)
        self.bulk_altitude.setSingleStep(1000)
        self.bulk_altitude.setValue(default_bulk_altitude(self.flight))
        self.bulk_altitude.setSuffix(" ft")
        self.bulk_altitude.setToolTip(
            "Apply this MSL altitude to every en-route waypoint. Takeoff, landing, "
            "divert, target, landing-zone, tanker, and ground (AGL) waypoints are "
            "left unchanged."
        )
        bulk_alt_layout.addWidget(self.bulk_altitude)
        self.apply_bulk_altitude = QPushButton("Apply to all")
        self.apply_bulk_altitude.clicked.connect(self.on_apply_bulk_altitude)
        bulk_alt_layout.addWidget(self.apply_bulk_altitude)
        rlayout.addLayout(bulk_alt_layout)

        rlayout.addWidget(QLabel("<strong>Generator :</strong>"))
        rlayout.addWidget(QLabel("<small>AI compatible</small>"))

        self.recreate_buttons.clear()
        for task in self.package.target.mission_types(for_player=Player.BLUE):
            if task == FlightType.AIR_ASSAULT and not self.game.settings.plugin_option(
                "ctld"
            ):
                # Only add Air Assault if ctld plugin is enabled
                continue

            def make_closure(arg):
                def closure():
                    return self.confirm_recreate(arg)

                return closure

            button = QPushButton(f"Recreate as {task}")
            button.clicked.connect(make_closure(task))
            rlayout.addWidget(button)
            self.recreate_buttons.append(button)

        self.add_nav_waypoint = QPushButton("Insert NAV point")
        self.add_nav_waypoint.clicked.connect(self.on_add_nav)
        rlayout.addWidget(self.add_nav_waypoint)

        rlayout.addWidget(QLabel("<strong>Advanced : </strong>"))
        rlayout.addWidget(QLabel("<small>Do not use for AI flights</small>"))

        self.rtb_waypoint = QPushButton("Add RTB Waypoint")
        self.rtb_waypoint.clicked.connect(self.on_rtb_waypoint)
        rlayout.addWidget(self.rtb_waypoint)

        self.delete_selected = QPushButton("Delete Selected")
        self.delete_selected.clicked.connect(self.on_delete_waypoint)
        rlayout.addWidget(self.delete_selected)

        self.open_fast_waypoint_button = QPushButton("Add Waypoint")
        self.open_fast_waypoint_button.clicked.connect(self.on_fast_waypoint)
        rlayout.addWidget(self.open_fast_waypoint_button)
        rlayout.addStretch()
        self.setLayout(layout)

    def on_add_nav(self):
        selected = self.flight_waypoint_list.selectedIndexes()
        if not selected:
            return
        index: QModelIndex = selected[0]
        self.flight_waypoint_list.setCurrentIndex(index)
        try:
            with game_lock():
                insert_nav_after(self.flight, index.row())
        except CommandError as ex:
            QMessageBox.critical(QWidget(), "Failed to add NAV waypoint", str(ex))
        else:
            self.on_change()

    def on_delete_waypoint(self):
        waypoints = []
        selection = self.flight_waypoint_list.selectionModel()
        # One index per selected cell: a whole row counts once.
        for row in sorted({index.row() for index in selection.selectedIndexes()}):
            if row > 0:
                waypoints.append(self.flight.flight_plan.waypoints[row])
        for waypoint in waypoints:
            self.delete_waypoint(waypoint)
        self.on_change()

    def delete_waypoint(self, waypoint: FlightWaypoint) -> None:
        if deletion_degrades(self.flight, waypoint) and not self.confirm_degrade():
            return
        with game_lock():
            delete_waypoint(self.flight, waypoint, allow_degrade=True)

    def confirm_degrade(self, parent: Optional[QWidget] = None) -> bool:
        result = QMessageBox.warning(
            parent if parent else self,
            "Degrade flight-plan?",
            "Deleting the selected waypoint(s) will require degradation to a custom flight-plan. "
            "A custom flight-plan will no longer respect the TOTs of the package.<br><br>"
            "<b>Are you sure you wish to continue?</b>",
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def on_fast_waypoint(self):
        self.subwindow = QPredefinedWaypointSelectionWindow(
            self.game, self.flight, self.flight_waypoint_list
        )
        self.subwindow.waypoints_added.connect(self.on_waypoints_added)
        self.subwindow.show()

    def on_waypoints_added(self, waypoints: Iterable[FlightWaypoint]) -> None:
        if not waypoints:
            return
        with game_lock():
            self.flight.flight_plan.layout.custom_waypoints.extend(waypoints)
        self.on_change()

    def on_rtb_waypoint(self):
        with game_lock():
            add_rtb_waypoint(self.flight, allow_degrade=True)
        self.on_change()

    def confirm_recreate(self, task: FlightType) -> None:
        result = QMessageBox.question(
            self,
            "Regenerate flight?",
            (
                "Changing the flight type will reset its flight plan. Do you want "
                "to continue?"
            ),
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if result == QMessageBox.StandardButton.Yes:
            try:
                with game_lock():
                    recreate_route(self.flight.coalition.game, self.flight, task)
            except CommandError as ex:
                QMessageBox.critical(
                    self,
                    "Could not recreate flight",
                    str(ex),
                    QMessageBox.StandardButton.Ok,
                )
            self.loadout_changed.emit()
            self.flight_waypoint_list.update_list()
            self.on_change()

    def on_apply_bulk_altitude(self) -> None:
        with game_lock():
            set_en_route_altitude(self.flight, self.bulk_altitude.value())
        self.on_change()

    def on_change(self):
        self.flight_waypoint_list.update_list()
        self.flight_waypoint_list.on_changed()
        self.update()

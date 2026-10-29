from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
)

import qt_ui.uiconstants as CONST
from game import Game
from game.ato.package import Package
from game.commands import (
    CommandError,
    fix_tots,
    flights_missing_pilots,
    generate_mission,
    packages_starting_in_the_past,
    skip_turn,
)
from game.game import TurnState
from game.gamelock import game_lock
from game.utils import meters
from qt_ui.models import GameModel
from qt_ui.simcontroller import SimController
from qt_ui.theme_manager import theme_signals
from qt_ui.uiflags import UiFlags
from qt_ui.widgets.QBudgetBox import QBudgetBox
from qt_ui.widgets.QConditionsWidget import QConditionsWidget
from qt_ui.widgets.QFactionsInfos import QFactionsInfos
from qt_ui.widgets.QIntelBox import QIntelBox
from qt_ui.widgets.clientslots import MaxPlayerCount
from qt_ui.widgets.simspeedcontrols import SimSpeedControls
from qt_ui.windows.AirWingDialog import AirWingDialog
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.PendingTransfersDialog import PendingTransfersDialog
from qt_ui.windows.QWaitingForMissionResultWindow import QWaitingForMissionResultWindow


class QTopPanel(QFrame):
    """Top panel of the Qt main window, only without the web UI (WEB-01.1).

    The web top bar replaces it. It stays for the Qt UI until the web UI is on by
    default (WEB-05.2), then goes with its widgets (WEB-09). The take-off rules live
    in `game.commands.mission`, shared with the web UI.
    """

    def __init__(
        self, game_model: GameModel, sim_controller: SimController, ui_flags: UiFlags
    ) -> None:
        super(QTopPanel, self).__init__()
        self.game_model = game_model
        self.sim_controller = sim_controller
        self.dialog: Optional[QDialog] = None

        self.setMaximumHeight(70)

        self.conditionsWidget = QConditionsWidget(sim_controller)
        self.budgetBox = QBudgetBox(self.game)

        pass_turn_text = "Pass Turn"
        if not self.game or self.game.turn == 0:
            pass_turn_text = "Begin Campaign"
        self.passTurnButton = QPushButton(pass_turn_text)
        self.passTurnButton.setProperty("style", "btn-primary")
        self.passTurnButton.clicked.connect(self.passTurn)
        if not self.game:
            self.passTurnButton.setEnabled(False)

        self.proceedButton = QPushButton("Take off")
        self.proceedButton.setProperty("style", "start-button")
        self.proceedButton.clicked.connect(self.launch_mission)
        if not self.game or self.game.turn == 0:
            self.proceedButton.setEnabled(False)

        self.refresh_theme_icons()
        theme_signals().theme_changed.connect(self.refresh_theme_icons)

        self.factionsInfos = QFactionsInfos(self.game)

        self.air_wing = QPushButton("Air Wing")
        self.air_wing.setDisabled(True)
        self.air_wing.setProperty("style", "btn-primary")
        self.air_wing.clicked.connect(self.open_air_wing)

        self.transfers = QPushButton("Transfers")
        self.transfers.setDisabled(True)
        self.transfers.setProperty("style", "btn-primary")
        self.transfers.clicked.connect(self.open_transfers)

        self.intel_box = QIntelBox(self.game)

        self.buttonBox = QGroupBox("Misc")
        self.buttonBoxLayout = QHBoxLayout()
        self.buttonBoxLayout.addWidget(self.air_wing)
        self.buttonBoxLayout.addWidget(self.transfers)
        self.buttonBox.setLayout(self.buttonBoxLayout)

        self.simSpeedControls = SimSpeedControls(sim_controller)

        self.proceedBox = QGroupBox("Proceed")
        self.proceedBoxLayout = QHBoxLayout()
        if ui_flags.show_sim_speed_controls:
            self.proceedBoxLayout.addLayout(self.simSpeedControls)
        self.proceedBoxLayout.addLayout(MaxPlayerCount(self.game_model.ato_model))
        self.proceedBoxLayout.addWidget(self.passTurnButton)
        self.proceedBoxLayout.addWidget(self.proceedButton)
        self.proceedBox.setLayout(self.proceedBoxLayout)

        self.controls = [
            self.air_wing,
            self.transfers,
            self.simSpeedControls,
            self.passTurnButton,
            self.proceedButton,
        ]

        self.layout = QHBoxLayout()

        self.layout.addWidget(self.factionsInfos)
        self.layout.addWidget(self.conditionsWidget)
        self.layout.addWidget(self.budgetBox)
        self.layout.addWidget(self.intel_box)
        self.layout.addWidget(self.buttonBox)
        self.layout.addStretch(1)
        self.layout.addWidget(self.proceedBox)

        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)

        GameUpdateSignal.get_instance().gameupdated.connect(self.setGame)
        GameUpdateSignal.get_instance().budgetupdated.connect(self.budget_update)

    def refresh_theme_icons(self, _variant: str = "") -> None:
        self.passTurnButton.setIcon(CONST.ICONS["PassTurn"])
        self.proceedButton.setIcon(CONST.ICONS["Proceed"])

    @property
    def game(self) -> Optional[Game]:
        return self.game_model.game

    def setGame(self, game: Optional[Game]):
        if game is None:
            return

        self.air_wing.setEnabled(True)
        self.transfers.setEnabled(True)

        self.conditionsWidget.setCurrentTurn(game.turn, game.conditions)

        if game.conditions.weather.clouds:
            base_m = game.conditions.weather.clouds.base
            base_ft = int(meters(base_m).feet)
            self.conditionsWidget.setToolTip(f"Cloud Base: {base_m}m / {base_ft}ft")
        else:
            self.conditionsWidget.setToolTip("")

        self.intel_box.set_game(game)
        self.budgetBox.setGame(game)
        self.factionsInfos.setGame(game)

        self.setControls(True)

        if game.turn > 0:
            self.passTurnButton.setText("Pass Turn")
        elif game.turn == 0:
            self.passTurnButton.setText("Begin Campaign")
            self.proceedButton.setEnabled(False)
            self.simSpeedControls.setEnabled(False)
        else:
            raise RuntimeError(f"game.turn out of bounds!\n  value = {game.turn}")

    def open_air_wing(self):
        self.dialog = AirWingDialog(self.game_model, self.window())
        self.dialog.show()

    def open_transfers(self):
        self.dialog = PendingTransfersDialog(self.game_model)
        self.dialog.show()

    def passTurn(self):
        with game_lock():
            state = skip_turn(self.game)
        self.on_turn_passed(state)

    def on_turn_passed(self, state: TurnState) -> None:
        """Refresh the Qt widgets once a turn was skipped, here or by the web UI."""
        GameUpdateSignal.get_instance().updateGame(self.game)
        GameUpdateSignal.get_instance().gameStateChanged(state)
        self.proceedButton.setEnabled(True)

    def confirm_no_client_launch(self) -> bool:
        result = QMessageBox.question(
            self,
            "Continue without player pilots?",
            (
                "No player pilots have been assigned to flights. Continuing will allow "
                "the AI to perform the mission, but players will be unable to "
                "participate.<br />"
                "<br />"
                "To assign player pilots to a flight, select a package from the "
                "Packages panel on the left of the main window, and then a flight from "
                "the Flights panel below the Packages panel. The edit button below the "
                "Flights panel will allow you to assign specific pilots to the flight. "
                "If you have no player pilots available, the checkbox next to the "
                "name will convert them to a player.<br />"
                "<br />Click 'Yes' to continue with an AI only mission"
                "<br />Click 'No' if you'd like to make more changes."
            ),
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        return result == QMessageBox.StandardButton.Yes

    def confirm_negative_start_time(self, negative_starts: List[Package]) -> bool:
        formatted = "<br />".join(
            [f"{p.primary_task} {p.target.name}" for p in negative_starts]
        )
        mbox = QMessageBox(
            QMessageBox.Icon.Question,
            "Continue with past start times?",
            (
                "Some flights in the following packages have start times set "
                "earlier than mission start time:<br />"
                "<br />"
                f"{formatted}<br />"
                "<br />"
                "Flight start times are estimated based on the package TOT, so it "
                "is possible that not all flights will be able to reach the "
                "target area at their assigned times.<br />"
                "<br />"
                "You can either continue with the mission as planned, with the "
                "misplanned flights potentially flying too fast and/or missing "
                "their rendezvous; automatically fix negative TOTs; or cancel "
                "mission start and fix the packages manually."
            ),
            parent=self,
        )
        auto = mbox.addButton(
            "Fix TOTs automatically", QMessageBox.ButtonRole.ActionRole
        )
        ignore = mbox.addButton(
            "Continue without fixing", QMessageBox.ButtonRole.DestructiveRole
        )
        cancel = mbox.addButton(QMessageBox.StandardButton.Cancel)
        mbox.setEscapeButton(cancel)
        mbox.exec()
        clicked = mbox.clickedButton()
        if clicked == auto:
            with game_lock():
                fix_tots(negative_starts, self.sim_controller.current_time_in_sim)
            return True
        elif clicked == ignore:
            return True
        return False

    def check_no_missing_pilots(self) -> bool:
        missing_pilots = flights_missing_pilots(self.game)
        if not missing_pilots:
            return False

        formatted = "<br />".join(
            [f"{p.primary_task} {p.target}: {f}" for p, f in missing_pilots]
        )
        mbox = QMessageBox(
            QMessageBox.Icon.Critical,
            "Flights are missing pilots",
            (
                "The following flights are missing one or more pilots:<br />"
                "<br />"
                f"{formatted}<br />"
                "<br />"
                "You must either assign pilots to those flights or cancel those "
                "missions."
            ),
            parent=self,
        )
        mbox.setEscapeButton(mbox.addButton(QMessageBox.StandardButton.Close))
        mbox.exec()
        return True

    def launch_mission(self):
        """Finishes planning and waits for mission completion."""
        if not self.game.ato_has_clients() and not self.confirm_no_client_launch():
            return

        if self.check_no_missing_pilots():
            return

        negative_starts = packages_starting_in_the_past(
            self.game, self.sim_controller.current_time_in_sim
        )
        if negative_starts:
            if not self.confirm_negative_start_time(negative_starts):
                return

        try:
            with game_lock():
                generate_mission(self.game, self.sim_controller)
        except CommandError as error:
            QMessageBox.critical(self, "Cannot take off", error.message)
            return

        waiting = QWaitingForMissionResultWindow(self.game, self.sim_controller, self)
        waiting.exec()

    def budget_update(self, game: Game):
        self.budgetBox.setGame(game)

    def setControls(self, enabled: bool):
        for controller in self.controls:
            controller.setEnabled(enabled)

    def check_for_contact(self) -> bool:
        if (
            len(self.game.blue.ato.packages) == 0
            and len(self.game.red.ato.packages) == 0
        ):
            mbox = QMessageBox(
                QMessageBox.Icon.Critical,
                "No flights planned",
                (
                    "No flights are planned and fast forward to first contact "
                    "is enabled. You must either plan flights or disable fast forward."
                ),
                parent=self,
            )
            mbox.setEscapeButton(mbox.addButton(QMessageBox.StandardButton.Close))
            mbox.exec()
            return False
        return True

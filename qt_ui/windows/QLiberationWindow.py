import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QGuiApplication,
    QIcon,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import qt_ui.uiconstants as CONST
from game import Game, VERSION, persistency, Migrator
from game.ato import Flight, Package
from game.debriefing import Debriefing
from game.game import TurnState
from game.layout import LAYOUTS
from game.persistency import pre_pretense_backups_dir
from game.pretense.pretensemissiongenerator import PretenseMissionGenerator
from game.server import EventStream, GameContext
from game.server.dependencies import QtCallbacks, QtContext, UiOptions
from game.server.qt.models import QtDialog
from game.commands import CommandError
from game.native import (
    ExternalLink,
    FileActionResult,
    NativeContext,
    open_game,
    save_game,
    save_game_as,
)
from game.theater import ControlPoint, MissionTarget, TheaterGroundObject
from game.theater.controlpoint import motorpools_inside_capture_zone
from qt_ui import liberation_install
from qt_ui.dialogs import Dialog
from qt_ui.models import GameModel
from qt_ui.nativebridge import QtNativeBridge, QtShell
from qt_ui.simcontroller import SimController
from qt_ui.theme_manager import theme_signals
from qt_ui.uiflags import UiFlags
from qt_ui.uncaughtexceptionhandler import UncaughtExceptionHandler
from qt_ui.widgets.QTopPanel import QTopPanel
from qt_ui.widgets.ato import QAirTaskingOrderPanel
from qt_ui.widgets.map.QLiberationMap import QLiberationMap
from qt_ui.windows.AirWingDialog import AirWingDialog
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.PendingTransfersDialog import PendingTransfersDialog
from qt_ui.windows.QDebriefingWindow import QDebriefingWindow
from qt_ui.windows.basemenu.QBaseMenu2 import QBaseMenu2
from qt_ui.windows.finances.QFinancesMenu import QFinancesMenu
from qt_ui.windows.groundobject.QGroundObjectMenu import QGroundObjectMenu
from qt_ui.windows.infos.QInfoPanel import QInfoPanel
from qt_ui.windows.intel import IntelWindow
from qt_ui.windows.logs.QLogsWindow import QLogsWindow
from qt_ui.windows.newgame.QNewGameWizard import NewGameWizard
from qt_ui.windows.notes.QNotesWindow import QNotesWindow
from qt_ui.windows.preferences.QLiberationPreferencesWindow import (
    QLiberationPreferencesWindow,
)
from qt_ui.windows.settings.QSettingsWindow import QSettingsWindow
from qt_ui.windows.stats.QStatsWindow import QStatsWindow


class QLiberationWindow(QMainWindow):
    new_package_signal = Signal(MissionTarget)
    tgo_info_signal = Signal(TheaterGroundObject)
    control_point_info_signal = Signal(ControlPoint)
    select_flight_signal = Signal(Flight)
    # Emitted from an API worker thread: queued onto the Qt main thread.
    turn_passed_signal = Signal(TurnState)
    # WEB-00.3: Qt screens opened by the web shell, from API worker threads too.
    open_dialog_signal = Signal(object)
    edit_package_signal = Signal(object)
    # WEB-05.1: the web UI accepted a mission result; Qt shows the debriefing.
    results_accepted_signal = Signal(object)
    # WEB-07.1: a web command changed the game in depth (cheats, settings).
    game_changed_signal = Signal()

    def __init__(self, game: Game | None, ui_flags: UiFlags) -> None:
        super().__init__()

        self._uncaught_exception_handler = UncaughtExceptionHandler(self)
        # WEB-00.3: the web view fills the window and replaces the Qt chrome.
        self.web_ui = liberation_install.web_ui_enabled()
        UiOptions.set(show_sim_speed_controls=ui_flags.show_sim_speed_controls)
        # The Qt top panel only exists without the web UI (WEB-01.1).
        self.top_panel: QTopPanel | None = None
        self.dialog: QWidget | None = None

        self.game = game
        self.sim_controller = SimController(self.game)
        self.sim_controller.sim_update.connect(EventStream.put_nowait)
        self.game_model = GameModel(game, self.sim_controller)
        GameContext.set_model(self.game_model)
        self.new_package_signal.connect(
            lambda target: Dialog.open_new_package_dialog(target, self)
        )
        self.tgo_info_signal.connect(self.open_tgo_info_dialog)
        self.control_point_info_signal.connect(self.open_control_point_info_dialog)
        self.select_flight_signal.connect(self.on_select_flight)
        self.open_dialog_signal.connect(self.open_dialog)
        self.edit_package_signal.connect(self.open_edit_package_dialog)
        self.results_accepted_signal.connect(self.on_results_accepted)
        self.game_changed_signal.connect(
            lambda: GameUpdateSignal.get_instance().updateGame(self.game)
        )
        QtContext.set_callbacks(
            QtCallbacks(
                lambda target: self.new_package_signal.emit(target),
                lambda tgo: self.tgo_info_signal.emit(tgo),
                lambda cp: self.control_point_info_signal.emit(cp),
                lambda flight: self.select_flight_signal.emit(flight),
                turn_passed=lambda state: self.turn_passed_signal.emit(state),
                open_dialog=lambda dialog: self.open_dialog_signal.emit(dialog),
                edit_package=lambda package: self.edit_package_signal.emit(package),
                game_changed=lambda: self.game_changed_signal.emit(),
                results_accepted=lambda d: self.results_accepted_signal.emit(d),
            )
        )
        # WEB-00.7: file dialogs, folders, links and quit for the web UI.
        self.native_bridge = QtNativeBridge(
            QtShell(
                self,
                on_game_loaded=self._on_game_opened,
                on_game_saved=self._on_game_saved,
                open_new_game=self.newGame,
                quit=self.close,
            )
        )
        NativeContext.set_bridge(self.native_bridge)
        Dialog.set_game(self.game_model)
        self.ato_panel = QAirTaskingOrderPanel(self.game_model)
        self.info_panel = QInfoPanel(self.game)
        self.liberation_map = QLiberationMap(
            self.game_model, ui_flags.dev_ui_webserver, self, web_shell=self.web_ui
        )

        self.setGeometry(300, 100, 270, 100)
        self.updateWindowTitle()
        self.setWindowIcon(QIcon("./resources/icon.png"))
        self.statusBar().showMessage("Ready")

        self.initUi(ui_flags)
        self.initActions()
        self.initToolbar()
        self.initMenuBar()
        self.connectSignals()

        # Default to maximized on the main display if we don't have any persistent
        # configuration.
        screen = QGuiApplication.primaryScreen().availableSize()
        self.setGeometry(0, 0, screen.width(), screen.height())
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # But override it with the saved configuration if it exists.
        self._restore_window_geometry()
        if self.web_ui:
            # After restoreState(), which would show the toolbars again.
            self._hide_qt_chrome()

        if self.game is None:
            last_save_file = liberation_install.get_last_save_file()
            if last_save_file:
                logging.info("Loading last saved game : " + str(last_save_file))
                game = persistency.load_game(last_save_file)
                game = self.migrate_game(game, last_save_file)
                self.onGameGenerated(game)
                self.updateWindowTitle(last_save_file if game else None)
            else:
                logging.info("No existing save game")
        else:
            self.onGameGenerated(self.game)

    def initUi(self, ui_flags: UiFlags) -> None:
        if self.web_ui:
            self._init_web_ui(ui_flags)
            return
        hbox = QSplitter(Qt.Orientation.Horizontal)
        vbox = QSplitter(Qt.Orientation.Vertical)
        hbox.addWidget(self.ato_panel)
        hbox.addWidget(vbox)
        vbox.addWidget(self.liberation_map)
        vbox.addWidget(self.info_panel)

        # Will make the ATO sidebar as small as necessary to fit the content. In
        # practice this means it is sized by the hints in the panel.
        hbox.setSizes([1, 10000000])
        vbox.setSizes([600, 100])

        self.top_panel = QTopPanel(self.game_model, self.sim_controller, ui_flags)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.top_panel)
        vbox.addWidget(hbox)

        central_widget = QWidget()
        central_widget.setLayout(vbox)
        self.setCentralWidget(central_widget)

    def _init_web_ui(self, ui_flags: UiFlags) -> None:
        """The map fills the window; the Qt panels move to windows opened on demand.

        The web top bar replaces QTopPanel (WEB-01.1): it is not created at all.
        """
        self.ato_window = self._panel_window("Air Tasking Order", self.ato_panel)
        self.reports_window = self._panel_window("Reports", self.info_panel)
        self.setCentralWidget(self.liberation_map)

    def _panel_window(self, title: str, panel: QWidget) -> QWidget:
        window = QWidget(self, Qt.WindowType.Window)
        window.setWindowTitle(title)
        layout = QVBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(panel)
        window.resize(500, 700)
        return window

    def _hide_qt_chrome(self) -> None:
        self.menuBar().hide()
        for bar in (self.tool_bar, self.links_bar, self.actions_bar):
            bar.hide()
        self.statusBar().hide()
        # The web shell owns the keyboard (Ctrl+S...): no double trigger.
        for action in (
            self.newGameAction,
            self.openAction,
            self.saveGameAction,
            self.saveAsAction,
        ):
            action.setShortcut(QKeySequence())

    def connectSignals(self):
        GameUpdateSignal.get_instance().gameupdated.connect(self.setGame)
        self.turn_passed_signal.connect(self.on_turn_passed)
        GameUpdateSignal.get_instance().debriefingReceived.connect(self.onDebriefing)
        GameUpdateSignal.get_instance().game_state_changed.connect(self.onEndGame)
        theme_signals().theme_changed.connect(self.refresh_theme_icons)

    def initActions(self):
        self.newGameAction = QAction("&New Game", self)
        self.newGameAction.triggered.connect(self.newGame)
        self.newGameAction.setShortcut("CTRL+N")

        self.openAction = QAction("&Open", self)
        self.openAction.triggered.connect(self.openFile)
        self.openAction.setShortcut("CTRL+O")

        self.saveGameAction = QAction("&Save", self)
        self.saveGameAction.triggered.connect(self.saveGame)
        self.saveGameAction.setShortcut("CTRL+S")

        self.saveAsAction = QAction("Save &As", self)
        self.saveAsAction.triggered.connect(self.saveGameAs)
        self.saveAsAction.setShortcut("CTRL+A")

        self.showAboutDialogAction = QAction("&About DCS Retribution", self)
        self.showAboutDialogAction.setIcon(QIcon.fromTheme("help-about"))
        self.showAboutDialogAction.triggered.connect(self.showAboutDialog)

        self.showLiberationPrefDialogAction = QAction("&Preferences", self)
        self.showLiberationPrefDialogAction.setIcon(QIcon.fromTheme("help-about"))
        self.showLiberationPrefDialogAction.triggered.connect(self.showLiberationDialog)

        self.openDiscordAction = QAction("&Discord Server", self)
        self.openDiscordAction.triggered.connect(
            lambda: self.open_link(ExternalLink.DISCORD)
        )

        self.openGithubAction = QAction("&Github Repo", self)
        self.openGithubAction.triggered.connect(
            lambda: self.open_link(ExternalLink.GITHUB)
        )

        self.ukraineAction = QAction("&Ukraine", self)
        self.ukraineAction.setIcon(CONST.ICONS["Ukraine"])
        self.ukraineAction.triggered.connect(
            lambda: self.open_link(ExternalLink.UKRAINE)
        )

        self.pretenseLinkAction = QAction("&DCS: Pretense", self)
        self.pretenseLinkAction.setIcon(QIcon(CONST.ICONS["Pretense_discord"]))
        self.pretenseLinkAction.triggered.connect(
            lambda: self.open_link(ExternalLink.PRETENSE_DISCORD)
        )

        self.newPretenseAction = QAction(
            "&Generate a Pretense Campaign from the running campaign", self
        )
        self.newPretenseAction.setIcon(QIcon(CONST.ICONS["Pretense_generate"]))
        self.newPretenseAction.triggered.connect(self.newPretenseCampaign)

        self.openLogsAction = QAction("Show &logs", self)
        self.openLogsAction.triggered.connect(self.showLogsDialog)

        self.openSettingsAction = QAction("Settings", self)
        self.openSettingsAction.triggered.connect(self.showSettingsDialog)

        self.openStatsAction = QAction("Stats", self)
        self.openStatsAction.triggered.connect(self.showStatsDialog)

        self.openNotesAction = QAction("Notes", self)
        self.openNotesAction.triggered.connect(self.showNotesDialog)

        self.importTemplatesAction = QAction("Import Layouts", self)
        self.importTemplatesAction.triggered.connect(self.import_templates)

        self.refresh_theme_icons()
        self.enable_game_actions(False)

    def refresh_theme_icons(self, _variant: str = "") -> None:
        """Sets the icons that depend on the theme (reloaded on theme change)."""
        for action, icon in (
            (self.newGameAction, "New"),
            (self.openAction, "Open"),
            (self.saveGameAction, "Save"),
            (self.saveAsAction, "Save"),
            (self.openDiscordAction, "Discord"),
            (self.openGithubAction, "Github"),
            (self.openSettingsAction, "Settings"),
            (self.openStatsAction, "Statistics"),
            (self.openNotesAction, "Notes"),
        ):
            action.setIcon(QIcon(CONST.ICONS[icon]))

    def enable_game_actions(self, enabled: bool):
        self.openSettingsAction.setVisible(enabled)
        self.openStatsAction.setVisible(enabled)
        self.openNotesAction.setVisible(enabled)

        # Also Disable SaveAction to prevent Keyboard Shortcut
        self.saveGameAction.setEnabled(enabled)
        self.saveGameAction.setVisible(enabled)
        self.saveAsAction.setEnabled(enabled)
        self.saveAsAction.setVisible(enabled)

    def initToolbar(self):
        self.tool_bar = self.addToolBar("File")
        self.tool_bar.addAction(self.newGameAction)
        self.tool_bar.addAction(self.openAction)
        self.tool_bar.addAction(self.saveGameAction)

        self.links_bar = self.addToolBar("Links")
        self.links_bar.addAction(self.openDiscordAction)
        self.links_bar.addAction(self.openGithubAction)
        self.links_bar.addAction(self.ukraineAction)
        self.links_bar.addAction(self.pretenseLinkAction)
        self.links_bar.addAction(self.newPretenseAction)

        self.actions_bar = self.addToolBar("Actions")
        self.actions_bar.addAction(self.openSettingsAction)
        self.actions_bar.addAction(self.openStatsAction)
        self.actions_bar.addAction(self.openNotesAction)

    def initMenuBar(self):
        self.menu = self.menuBar()

        file_menu = self.menu.addMenu("&File")
        file_menu.addAction(self.newGameAction)
        file_menu.addAction(self.openAction)
        file_menu.addSeparator()
        file_menu.addAction(self.saveGameAction)
        file_menu.addAction(self.saveAsAction)
        file_menu.addSeparator()
        file_menu.addAction(self.showLiberationPrefDialogAction)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close)

        tools_menu = self.menu.addMenu("&Developer tools")
        tools_menu.addAction(self.importTemplatesAction)

        help_menu = self.menu.addMenu("&Help")
        help_menu.addAction(self.openDiscordAction)
        help_menu.addAction(self.openGithubAction)
        help_menu.addAction(self.ukraineAction)
        help_menu.addAction("&Releases", lambda: self.open_link(ExternalLink.RELEASES))
        help_menu.addAction(
            "&Online Manual", lambda: self.open_link(ExternalLink.MANUAL)
        )
        help_menu.addAction(
            "&ED Forum Thread", lambda: self.open_link(ExternalLink.FORUM_THREAD)
        )
        help_menu.addAction(
            "Report an &issue", lambda: self.open_link(ExternalLink.ISSUES)
        )
        help_menu.addAction(self.openLogsAction)

        help_menu.addSeparator()
        help_menu.addAction(self.showAboutDialogAction)

    @staticmethod
    def make_display_rule_action(
        display_rule, group: Optional[QActionGroup] = None
    ) -> QAction:
        def make_check_closure():
            def closure():
                display_rule.value = action.isChecked()

            return closure

        action = QAction(f"&{display_rule.menu_text}", group)

        if display_rule.menu_text in CONST.ICONS.keys():
            action.setIcon(CONST.ICONS[display_rule.menu_text])

        action.setCheckable(True)
        action.setChecked(display_rule.value)
        action.toggled.connect(make_check_closure())
        return action

    def newGame(self):
        wizard = NewGameWizard(self)
        wizard.show()
        wizard.accepted.connect(lambda: self.onGameGenerated(wizard.generatedGame))

    def newPretenseCampaign(self):
        output = persistency.mission_path_for("pretense_campaign.miz")
        try:
            PretenseMissionGenerator(
                self.game, self.game.conditions.start_time
            ).generate_miz(output)
        except Exception as e:
            now = datetime.now()
            date_time = now.strftime("%Y-%d-%mT%H_%M_%S")
            path = pre_pretense_backups_dir()
            tgt = path / f"pre-pretense-backup_{date_time}.retribution"
            path /= f".pre-pretense-backup.retribution"
            if path.exists():
                with open(path, "rb") as source:
                    with open(tgt, "wb") as target:
                        target.write(source.read())
            raise e

        title = "Pretense campaign generated"
        msg = f"A Pretense campaign mission has been successfully generated in {output}"
        QMessageBox.information(QApplication.focusWidget(), title, msg, QMessageBox.Ok)

    def openFile(self) -> None:
        self._run_file_action(open_game)

    def _on_game_opened(self, game: Game, path: str) -> None:
        """A save file was read and migrated (`game.native.open_game`)."""
        self._warn_motorpool_capture_zone(game)
        GameUpdateSignal.get_instance().game_loaded.emit(game)
        self.updateWindowTitle(path)

    def migrate_game(self, game, path):
        if game:
            is_liberation = ".liberation" in path
            try:
                Migrator(game, is_liberation)
                return game
            except Exception as e:
                logging.exception(e)
                self.incompatible_save_popup(path)
        else:
            self.incompatible_save_popup(path)
        return None

    def incompatible_save_popup(self, path):
        relative_path = Path(path)
        QMessageBox.critical(
            self,
            "Incompatible save",
            "Incompatible save file detected, please report the issue on GitHub or Discord.\n"
            f"Make sure to include the campaign that fails to load, i.e.:\n\n{relative_path}",
        )

    def saveGame(self) -> None:
        logging.info("Saving game")
        self._run_file_action(save_game)

    def saveGameAs(self) -> None:
        self._run_file_action(save_game_as)

    def _run_file_action(
        self, action: Callable[..., FileActionResult]
    ) -> FileActionResult | None:
        """Runs a shared file action from a Qt menu, on the Qt main thread."""
        try:
            return action(self.native_bridge, lambda: self.game)
        except CommandError as error:
            QMessageBox.critical(self, "DCS Retribution", error.message)
            return None

    def _on_game_saved(self, path: str) -> None:
        liberation_install.setup_last_save_file(path)
        liberation_install.save_config()
        self.updateWindowTitle(path)

    def updateWindowTitle(self, save_path: Optional[str] = None) -> None:
        """
        Window title format: DCS Retribution - vX.X.X - campaign_name - file_name
        Campaign name is shown if a game is loaded and has a campaign_name.
        File name is appended only if save_path is provided.
        """
        window_title = f"DCS Retribution - v{VERSION}"

        if self.game and self.game.campaign_name:
            window_title += f" - {self.game.campaign_name}"

        if save_path:
            file_name = save_path.split("/")[-1].rsplit(".", 1)[0]
            window_title += f" - {file_name}"

        self.setWindowTitle(window_title)

    def onGameGenerated(self, game: Game):
        logging.info("On Game generated")
        self.game = game
        self._warn_motorpool_capture_zone(game)
        self.updateWindowTitle()
        GameUpdateSignal.get_instance().game_loaded.emit(self.game)

    def _warn_motorpool_capture_zone(self, game: Optional[Game]) -> None:
        if game is None or not game.settings.motorpool_enabled:
            return
        violations = motorpools_inside_capture_zone(game.theater.controlpoints)
        if not violations:
            return
        # Defer so the modal lands on top of the main window rather than racing
        # window setup during the startup auto-load.
        QTimer.singleShot(
            0,
            lambda: QMessageBox.warning(
                self,
                "Motorpool placement problem",
                "These motorpools are inside their control point's 3 km capture "
                "zone, so their parked reserve vehicles will block base capture. "
                "Move each Garage_A marker outside the capture radius:\n\n"
                + "\n".join(str(v) for v in violations),
            ),
        )

    def onEndGame(self, state: TurnState):
        if state == TurnState.CONTINUE:
            return

        for window in QApplication.topLevelWidgets():
            if window is not self:
                window.close()

        GameUpdateSignal.get_instance().updateGame(None)

        if self.top_panel is not None:
            self.top_panel.setControls(False)

        title = "Victory!" if TurnState.WIN else "Defeat!"
        msgvar = "won" if TurnState.WIN else "lost"
        msg = f"You have {msgvar} the campaign, do you wish to start a new one?"
        result = QMessageBox.information(
            QApplication.focusWidget(),
            title,
            msg,
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )

        if result is not None and result == QMessageBox.StandardButton.Yes:
            self.newGame()

    def setGame(self, game: Optional[Game]):
        try:
            self.game = game
            if self.info_panel is not None:
                self.info_panel.setGame(game)
            self.sim_controller.set_game(game)
            self.game_model.set(self.game)
            self.game_model.init_comms_registry()
        except AttributeError:
            logging.exception("Incompatible save game")
            QMessageBox.critical(
                self,
                "Could not load save game",
                "The save game you have loaded is incompatible with this "
                "version of DCS Retribution.\n"
                "\n"
                f"{traceback.format_exc()}",
                QMessageBox.StandardButton.Ok,
            )
            GameUpdateSignal.get_instance().updateGame(None)
        finally:
            self.enable_game_actions(self.game is not None)

    def showAboutDialog(self):
        contributors = [
            "shdwp",
            "Khopa",
            "ColonelPanic",
            "RndName",
            "Roach",
            "Malakhit",
            "Wrycu",
            "calvinmorrow",
            "JohanAberg",
            "Deus",
            "SiKruger",
            "Mustang-25",
            "bgreman",
            "magwo",
            "SnappyComebacks",
            "kavinsky",
            "Schneefl0cke",
            "pbzweihander",
            "Raskil",
            "nosv1",
            "jake-lewis",
            "teamMOYA",
            "benedikt-wegmann",
            "movq",
            "bbirchnz",
            "eddiwood",
            "root0fall",
            "calvinmorrow",
            "UKayeF",
            "Captain Cody",
            "steveveepee",
            "pedromagueija",
            "parithon",
            "TheCandianVendingMachine",
            "bwRavencl",
            "davidp57",
            "Plob",
            "Hawkmoon",
            "alrik11es",
            "Starfire13",
            "Hornet2041/Lion",
            "SgtFuzzle17",
            "Doc_of_Mur",
            "NickJZX",
            "Sith1144",
            "Raffson",
            "MetalStormGhost",
            "HolyOrangeJuice (WRL)",
            "Adecarcer",
            "pande4360",
            "zhexu14",
            "ColonelAkirNakesh",
            "Nosajthedevil",
            "kivipe",
            "Turbolious",
            "ingax01",
            "M-Chimiste",
            "tmz42",
            "Drexyl",
            "Druss99",
            "Biggus22",
            "StillClock1",
        ]
        text = (
            "<h3>DCS Retribution " + VERSION + "</h3>" + "<b>Source code : </b>"
            "<a href='https://github.com/dcs-retribution/dcs-retribution'>"
            "https://github.com/dcs-retribution/dcs-retribution </a>"
            + "<h4>Authors</h4>"
            + "<p>DCS Retribution is an (independent) fork of DCS Liberation, "
            "which was originally developed by <b>shdwp</b>. "
            "DCS Liberation 2.0 is a partial rewrite based on this work by <b>Khopa</b>. "
            "DCS Retribution was forked during development of "
            "DCS Liberation v6.0.0 in 2022 by <b>Raffson</> & <b>MetalStormGhost</>."
            "<h4>Contributors</h4>"
            + ", ".join(contributors)
            + "<h4>Special Thanks  :</h4>"
            "<b>rp-</b> <i>for the pydcs framework</i><br/>"
            "<b>Grimes (mrSkortch)</b> & <b>Speed</b> <i>for the MIST framework</i><br/>"
            "<b>Ciribob </b> <i>for the JTACAutoLase.lua script</i><br/>"
            "<b>Walder </b> <i>for the Skynet-IADS script</i><br/>"
            "<b>Anubis Yinepu </b> <i>for the Hercules Cargo script</i><br/>"
            '<a href="https://www.flaticon.com/free-icons/bug" title="bug icons">Bug icons created by Freepik - Flaticon</a><br />'
            'Contains information from <a href="https://osmdata.openstreetmap.de/">OpenStreetMap © OpenStreetMap contributors</a>, which is made available here under the <a href="https://opendatacommons.org/licenses/odbl/1-0/">Open Database License (ODbL)</a>.<br />'
            '<a href="https://download.geofabrik.de/index.html/">OpenStreetMap Data Extracts from Geofabrik</a><br />'
            '<a href="https://www.earthdata.nasa.gov/">NASA EarthData</a><br />'
            + "<h4>Splash Screen  :</h4>"
            + "Artwork by Andriy Dankovych (CC BY-SA)"
            " <a href='https://www.facebook.com/AndriyDankovych'>"
            "[https://www.facebook.com/AndriyDankovych]</a>"
        )
        about = QMessageBox()
        about.setWindowTitle("About DCS Retribution")
        about.setIcon(QMessageBox.Icon.Information)
        about.setText(text)
        logging.info(about.textFormat())
        about.exec()

    def showLiberationDialog(self):
        self.subwindow = QLiberationPreferencesWindow()
        self.subwindow.show()

    def showSettingsDialog(self) -> None:
        self.dialog = QSettingsWindow(self.game)
        self.dialog.show()

    def showStatsDialog(self):
        self.dialog = QStatsWindow(self.game)
        self.dialog.show()

    def showNotesDialog(self):
        self.dialog = QNotesWindow(self.game)
        self.dialog.show()

    def import_templates(self):
        LAYOUTS.import_templates()

    def showLogsDialog(self):
        self.dialog = QLogsWindow(self)
        self.dialog.show()

    def onDebriefing(self, debrief: Debriefing):
        logging.info("On Debriefing")
        self.debriefing = QDebriefingWindow(debrief)
        self.debriefing.show()
        self.game_model.init_comms_registry()

    def open_dialog(self, dialog: QtDialog) -> None:
        """Opens a Qt screen for the web shell (WEB-00.3), on the Qt main thread."""
        handlers: dict[QtDialog, Callable[[], object]] = {
            QtDialog.PREFERENCES: self.showLiberationDialog,
            QtDialog.STATS: self.showStatsDialog,
            QtDialog.NOTES: self.showNotesDialog,
            QtDialog.LOGS: self.showLogsDialog,
            QtDialog.ABOUT: self.showAboutDialog,
            QtDialog.IMPORT_LAYOUTS: self.import_templates,
            QtDialog.PRETENSE_CAMPAIGN: self.newPretenseCampaign,
            QtDialog.AIR_WING: self.open_air_wing,
            QtDialog.TRANSFERS: self.open_transfers,
            QtDialog.AIR_TASKING_ORDER: lambda: self._show_panel("ato_window"),
            QtDialog.REPORTS: lambda: self._show_panel("reports_window"),
            QtDialog.FINANCES: self.open_finances,
            QtDialog.INTEL: self.open_intel,
            QtDialog.DEBRIEFING: self.show_last_debriefing,
        }
        # The game may have been unloaded between the request and this slot.
        if dialog.needs_game and self.game is None:
            return
        handlers[dialog]()

    def on_turn_passed(self, state: TurnState) -> None:
        """Refresh the Qt widgets once the web UI passed the turn."""
        GameUpdateSignal.get_instance().updateGame(self.game)
        GameUpdateSignal.get_instance().gameStateChanged(state)

    def open_air_wing(self) -> None:
        self.dialog = AirWingDialog(self.game_model, self)
        self.dialog.show()

    def open_transfers(self) -> None:
        self.dialog = PendingTransfersDialog(self.game_model)
        self.dialog.show()

    def open_finances(self) -> None:
        self.dialog = QFinancesMenu(self.game)
        self.dialog.show()

    def open_intel(self) -> None:
        self.dialog = IntelWindow(self.game)
        self.dialog.show()

    def on_results_accepted(self, debriefing: Debriefing) -> None:
        """The web UI accepted a mission result: show the Qt debriefing (until
        WEB-05.2) and refresh the Qt widgets, as QWaitingForMissionResultWindow does.
        """
        GameUpdateSignal.get_instance().sendDebriefing(debriefing)
        GameUpdateSignal.get_instance().updateGame(self.game)

    def _show_panel(self, name: str) -> None:
        # Without the web shell the panel is already part of the main window.
        window: QWidget | None = getattr(self, name, None)
        if window is None:
            return
        window.show()
        window.raise_()
        window.activateWindow()

    def show_last_debriefing(self) -> None:
        debriefing = getattr(self, "debriefing", None)
        if debriefing is None:
            QMessageBox.information(
                self, "Debriefing", "No mission result has been received yet."
            )
            return
        debriefing.show()
        debriefing.raise_()

    def open_link(self, link: ExternalLink) -> None:
        self.native_bridge.open_url(link.url)

    def open_edit_package_dialog(self, package: Package) -> None:
        model = self.game_model.ato_model.find_matching_package_model(package)
        if model is None:
            logging.warning("Cannot edit package %s: not in the player ATO", package)
            return
        Dialog.open_edit_package_dialog(model)

    def open_tgo_info_dialog(self, tgo: TheaterGroundObject) -> None:
        QGroundObjectMenu(self, tgo, tgo.control_point, self.game_model).show()

    def open_control_point_info_dialog(self, cp: ControlPoint) -> None:
        self._cp_dialog = QBaseMenu2(None, cp, self.game_model)
        self._cp_dialog.show()

    def on_select_flight(self, flight: Flight) -> None:
        self.ato_panel.select_flight_on_map(flight)

    def _qsettings(self) -> QSettings:
        return QSettings("DCS Retribution", "Qt UI")

    def _restore_window_geometry(self) -> None:
        settings = self._qsettings()
        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("windowState"))

    def _save_window_geometry(self) -> None:
        settings = self._qsettings()
        settings.setValue("geometry", self.saveGeometry())
        if not self.web_ui:
            # The web shell hides the toolbars: keep the Qt layout for the Qt UI.
            settings.setValue("windowState", self.saveState())

    def closeEvent(self, event: QCloseEvent) -> None:
        result = QMessageBox.question(
            self,
            "Quit Retribution?",
            "Would you like to save before quitting?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if result in [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No]:
            if result == QMessageBox.StandardButton.Yes and self.game is not None:
                self.saveGame()
            self._save_window_geometry()
            super().closeEvent(event)
            self.dialog = None
            self.debriefing = None
            for window in QApplication.topLevelWidgets():
                window.close()
        else:
            event.ignore()

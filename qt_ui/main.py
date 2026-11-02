import argparse
import logging
import ntpath
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QCheckBox, QSplashScreen
from dcs.liveries.liverycache import LiveryCache
from dcs.payloads import PayloadDirectories

from game import Game, VERSION, logging_config, persistency
from game.ato import FlightType
from game.commands import newgame
from game.data.weapons import Pylon, Weapon, WeaponGroup
from game.dcs.aircrafttype import AircraftType
from game.persistency import base_path
from game.profiling import logged_duration
from game.server import Server
from game.server.dependencies import UiOptions
from game.server.gamesession import start_session
from pydcs_extensions import load_mods
from game import liberation_install
from qt_ui.shell import ShellWindow

THIS_DIR = Path(__file__).parent


def inject_custom_payloads(user_path: Path) -> None:
    dev_payloads = THIS_DIR.parent / "resources/customized_payloads"
    # The packaged release rearranges the file locations, so the release has the
    # customized payloads in a different location.
    release_payloads = THIS_DIR / "resources/customized_payloads"
    if dev_payloads.exists():
        payloads = dev_payloads
    elif release_payloads.exists():
        payloads = release_payloads
    else:
        raise RuntimeError(
            f"Could not find customized payloads at {release_payloads} or "
            f"{dev_payloads}. Aircraft will have no payloads."
        )
    # We configure these as fallbacks so that the user's payloads override ours.
    PayloadDirectories.set_fallback(payloads)
    PayloadDirectories.set_preferred(user_path / "MissionEditor" / "UnitPayloads")


def warn_about_missing_install_directory(splash: QSplashScreen) -> None:
    if not liberation_install.ignore_empty_install_directory():
        ignore_checkbox = QCheckBox("Do not show again")
        ignore_checkbox.stateChanged.connect(set_ignore_empty_install_directory)
        message_box = QtWidgets.QMessageBox(parent=splash)
        message_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        message_box.setWindowTitle("No DCS installation directory.")
        message_box.setText(
            "The DCS Installation directory is not set correctly. "
            "This will prevent DCS Retribution from working properly, as the MissionScripting "
            "file will not be modified."
            "<br/><br/>To solve this problem, you can set the Installation directory "
            "within the preferences menu. You can also manually edit or replace the "
            "following file:"
            "<br/><br/><strong>&lt;dcs_installation_directory&gt;/Scripts/MissionScripting.lua</strong>"
            "<br/><br/>The easiest way to do it is to replace the original file with the file in dcs-retribution "
            "distribution (&lt;dcs_retribution_installation&gt;/resources/scripts/MissionScripting.lua)."
            "<br/><br/>You can find more information on how to manually change this file in the Retribution Wiki "
            "(Page: Dedicated Server Guide) on GitHub.</p>"
        )
        message_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
        message_box.setCheckBox(ignore_checkbox)
        message_box.exec()


def run_ui(game: Optional[Game], dev: bool) -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    # The few native dialogs left match the dark web UI.
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)

    # The web UI shows its own first start screen (WEB-07.2), which replaces the
    # MissionScripting file once the player accepts.
    first_start = liberation_install.init()

    logging.info("Using {} as 'Saved Game Folder'".format(persistency.base_path()))
    logging.info(
        "Using {} as 'DCS installation folder'".format(
            liberation_install.get_dcs_install_directory()
        )
    )

    inject_custom_payloads(persistency.base_path())

    # Splash screen setup
    pixmap = QPixmap("./resources/ui/splash_screen.png")
    splash = QSplashScreen(pixmap)
    splash.show()

    if not first_start:
        # Show warning if no DCS Installation directory was set
        if liberation_install.get_dcs_install_directory() == "":
            logging.warning(
                "DCS Installation directory is empty. MissionScripting file will not be replaced!"
            )
            warn_about_missing_install_directory(splash)
        # Replace DCS Mission scripting file to allow DCS Retribution to work
        try:
            liberation_install.replace_mission_scripting_file()
        except Exception as e:
            logging.error(e)
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.setWindowTitle("Wrong DCS installation directory.")
            error_dialog.showMessage(
                "Unable to modify Mission Scripting file. Possible issues with rights. "
                "Try running as admin, or please perform the modification of the MissionScripting file manually."
            )
            error_dialog.exec()

    # Start window
    window = ShellWindow(game, dev)
    window.showMaximized()
    splash.finish(window)
    qt_execution_code = app.exec()

    # Restore Mission Scripting file
    logging.info("QT App terminated with status code : " + str(qt_execution_code))
    logging.info("Attempt to restore original mission scripting file")
    liberation_install.restore_original_mission_scripting()
    logging.info("QT process exited with code : " + str(qt_execution_code))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")

    def path_arg(arg: str) -> Path:
        path = Path(arg)
        if not path.exists():
            raise argparse.ArgumentTypeError("path does not exist")
        return path

    parser.add_argument(
        "--warn-missing-weapon-data",
        action="store_true",
        help="Emits a warning for weapons without date or fallback information.",
    )

    parser.add_argument("--dev", action="store_true", help="Enable development mode.")

    speed_controls_group = parser.add_argument_group()
    speed_controls_group.add_argument(
        "--show-sim-speed-controls",
        action="store_true",
        help="Shows the sim speed controls in the top panel.",
    )
    speed_controls_group.add_argument(
        "--no-show-sim-speed-controls",
        dest="show_sim_speed_controls",
        action="store_false",
        help="Hides the sim speed controls in the top panel (default).",
    )

    parser.add_argument("--new-map", help="Deprecated. Does nothing.")
    parser.add_argument("--old-map", help="Deprecated. Does nothing.")

    new_game = subparsers.add_parser("new-game")

    new_game.add_argument(
        "campaign", type=path_arg, help="Path to the campaign to start."
    )

    new_game.add_argument(
        "--blue", default="USA 2005", help="Name of the blue faction."
    )

    new_game.add_argument(
        "--red", default="Russia 1990", help="Name of the red faction."
    )

    new_game.add_argument(
        "--supercarrier", action="store_true", help="Use the supercarrier module."
    )

    new_game.add_argument(
        "--auto-procurement", action="store_true", help="Automate bluefor procurement."
    )

    new_game.add_argument(
        "--use-new-squadron-rules",
        action="store_true",
        help=(
            "Limit the number of aircraft per squadron and begin the campaign with "
            "them at full strength."
        ),
    )

    new_game.add_argument(
        "--inverted", action="store_true", help="Invert the campaign."
    )

    new_game.add_argument(
        "--date",
        type=datetime.fromisoformat,
        default=datetime.today(),
        help="Start date of the campaign.",
    )

    new_game.add_argument(
        "--restrict-weapons-by-date",
        action="store_true",
        help="Enable campaign date restricted weapons.",
    )

    new_game.add_argument("--cheats", action="store_true", help="Enable cheats.")

    new_game.add_argument(
        "--advanced-iads", action="store_true", help="Enable advanced IADS."
    )

    new_game.add_argument(
        "--squadrons-start-full",
        action="store_true",
        help="Fill every squadron to its aircraft limit on turn 0.",
    )

    new_game.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Same parameters and seed, same campaign.",
    )

    lint_weapons = subparsers.add_parser("lint-weapons")
    lint_weapons.add_argument("aircraft", help="Name of the aircraft variant to lint.")

    subparsers.add_parser("dump-task-priorities")

    return parser.parse_args()


def create_game(args: argparse.Namespace) -> Game:
    """The CLI `new-game`, on the same code as both wizards."""
    first_start = liberation_install.init()
    if first_start:
        sys.exit(
            "Cannot generate campaign without configuring DCS Retribution. Start the UI "
            "for the first run configuration."
        )

    # This needs to run before the pydcs payload cache is created, which happens
    # extremely early. It's not a problem that we inject these paths twice because we'll
    # get the same answers each time.
    #
    # Without this, it is not possible to use next turn (or anything that needs to check
    # for loadouts) without saving the generated campaign and reloading it the normal
    # way.
    inject_custom_payloads(persistency.base_path())
    return newgame.create_game(
        newgame.cli_parameters(
            args.campaign,
            args.blue,
            args.red,
            args.supercarrier,
            args.auto_procurement,
            args.inverted,
            args.cheats,
            args.date,
            args.restrict_weapons_by_date,
            args.advanced_iads,
            args.use_new_squadron_rules,
            args.squadrons_start_full,
            args.seed,
        )
    )


def set_ignore_empty_install_directory(value: bool) -> None:
    liberation_install.set_ignore_empty_install_directory(value)
    liberation_install.save_config()


def lint_all_weapon_data() -> None:
    for weapon in WeaponGroup.named("Unknown").weapons:
        logging.warning(f"No weapon data for {weapon}: {weapon.clsid}")


def lint_weapon_data_for_aircraft(aircraft: AircraftType) -> None:
    all_weapons: set[Weapon] = set()
    for pylon in Pylon.iter_pylons(aircraft):
        all_weapons |= pylon.allowed

    for weapon in all_weapons:
        if weapon.weapon_group.name == "Unknown":
            logging.warning(f'{weapon.clsid} "{weapon.name}" has no weapon data')


def fix_pycharm_debugger_if_needed() -> None:
    """Applies workaround for a pycharm debugger bug.

    https://youtrack.jetbrains.com/issue/PY-53232/Debugger-doesnt-work-when-pyproj-is-imported
    """
    # sys.gettrace() will return something whenever *some* debugger is being used. The
    # pdb module will be loaded if that debugger is the built-in python debugger.
    if sys.gettrace() is not None and "pdb" not in sys.modules:
        logging.debug(
            "Applying workaround for https://youtrack.jetbrains.com/issue/PY-53232/Debugger-doesnt-work-when-pyproj-is-imported"
        )
        ntpath.sep = "\\"


def dump_task_priorities() -> None:
    first_start = liberation_install.init()
    if first_start:
        sys.exit(
            "Cannot dump task priorities without configuring DCS Liberation. Start the"
            "UI for the first run configuration."
        )

    data: dict[str, dict[str, int]] = {}
    for task in FlightType:
        data[task.value] = {
            a.name: a.task_priority(task)
            for a in AircraftType.priority_list_for_task(task)
        }

    debug_path = base_path() / "Debug" / "priorities.yaml"
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    with debug_path.open("w", encoding="utf-8") as output:
        yaml.dump(data, output, sort_keys=False, allow_unicode=True)


_single_instance_lock = None  # held lock-file handle; the OS frees it on exit


def _acquire_single_instance_lock() -> bool:
    """Become the only running instance; return False if another one holds the lock.

    Uses an OS advisory lock on a temp file that the OS releases automatically when
    this process exits, even on a crash. Without it, relaunching the executable
    starts a second process that cannot bind the already-used web-server port, hangs
    without ever showing a window, and is left orphaned when the first window closes.
    """
    global _single_instance_lock
    lock_path = Path(tempfile.gettempdir()) / "dcs_retribution.lock"
    try:
        handle = open(lock_path, "w")
    except OSError:
        return True  # never block startup on a lock-file problem
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return False
    _single_instance_lock = handle  # keep open for the lifetime of the process
    return True


def main():
    logging_config.init_logging(VERSION)

    if not _acquire_single_instance_lock():
        logging.warning(
            "DCS Retribution is already running; exiting this duplicate instance."
        )
        sys.exit(0)

    logging.debug("Python version %s", sys.version)

    if not str(Path(__file__)).isascii():
        logging.warning(
            "Installation path contains non-ASCII characters. This is known to cause problems."
        )

    game: Optional[Game] = None

    args = parse_args()

    # TODO: Flesh out data and then make unconditional.
    if args.warn_missing_weapon_data:
        lint_all_weapon_data()

    load_mods()

    LiveryCache.cache()

    if args.subcommand == "new-game":
        with logged_duration("New game creation"):
            game = create_game(args)
    if args.subcommand == "lint-weapons":
        lint_weapon_data_for_aircraft(AircraftType.named(args.aircraft))
        return
    if args.subcommand == "dump-task-priorities":
        dump_task_priorities()
        return

    liberation_install.init()
    start_session()
    UiOptions.set(show_sim_speed_controls=args.show_sim_speed_controls)
    with Server(liberation_install.server_port()).run_in_thread():
        run_ui(game, args.dev)


if __name__ == "__main__":
    main()

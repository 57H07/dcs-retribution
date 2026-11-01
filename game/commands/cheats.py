"""The cheats of the base menu (WEB-02.3), each behind its setting.

From the Qt `QBaseMenu2` (base capture, runway state) and `QGroundForcesStrategy`
(front line position).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .errors import CommandError
from .frontline import require_front_line

if TYPE_CHECKING:
    from game import Game
    from game.game import TurnState
    from game.sim import GameUpdateEvents
    from game.theater import ControlPoint

#: Base strength moved by one click, as in the Qt menu.
FRONT_LINE_CHEAT_STRENGTH = 0.2


def cheat_move_front_line(
    game: Game,
    cp: ControlPoint,
    enemy: ControlPoint,
    advance: bool,
    events: GameUpdateEvents,
) -> None:
    """Moves a front line, then replans: missions it affects are no longer valid.

    Raises:
        CommandError: the cheat is off, or not a front line of this player base.
    """
    if not game.settings.enable_frontline_cheats:
        raise CommandError("The front line cheat is not enabled in the settings.")
    require_front_line(cp, enemy)
    amount = FRONT_LINE_CHEAT_STRENGTH if advance else -FRONT_LINE_CHEAT_STRENGTH
    cp.base.affect_strength(amount)
    enemy.base.affect_strength(-amount)
    front_line = cp.front_line_with(enemy)
    front_line.update_position()
    events.update_front_line(front_line)
    game.initialize_turn(events)


def cheat_runway_label(game: Game, cp: ControlPoint) -> Optional[str]:
    """The action of the runway cheat for this base, None when it is not offered."""
    if not cp.runway_is_destroyable or not game.settings.enable_runway_state_cheat:
        return None
    return "Repair runway" if cp.runway_can_be_repaired else "Destroy runway"


def cheat_runway_state(game: Game, cp: ControlPoint, events: GameUpdateEvents) -> None:
    """Repairs a damaged runway at once, or destroys a working one.

    Raises:
        CommandError: the cheat is off, or this base has no runway to destroy.
    """
    if cheat_runway_label(game, cp) is None:
        raise CommandError("The runway cheat is not available for this base.")
    if cp.runway_can_be_repaired:
        cp.runway_status.repair()
    else:
        cp.runway_status.damage()
    events.update_control_point(cp)


def cheat_capture_label(game: Game, cp: ControlPoint) -> Optional[str]:
    """The action of the capture cheat for this base, None when it is off."""
    if not game.settings.enable_base_capture_cheat:
        return None
    return "Sink/Resurrect" if cp.is_fleet else "Capture"


def cheat_capture(game: Game, cp: ControlPoint, events: GameUpdateEvents) -> TurnState:
    """Flips a base (or sinks and resurrects a fleet), then replans the whole turn.

    Returns:
        The state of the campaign: it may be over.

    Raises:
        CommandError: the cheat is off.
    """
    from game.sim.missionresultsprocessor import MissionResultsProcessor

    if cheat_capture_label(game, cp) is None:
        raise CommandError("The base capture cheat is not enabled in the settings.")
    if cp.is_fleet:
        for go in cp.ground_objects:
            if go.is_naval_control_point:
                if go.alive_unit_count > 0:
                    for unit in go.units:
                        unit.kill(events)
                else:
                    for unit in go.units:
                        unit.revive(events)
    else:
        cp.capture(game, events, for_player=cp.captured.opponent)
        MissionResultsProcessor(game).redeploy_units(cp)
    # The ATO needs to be reset: missions planned against the flipped base (or killed
    # carrier) are no longer valid.
    game.initialize_turn(events)
    return game.check_win_loss()

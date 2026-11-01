"""Front line stances of a base (WEB-02.3), from the Qt `QGroundForcesStrategy`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.ground_forces.combat_stance import CombatStance
from .errors import CommandError

if TYPE_CHECKING:
    from game.sim import GameUpdateEvents
    from game.theater import ControlPoint


def enemies_at_front(cp: ControlPoint) -> list[ControlPoint]:
    """The enemy bases this player base has a front line with."""
    if not cp.captured.is_blue:
        return []
    return [enemy for enemy in cp.connected_points if enemy.captured.is_red]


def front_line_stance(cp: ControlPoint, enemy: ControlPoint) -> CombatStance:
    return cp.stances.get(enemy.id, CombatStance.DEFENSIVE)


def require_front_line(cp: ControlPoint, enemy: ControlPoint) -> None:
    """
    Raises:
        CommandError: not a front line of this player base.
    """
    if enemy not in enemies_at_front(cp):
        raise CommandError(f"{cp.name} has no front line with {enemy.name}.")


def set_front_line_stance(
    cp: ControlPoint, enemy: ControlPoint, stance: str, events: GameUpdateEvents
) -> None:
    """Sets what the ground forces of this base do on a front line.

    Args:
        stance: name of a `CombatStance`.

    Raises:
        CommandError: not a front line of this player base, or an unknown stance.
    """
    require_front_line(cp, enemy)
    try:
        cp.stances[enemy.id] = CombatStance[stance]
    except KeyError:
        raise CommandError(f"{stance} is not a front line stance.")
    events.update_control_point(cp)

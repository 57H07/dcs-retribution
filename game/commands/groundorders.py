"""Ground unit orders at a base (WEB-02.3).

The rules of the Qt `QArmorRecruitmentMenu` and `GroundUnitPurchaseAdapter`, shared with
the web base screen. Ground units are paid when ordered and delivered next turn:

- buying needs the budget and a friendly base that can recruit (any on turn 0, then
  one with a factory), and the base must be able to deploy ground units;
- removing a unit cancels a pending order (refunded); ground units are never sold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Optional

from game.purchaseadapter import GroundUnitPurchaseAdapter
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.dcs.groundunittype import GroundUnitType
    from game.sim import GameUpdateEvents
    from game.theater import ControlPoint


@dataclass(frozen=True)
class GroundUnitOrder:
    unit_type: GroundUnitType
    #: Units to buy; negative to cancel pending orders.
    quantity: int


def ground_unit_types(cp: ControlPoint) -> list[GroundUnitType]:
    """What can be ordered at this base: the ground units of its faction."""
    return sorted(set(cp.coalition.faction.ground_units), key=lambda u: u.display_name)


def find_ground_unit_type(cp: ControlPoint, unit_id: str) -> GroundUnitType:
    """The orderable unit with this `variant_id`.

    Raises:
        CommandError: the faction of the base has no such unit.
    """
    for unit_type in ground_unit_types(cp):
        if unit_type.variant_id == unit_id:
            return unit_type
    raise CommandError(f"{unit_id} is not a ground unit of your faction.")


def recruitment_refusal(game: Game, cp: ControlPoint) -> Optional[str]:
    """Why no ground unit can reach this base, or None."""
    if not cp.can_deploy_ground_units:
        return f"{cp.name} cannot deploy ground units."
    if not cp.has_ground_unit_source(game):
        return "None of your bases can recruit ground units: you need a factory."
    return None


def ground_buy_refusal(
    game: Game, cp: ControlPoint, unit_type: GroundUnitType
) -> Optional[str]:
    """Why one more unit of this type cannot be ordered here, or None."""
    budget = cp.coalition.budget
    if budget < unit_type.price:
        return (
            f"A {unit_type.display_name} costs ${unit_type.price:g}M but you have only "
            f"${budget:g}M available."
        )
    return recruitment_refusal(game, cp)


def max_ground_units_to_add(
    game: Game, cp: ControlPoint, unit_type: GroundUnitType
) -> int:
    """How many units of this type could be ordered here alone, right now."""
    if recruitment_refusal(game, cp) is not None:
        return 0
    if unit_type.price <= 0:
        # Nothing limits a free unit but the size of the order.
        return 999
    return max(0, int(cp.coalition.budget // unit_type.price))


def _require_player_base(cp: ControlPoint) -> None:
    if not cp.captured.is_blue:
        raise CommandError(
            f"{cp.name} is not your base: you cannot order ground units."
        )


def _apply_one(
    game: Game, adapter: GroundUnitPurchaseAdapter, unit_type: GroundUnitType, step: int
) -> None:
    cp = adapter.control_point
    if step > 0:
        refusal = ground_buy_refusal(game, cp, unit_type)
        if refusal is not None:
            raise CommandError(refusal)
        adapter.buy(unit_type, 1)
    else:
        if not adapter.has_pending_orders(unit_type):
            raise CommandError(
                f"No {unit_type.display_name} on order at {cp.name}: ground units "
                "cannot be sold."
            )
        adapter.sell(unit_type, 1)


def _publish(cp: ControlPoint, events: GameUpdateEvents) -> None:
    events.update_control_point(cp)
    events.update_budget()


def order_ground_units(
    game: Game,
    cp: ControlPoint,
    orders: Iterable[GroundUnitOrder],
    events: GameUpdateEvents,
) -> None:
    """Applies a whole order, or nothing of it.

    Cancellations go first: they free the money the purchases of the same order may
    need.

    Raises:
        CommandError: not a player base, empty order, or a line refused by the budget,
            the lack of a factory, or the lack of a pending order to cancel.
    """
    _require_player_base(cp)
    lines = sorted(
        (order for order in orders if order.quantity != 0), key=lambda o: o.quantity
    )
    if not lines:
        raise CommandError("The order is empty.")
    budget = cp.coalition.budget
    pending = dict(cp.ground_unit_orders.units)
    adapter = GroundUnitPurchaseAdapter(cp, cp.coalition, game)
    try:
        for line in lines:
            step = 1 if line.quantity > 0 else -1
            for _ in range(abs(line.quantity)):
                _apply_one(game, adapter, line.unit_type, step)
    except CommandError:
        cp.coalition.budget = budget
        cp.ground_unit_orders.units.clear()
        cp.ground_unit_orders.units.update(pending)
        raise
    _publish(cp, events)


def change_ground_unit_order(
    game: Game,
    cp: ControlPoint,
    unit_type: GroundUnitType,
    quantity: int,
    events: GameUpdateEvents,
) -> None:
    """One unit at a time, keeping what was done before a refusal.

    The Shift and Ctrl clicks of the Qt menus buy "up to" 10 or 5 units.

    Raises:
        CommandError: why the next unit was refused.
    """
    _require_player_base(cp)
    step = 1 if quantity > 0 else -1
    adapter = GroundUnitPurchaseAdapter(cp, cp.coalition, game)
    try:
        for _ in range(abs(quantity)):
            _apply_one(game, adapter, unit_type, step)
    finally:
        _publish(cp, events)

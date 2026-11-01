"""Aircraft orders and new squadrons at a base (WEB-02.2).

The rules of the Qt base menu (`QAircraftRecruitmentMenu`, `SquadronDialog`), shared
with the web base screen. An aircraft is paid when ordered and delivered next turn:

- buying needs the budget, parking (`ControlPoint.unclaimed_parking`, which counts the
  parking pools helicopters and fixed wing aircraft share) and room in the squadron
  (only with the `enable_squadron_aircraft_limits` setting);
- removing an aircraft cancels a pending order first (refunded), then sells an
  untasked aircraft of the squadron.

New squadrons are the aircraft of the faction that the base can operate, as in the
"Add new Squadron" popup of `AirWingConfigurationDialog`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Optional

from game.dcs.aircrafttype import AircraftType
from game.purchaseadapter import PurchaseAdapter
from game.theater.controlpoint import ParkingType
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.ato.flighttype import FlightType
    from game.sim import GameUpdateEvents
    from game.squadrons import Squadron
    from game.squadrons.squadrondef import SquadronDef
    from game.theater import ControlPoint


def _parking_room(cp: ControlPoint, squadron: Squadron) -> int:
    return cp.unclaimed_parking(ParkingType().from_squadron(squadron))


def buy_refusal(cp: ControlPoint, squadron: Squadron) -> Optional[str]:
    """Why one more aircraft cannot be ordered for this squadron, or None."""
    aircraft = squadron.aircraft
    budget = cp.coalition.budget
    if budget < aircraft.price:
        return (
            f"A {aircraft.display_name} costs ${aircraft.price:g}M but you have only "
            f"${budget:g}M available."
        )
    if _parking_room(cp, squadron) <= 0:
        return f"No parking left for a {aircraft.display_name} at {cp.name}."
    if not squadron.has_aircraft_capacity_for(1):
        return f"{squadron.name} is full: {squadron.max_size} aircraft at most."
    return None


def removal_refusal(squadron: Squadron) -> Optional[str]:
    """Why no aircraft can be cancelled or sold from this squadron, or None."""
    if squadron.pending_deliveries > 0 or squadron.untasked_aircraft > 0:
        return None
    return (
        f"{squadron.name} has no aircraft to sell: none is owned, or they are all "
        "assigned to a mission."
    )


class AircraftPurchaseAdapter(PurchaseAdapter["Squadron"]):
    def __init__(self, control_point: ControlPoint) -> None:
        super().__init__(control_point.coalition)
        self.control_point = control_point

    def pending_delivery_quantity(self, item: Squadron) -> int:
        return item.pending_deliveries

    def current_quantity_of(self, item: Squadron) -> int:
        return item.owned_aircraft

    def can_buy(self, item: Squadron) -> bool:
        return buy_refusal(self.control_point, item) is None

    def can_sell(self, item: Squadron) -> bool:
        return item.untasked_aircraft > 0

    def do_purchase(self, item: Squadron) -> None:
        item.pending_deliveries += 1

    def do_cancel_purchase(self, item: Squadron) -> None:
        item.pending_deliveries -= 1

    def do_sale(self, item: Squadron) -> None:
        item.untasked_aircraft -= 1
        item.pending_deliveries -= 1

    def do_cancel_sale(self, item: Squadron) -> None:
        item.untasked_aircraft += 1
        item.pending_deliveries += 1

    def price_of(self, item: Squadron) -> int:
        return item.aircraft.price

    def name_of(self, item: Squadron, multiline: bool = False) -> str:
        if multiline:
            separator = "<br />"
        else:
            separator = " "
        return separator.join([item.aircraft.display_name, str(item)])

    def unit_type_of(self, item: Squadron) -> AircraftType:
        return item.aircraft


@dataclass(frozen=True)
class AircraftOrder:
    squadron: Squadron
    #: Aircraft to buy; negative to cancel orders, then sell.
    quantity: int


def max_aircraft_to_add(cp: ControlPoint, squadron: Squadron) -> int:
    """How many aircraft could be ordered for this squadron alone, right now."""
    limits = [_parking_room(cp, squadron)]
    price = squadron.aircraft.price
    if price > 0:
        limits.append(int(cp.coalition.budget // price))
    if squadron.settings.enable_squadron_aircraft_limits:
        limits.append(
            squadron.max_size - squadron.owned_aircraft - squadron.pending_deliveries
        )
    return max(0, min(limits))


def max_aircraft_to_remove(squadron: Squadron) -> int:
    """How many aircraft can be cancelled or sold from this squadron, right now."""
    return max(0, squadron.pending_deliveries) + max(0, squadron.untasked_aircraft)


def _require_player_base(cp: ControlPoint) -> None:
    if not cp.captured.is_blue:
        raise CommandError(f"{cp.name} is not your base: you cannot order aircraft.")


def _apply(adapter: AircraftPurchaseAdapter, order: AircraftOrder) -> None:
    squadron = order.squadron
    if squadron.location != adapter.control_point:
        raise CommandError(
            f"{squadron.name} is not stationed at {adapter.control_point.name}."
        )
    for _ in range(abs(order.quantity)):
        if order.quantity > 0:
            refusal = buy_refusal(adapter.control_point, squadron)
        else:
            refusal = removal_refusal(squadron)
        if refusal is not None:
            raise CommandError(refusal)
        if order.quantity > 0:
            adapter.buy(squadron, 1)
        else:
            adapter.sell(squadron, 1)


def _publish(cp: ControlPoint, events: GameUpdateEvents) -> None:
    events.update_control_point(cp)
    events.update_budget()


def order_aircraft(
    cp: ControlPoint, orders: Iterable[AircraftOrder], events: GameUpdateEvents
) -> None:
    """Applies a whole order, or nothing of it.

    Cancellations and sales go first: they free the money and the parking the
    purchases of the same order may need.

    Raises:
        CommandError: not a player base, empty order, a squadron stationed elsewhere,
            or a line refused by the budget, parking or squadron limits.
    """
    _require_player_base(cp)
    lines = sorted(
        (order for order in orders if order.quantity != 0), key=lambda o: o.quantity
    )
    if not lines:
        raise CommandError("The order is empty.")
    budget = cp.coalition.budget
    before = [
        (o.squadron, o.squadron.pending_deliveries, o.squadron.untasked_aircraft)
        for o in lines
    ]
    adapter = AircraftPurchaseAdapter(cp)
    try:
        for line in lines:
            _apply(adapter, line)
    except CommandError:
        cp.coalition.budget = budget
        for squadron, pending, untasked in before:
            squadron.pending_deliveries = pending
            squadron.untasked_aircraft = untasked
        raise
    _publish(cp, events)


def cancel_aircraft_orders(
    cp: ControlPoint, squadron: Squadron, events: GameUpdateEvents
) -> None:
    """Brings the pending deliveries of a squadron back to zero.

    Pending orders are refunded; a pending sale is bought back, like any purchase.

    Raises:
        CommandError: not a player base, nothing pending, or the sale cannot be bought
            back.
    """
    _require_player_base(cp)
    if squadron.pending_deliveries == 0:
        raise CommandError(f"{squadron.name} has no pending order.")
    order_aircraft(cp, [AircraftOrder(squadron, -squadron.pending_deliveries)], events)


def change_aircraft_order(
    cp: ControlPoint, squadron: Squadron, quantity: int, events: GameUpdateEvents
) -> None:
    """One aircraft at a time, keeping what was done before a refusal.

    The Shift and Ctrl clicks of the Qt menus buy "up to" 10 or 5 aircraft.

    Raises:
        CommandError: why the next aircraft was refused.
    """
    _require_player_base(cp)
    step = 1 if quantity > 0 else -1
    try:
        for _ in range(abs(quantity)):
            _apply(AircraftPurchaseAdapter(cp), AircraftOrder(squadron, step))
    finally:
        _publish(cp, events)


@dataclass(frozen=True)
class SquadronChoice:
    """An aircraft that can get a new squadron at a base."""

    aircraft: AircraftType
    tasks: list[FlightType]
    #: Unclaimed squadron presets that can operate from the base.
    presets: list[SquadronDef]


def squadron_choices(cp: ControlPoint) -> list[SquadronChoice]:
    """What `create_squadron` accepts at this base; nothing for another base."""
    if not cp.captured.is_blue:
        return []
    coalition = cp.coalition
    aircraft_types = [
        aircraft
        for aircraft in coalition.faction.all_aircrafts
        if isinstance(aircraft, AircraftType) and cp.can_operate(aircraft)
    ]
    defs = coalition.air_wing.squadron_defs
    return [
        SquadronChoice(
            aircraft,
            sorted(aircraft.iter_task_capabilities(), key=lambda task: task.value),
            sorted(
                (
                    squadron_def
                    for squadron_def in defs.get(aircraft, [])
                    if not squadron_def.claimed and squadron_def.operates_from(cp)
                ),
                key=lambda squadron_def: squadron_def.name,
            ),
        )
        for aircraft in sorted(aircraft_types, key=lambda a: a.display_name)
    ]


def create_squadron(
    game: Game,
    cp: ControlPoint,
    aircraft_id: str,
    primary_task: str,
    preset: Optional[str],
    events: GameUpdateEvents,
) -> Squadron:
    """Adds an empty squadron to the base, with its pilots; aircraft are ordered next.

    Args:
        aircraft_id: `AircraftType.variant_id` of a `squadron_choices` entry.
        primary_task: `FlightType` value among the tasks of that entry.
        preset: name of a preset of that entry; None generates a squadron.

    Raises:
        CommandError: not a player base, or a choice this base does not offer.
    """
    from game.campaignloader.campaignairwingconfig import DEFAULT_SQUADRON_SIZE
    from game.squadrons import Squadron

    if not cp.captured.is_blue:
        raise CommandError(f"{cp.name} is not your base: you cannot add a squadron.")
    choice = next(
        (c for c in squadron_choices(cp) if c.aircraft.variant_id == aircraft_id),
        None,
    )
    if choice is None:
        raise CommandError(
            f"{aircraft_id} is not in your faction, or cannot operate from {cp.name}."
        )
    task = next((t for t in choice.tasks if t.value == primary_task), None)
    if task is None:
        raise CommandError(
            f"The {choice.aircraft.display_name} cannot fly {primary_task}."
        )
    air_wing = cp.coalition.air_wing
    if preset is None:
        squadron_def = air_wing.squadron_def_generator.generate_for_aircraft(
            choice.aircraft
        )
    else:
        found = next((d for d in choice.presets if d.name == preset), None)
        if found is None:
            raise CommandError(f"The squadron {preset} is not available at {cp.name}.")
        squadron_def = found
    squadron = Squadron.create_from(
        squadron_def, task, DEFAULT_SQUADRON_SIZE, cp, cp.coalition, game
    )
    air_wing.add_squadron(squadron)
    # The turn 0 setup: its full pilot roster now, and no aircraft.
    squadron.populate_for_turn_0(squadrons_start_full=False)
    events.update_control_point(cp)
    return squadron

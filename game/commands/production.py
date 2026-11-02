"""Everything in progress for the player, and what waits for a decision (issue #182).

A read model over what the base, squadron, site and transfer screens show one by one.
Each action runs the command those screens use, so its rules stay in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterator, Literal, Optional

from game.theater.player import Player
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    NavalGroundObject,
)
from .aircraftorders import cancel_aircraft_orders
from .errors import CommandError
from .groundobjects import GroundUnitStatus, ground_object_units, repair_ground_unit
from .groundorders import GroundUnitOrder, order_ground_units
from .repairs import Repair, base_repairs, order_repair, squadron_repair_id
from .transfers import cancel_transfer

if TYPE_CHECKING:
    from game import Game
    from game.sim import GameUpdateEvents
    from game.squadrons import Squadron
    from game.theater import ControlPoint, TheaterGroundObject
    from game.transfers import TransferOrder

ProductionGroup = Literal[
    "aircraft-orders",
    "ground-orders",
    "maintenance",
    "repairs",
    "transfers",
    "damage",
    "ships",
]

_GROUP_ORDER: list[ProductionGroup] = [
    "aircraft-orders",
    "ground-orders",
    "maintenance",
    "repairs",
    "transfers",
    "damage",
    "ships",
]


@dataclass(frozen=True)
class ProductionAction:
    label: str
    #: Millions to pay; negative for a refund.
    cost: float
    run: Callable[[GameUpdateEvents], object]
    #: The change reaches the running simulation (see the transfers routes).
    reloads_sim: bool = False


@dataclass(frozen=True)
class ProductionItem:
    #: Stable while the item exists and safe in a URL path, passed back to
    #: `run_production_action`.
    id: str
    group: ProductionGroup
    label: str
    detail: str
    #: Turns until it ends; None when no delay is known (transfers, waiting items).
    turns: Optional[int]
    base: Optional[ControlPoint]
    tgo: Optional[TheaterGroundObject]
    action: Optional[ProductionAction]


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _aircraft_orders(game: Game) -> Iterator[ProductionItem]:
    for squadron in game.blue.air_wing.iter_squadrons():
        pending = squadron.pending_deliveries
        if pending == 0:
            continue
        base = squadron.location

        def cancel(events: GameUpdateEvents, s: Squadron = squadron) -> None:
            cancel_aircraft_orders(s.location, s, events)

        name = squadron.aircraft.display_name
        yield ProductionItem(
            f"aircraft-order:{squadron.id}",
            "aircraft-orders",
            f"{pending} × {name}" if pending > 0 else f"{-pending} × {name} sold",
            f"{squadron.name} · {base.name}",
            1,
            base,
            None,
            ProductionAction(
                "Cancel" if pending > 0 else "Buy back",
                -pending * squadron.aircraft.price,
                cancel,
            ),
        )


def _ground_orders(game: Game) -> Iterator[ProductionItem]:
    for base in game.theater.control_points_for(Player.BLUE):
        for unit_type, count in base.ground_unit_orders.units.items():
            if count <= 0:
                continue

            def cancel(
                events: GameUpdateEvents,
                cp: ControlPoint = base,
                order: GroundUnitOrder = GroundUnitOrder(unit_type, -count),
            ) -> None:
                order_ground_units(game, cp, [order], events)

            yield ProductionItem(
                f"ground-order:{base.id}:{unit_type.variant_id.encode().hex()}",
                "ground-orders",
                f"{count} × {unit_type.display_name}",
                base.name,
                1,
                base,
                None,
                ProductionAction("Cancel", -count * unit_type.price, cancel),
            )


def _order_repair_action(
    game: Game, base: ControlPoint, repair: Repair, label: str
) -> ProductionAction:
    return ProductionAction(
        label,
        repair.cost,
        lambda events: order_repair(game, base, repair.id, events),
    )


def _maintenance(game: Game, base: ControlPoint) -> Iterator[ProductionItem]:
    repairs = {r.id: r for r in base_repairs(game, base) if r.kind == "aircraft"}
    for squadron in base.squadrons:
        count = squadron.aircraft_in_maintenance
        if not count:
            continue
        repair = repairs[squadron_repair_id(squadron)]
        yield ProductionItem(
            f"maintenance:{squadron.id}",
            "maintenance",
            f"{count} × {squadron.aircraft.display_name}",
            f"{squadron.name} · {base.name}",
            max((turns for _, turns in squadron.maintenance_summary), default=1),
            base,
            None,
            (
                None
                if repair.in_progress
                else _order_repair_action(game, base, repair, "Expedite")
            ),
        )


def _site_of(base: ControlPoint, repair: Repair) -> Optional[TheaterGroundObject]:
    return next(
        (t for t in base.ground_objects if repair.id.startswith(f"tgo:{t.id}")), None
    )


def _base_repairs(game: Game, base: ControlPoint) -> Iterator[ProductionItem]:
    for repair in base_repairs(game, base):
        if repair.kind == "aircraft":
            continue
        if repair.in_progress:
            yield ProductionItem(
                f"repair:{base.id}:{repair.id}",
                "repairs",
                repair.label,
                base.name,
                repair.turns,
                base,
                _site_of(base, repair),
                None,
            )
        else:
            yield ProductionItem(
                f"repair:{base.id}:{repair.id}",
                "damage",
                repair.label,
                f"{base.name} · {_plural(repair.turns, 'turn')} once started",
                None,
                base,
                _site_of(base, repair),
                _order_repair_action(game, base, repair, "Repair"),
            )


def _repair_units(
    game: Game, tgo: TheaterGroundObject, units: list[GroundUnitStatus], label: str
) -> ProductionAction:
    unit_ids = [status.unit.id for status in units]

    def run(events: GameUpdateEvents) -> None:
        for unit_id in unit_ids:
            repair_ground_unit(game, tgo, unit_id, events)

    return ProductionAction(
        label, sum(status.repair_cost or 0 for status in units), run
    )


def _site_repairs(game: Game, base: ControlPoint) -> Iterator[ProductionItem]:
    for tgo in base.ground_objects:
        if isinstance(tgo, BuildingGroundObject):
            continue
        statuses = ground_object_units(game, tgo)
        running = [s for s in statuses if s.state in ("repairing", "inoperative")]
        for turns in sorted({s.turns_remaining for s in running}):
            units = [s for s in running if s.turns_remaining == turns]
            payable = [s for s in units if s.repair_cost is not None]
            yield ProductionItem(
                f"site-repair:{tgo.id}:{turns}",
                "repairs",
                f"{tgo.name}: {_plural(len(units), 'unit')}",
                base.name,
                turns,
                base,
                tgo,
                _repair_units(game, tgo, payable, "Repair now") if payable else None,
            )
        waiting = [
            s for s in statuses if s.state == "destroyed" and s.repair_cost is not None
        ]
        if waiting:
            yield ProductionItem(
                f"site-damage:{tgo.id}",
                "ships" if isinstance(tgo, NavalGroundObject) else "damage",
                f"{tgo.name}: {_plural(len(waiting), 'unit')} destroyed",
                base.name,
                None,
                base,
                tgo,
                _repair_units(game, tgo, waiting, "Repair"),
            )


def _transfer_item(game: Game, transfer: TransferOrder) -> ProductionItem:
    def cancel(events: GameUpdateEvents) -> None:
        cancel_transfer(game, transfer)
        events.update_control_point(transfer.origin)

    return ProductionItem(
        f"transfer:{transfer.id}",
        "transfers",
        _plural(transfer.size, "ground unit"),
        f"{transfer.origin.name} → {transfer.destination.name} · "
        f"{transfer.description}",
        None,
        transfer.origin,
        None,
        ProductionAction("Cancel", 0, cancel, reloads_sim=True),
    )


def production_items(game: Game) -> list[ProductionItem]:
    """The player's items by group, then by remaining turns. Nothing of the enemy."""
    items = [*_aircraft_orders(game), *_ground_orders(game)]
    for base in game.theater.control_points_for(Player.BLUE):
        items += [
            *_maintenance(game, base),
            *_base_repairs(game, base),
            *_site_repairs(game, base),
        ]
    items += [
        _transfer_item(game, t) for t in game.coalition_for(Player.BLUE).transfers
    ]
    return sorted(
        items,
        key=lambda item: (
            _GROUP_ORDER.index(item.group),
            item.turns if item.turns is not None else float("inf"),
            item.label,
        ),
    )


def is_in_progress(item: ProductionItem) -> bool:
    """False for what waits for a decision or for money."""
    return item.group not in ("damage", "ships")


def run_production_action(
    game: Game, item_id: str, events: GameUpdateEvents
) -> ProductionItem:
    """Runs the action of one item.

    Raises:
        CommandError: the item is gone (404), has no action, or costs too much (then
            nothing is done); or why the underlying command refused.
    """
    item = next((i for i in production_items(game) if i.id == item_id), None)
    if item is None:
        raise CommandError("This item is no longer listed.", status_code=404)
    if item.action is None:
        raise CommandError(f"Nothing can be done on {item.label} now.")
    if item.action.cost > game.blue.budget:
        raise CommandError(
            f"{item.label} costs ${item.action.cost:g}M but you have only "
            f"${game.blue.budget:g}M available."
        )
    item.action.run(events)
    return item

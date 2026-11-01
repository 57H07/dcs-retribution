"""Ground objects (TGOs): unit status, repairs and group purchases (WEB-08.3).

The rules of the Qt ground object windows (`QGroundObjectMenu`, `QBuildingInfo`,
`QGroundObjectBuyMenu`), shared by the API and those windows until WEB-09:

- a destroyed unit of a player site can be repaired for its unit price, a destroyed
  building for `TheaterGroundObject.repair_cost()` when it has a value; a unit made
  inoperative by persistent damage for `accelerated_repair_cost()`, at once, with the
  `persistent_damage_paid_ground_repair` setting;
- only a purchasable site can be replaced or disbanded, at a player base (or an enemy
  one with `enable_enemy_buy_sell`), and never at a neutral base. The units of the old
  group, alive or under repair, are credited to the buyer;
- buying is free on turn 0.

Any of these changes can change the enemy's plans: a site the enemy has a package
against makes it replan (see `Game.initialize_turn`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, Literal, NoReturn, Optional, Type

from dcs.unittype import UnitType as DcsUnitType

from game.config import REWARDS
from game.data.groups import GroupRole, GroupTask
from game.theater.grounddamage import accelerated_repair_cost
from game.theater.player import Player
from game.theater.repairs import buy_repair, repair_turns_for
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    CoastalSiteGroundObject,
    EwrGroundObject,
    MissileSiteGroundObject,
    SamGroundObject,
    ShipGroundObject,
    VehicleGroupGroundObject,
)
from game.utils import Heading
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.armedforces.forcegroup import ForceGroup
    from game.layout.layout import TgoLayout, TgoLayoutUnitGroup
    from game.sim import GameUpdateEvents
    from game.theater import TheaterGroundObject
    from game.theater.theatergroup import TheaterUnit

UnitState = Literal["operational", "inoperative", "repairing", "destroyed"]


@dataclass(frozen=True)
class GroundUnitStatus:
    unit: TheaterUnit
    state: UnitState
    #: Turns before the unit is back: repair underway, or inoperative countdown.
    turns_remaining: int
    #: Price in millions of the repair the player can order; None if there is none.
    repair_cost: Optional[float]
    #: Delay of that repair once ordered (0 = at once).
    repair_turns: int


def listed_units(tgo: TheaterGroundObject) -> Iterator[TheaterUnit]:
    """The units a sheet shows: only the buildings of a building site."""
    return tgo.statics if isinstance(tgo, BuildingGroundObject) else tgo.units


def _repair_cost_of_dead_unit(
    tgo: TheaterGroundObject, unit: TheaterUnit
) -> Optional[float]:
    if isinstance(tgo, BuildingGroundObject):
        # Buildings without value are not repairable.
        cost = tgo.repair_cost()
        return cost if cost > 0 else None
    if not unit.repairable or unit.unit_type is None:
        return None
    return unit.unit_type.price


def unit_status(game: Game, unit: TheaterUnit) -> GroundUnitStatus:
    tgo = unit.ground_object
    player_site = tgo.control_point.captured.is_blue
    if not unit.alive:
        if unit.repair_turns_remaining is not None:
            return GroundUnitStatus(
                unit, "repairing", unit.repair_turns_remaining, None, 0
            )
        cost = _repair_cost_of_dead_unit(tgo, unit) if player_site else None
        turns = repair_turns_for(unit, game.settings) if cost is not None else 0
        return GroundUnitStatus(unit, "destroyed", 0, cost, turns)
    if unit.inoperative:
        turns_left = unit.inoperative_turns_remaining(game.turn)
        payable = player_site and game.settings.persistent_damage_paid_ground_repair
        cost = accelerated_repair_cost(unit) if payable else None
        return GroundUnitStatus(unit, "inoperative", turns_left, cost, 0)
    return GroundUnitStatus(unit, "operational", 0, None, 0)


def ground_object_units(game: Game, tgo: TheaterGroundObject) -> list[GroundUnitStatus]:
    return [unit_status(game, unit) for unit in listed_units(tgo)]


def building_value(tgo: TheaterGroundObject) -> float:
    """Income of one building of this site per turn; 0 for other categories."""
    return REWARDS.get(tgo.category, 0)


def _tgo_changed(
    game: Game, tgo: TheaterGroundObject, events: GameUpdateEvents
) -> None:
    tgo.invalidate_threat_poly()
    events.update_tgo(tgo)
    game.theater.iads_network.update_tgo(tgo, events)
    if any(package.target == tgo for package in game.ato_for(Player.RED).packages):
        # The opponent of the site's owner replans, not its owner: the player does
        # not redo their planning because they repaired a SAM.
        owner = tgo.coalition.player
        game.initialize_turn(events, for_red=owner.is_blue, for_blue=owner.is_red)


def _refuse_budget(tgo: TheaterGroundObject, cost: float) -> NoReturn:
    raise CommandError(
        f"This costs ${cost:g}M but you have only "
        f"${tgo.coalition.budget:g}M available."
    )


def repair_ground_unit(
    game: Game, tgo: TheaterGroundObject, unit_id: int, events: GameUpdateEvents
) -> GroundUnitStatus:
    """Pays for the repair of one unit and starts it.

    Raises:
        CommandError: unknown unit (404), nothing to order on this unit, or not
            enough budget.
    """
    unit = next((u for u in listed_units(tgo) if u.id == unit_id), None)
    if unit is None:
        raise CommandError(f"{tgo.name} has no unit {unit_id}.", status_code=404)
    status = unit_status(game, unit)
    if status.repair_cost is None:
        raise CommandError("This unit cannot be repaired now.")
    if status.state == "inoperative":
        if tgo.coalition.budget < status.repair_cost:
            _refuse_budget(tgo, status.repair_cost)
        tgo.coalition.budget -= status.repair_cost
        unit.end_inoperative(events)
    elif not buy_repair(game, unit, status.repair_cost, events):
        _refuse_budget(tgo, status.repair_cost)
    events.update_budget()
    _tgo_changed(game, tgo, events)
    return unit_status(game, unit)


def can_adjust_heading(tgo: TheaterGroundObject, player: Player = Player.BLUE) -> bool:
    if isinstance(tgo, BuildingGroundObject):
        return False
    return tgo.control_point.is_friendly(to_player=player)


def conflict_heading(game: Game, tgo: TheaterGroundObject) -> Heading:
    return game.theater.heading_to_conflict_from(tgo.position) or tgo.heading


def rotate_ground_object(
    tgo: TheaterGroundObject,
    heading: Heading,
    events: GameUpdateEvents,
    player: Player = Player.BLUE,
) -> None:
    """Turns a whole site to a new heading.

    Raises:
        CommandError: not a site of this player, or a building site.
    """
    if not can_adjust_heading(tgo, player):
        raise CommandError(f"You cannot turn {tgo.name}.")
    tgo.rotate(heading)
    events.update_tgo(tgo)


def can_hide_on_mfd(tgo: TheaterGroundObject) -> bool:
    return (
        not isinstance(tgo, BuildingGroundObject)
        and tgo.is_iads
        and tgo.control_point.is_friendly(to_player=Player.RED)
    )


def set_hidden_on_mfd(
    tgo: TheaterGroundObject, hidden: bool, events: GameUpdateEvents
) -> None:
    """Hides an enemy air defense site from the aircraft MFDs, or shows it.

    Raises:
        CommandError: not an enemy air defense site.
    """
    if not can_hide_on_mfd(tgo):
        raise CommandError(f"{tgo.name} cannot be hidden on the MFD.")
    tgo.hide_on_mfd = hidden
    events.update_tgo(tgo)


def can_buy_or_sell(game: Game, tgo: TheaterGroundObject) -> bool:
    captured = tgo.control_point.captured
    if captured.is_neutral or not tgo.purchasable:
        return False
    return game.settings.enable_enemy_buy_sell or captured.is_blue


def resale_value(tgo: TheaterGroundObject) -> int:
    """What the current group is worth: its live units and those under repair."""
    if not tgo.purchasable:
        return 0
    pending = sum(
        unit.unit_type.price
        for unit in tgo.units
        if not unit.alive
        and unit.repair_turns_remaining is not None
        and unit.unit_type is not None
    )
    return tgo.value + pending


def disband_ground_object(
    game: Game, tgo: TheaterGroundObject, events: GameUpdateEvents
) -> int:
    """Removes the group of a site and credits its owner; returns the amount.

    Raises:
        CommandError: the site cannot be sold, or has nothing left to sell.
    """
    if not can_buy_or_sell(game, tgo):
        raise CommandError(f"{tgo.name} cannot be disbanded.")
    value = resale_value(tgo)
    if value <= 0:
        raise CommandError(f"{tgo.name} has nothing left to disband.")
    tgo.coalition.budget += value
    tgo.groups = []
    events.update_budget()
    _tgo_changed(game, tgo, events)
    return value


def _purchase_tasks(tgo: TheaterGroundObject) -> Optional[list[GroupTask]]:
    if isinstance(tgo, SamGroundObject):
        return GroupRole.AIR_DEFENSE.tasks
    if isinstance(tgo, VehicleGroupGroundObject):
        return GroupRole.GROUND_FORCE.tasks
    if isinstance(tgo, EwrGroundObject):
        return [GroupTask.EARLY_WARNING_RADAR]
    if isinstance(tgo, ShipGroundObject):
        return [GroupTask.NAVY]
    if isinstance(tgo, MissileSiteGroundObject):
        return [GroupTask.MISSILE]
    if isinstance(tgo, CoastalSiteGroundObject):
        return [GroupTask.COASTAL]
    return None


def purchasable_force_groups(tgo: TheaterGroundObject) -> list[ForceGroup]:
    """The force groups of the owner's faction that fit this site, by name."""
    tasks = _purchase_tasks(tgo)
    if tasks is None:
        return []
    return tgo.coalition.armed_forces.groups_for_tasks(tasks)


@dataclass(frozen=True)
class SlotOption:
    #: DCS id of the type, passed back in `SlotChoice`.
    id: str
    name: str
    price: int
    dcs_unit_type: Type[DcsUnitType]


@dataclass(frozen=True)
class LayoutSlot:
    """A set of units of one type in a layout: what the buyer picks."""

    #: Position in the layout, passed back in `SlotChoice`.
    id: int
    group_name: str
    unit_group: TgoLayoutUnitGroup
    options: list[SlotOption]
    #: Default number of units (random in the range of the layout, if it has one).
    amount: int
    max_amount: int
    optional: bool


def _slot_options(
    force_group: ForceGroup, unit_group: TgoLayoutUnitGroup
) -> list[SlotOption]:
    options: dict[str, SlotOption] = {}
    for unit_type in force_group.unit_types_for_group(unit_group):
        dcs_type = unit_type.dcs_unit_type
        options.setdefault(
            dcs_type.id,
            SlotOption(dcs_type.id, unit_type.display_name, unit_type.price, dcs_type),
        )
    for static_type in force_group.statics_for_group(unit_group):
        options.setdefault(
            static_type.id,
            SlotOption(static_type.id, f"{static_type.id} (Static)", 0, static_type),
        )
    return list(options.values())


def layout_slots(force_group: ForceGroup, layout: TgoLayout) -> list[LayoutSlot]:
    """The slots of a layout, without those the force group has no unit for."""
    slots = []
    index = 0
    for group in layout.groups:
        for unit_group in group.unit_groups:
            options = _slot_options(force_group, unit_group)
            if options:
                slots.append(
                    LayoutSlot(
                        index,
                        group.group_name,
                        unit_group,
                        options,
                        unit_group.group_size,
                        unit_group.max_size,
                        unit_group.optional,
                    )
                )
            index += 1
    return slots


@dataclass(frozen=True)
class SlotChoice:
    slot: int
    unit_type: str
    amount: int


@dataclass(frozen=True)
class PurchaseLine:
    group_name: str
    unit_group: TgoLayoutUnitGroup
    dcs_unit_type: Type[DcsUnitType]
    amount: int
    unit_price: int


@dataclass(frozen=True)
class TgoPurchase:
    force_group: ForceGroup
    lines: list[PurchaseLine]

    @property
    def price(self) -> int:
        return sum(line.amount * line.unit_price for line in self.lines)


@dataclass(frozen=True)
class PurchaseQuote:
    #: Price of the new group.
    price: int
    #: Value of the old group, deducted from the price.
    credit: int
    #: What the buyer pays (negative when they get money back; 0 on turn 0).
    cost: int
    affordable: bool


def _named_force_group(tgo: TheaterGroundObject, name: str) -> ForceGroup:
    for force_group in purchasable_force_groups(tgo):
        if force_group.name == name:
            return force_group
    raise CommandError(f"{name} is not available at {tgo.name}.")


def _named_layout(force_group: ForceGroup, name: str) -> TgoLayout:
    for layout in force_group.layouts:
        if layout.name == name:
            return layout
    raise CommandError(f"{force_group.name} has no layout {name}.")


def _purchase_line(slot: LayoutSlot, choice: SlotChoice) -> PurchaseLine:
    option = next((o for o in slot.options if o.id == choice.unit_type), None)
    if option is None:
        raise CommandError(f"{choice.unit_type} does not fit {slot.group_name}.")
    if not 1 <= choice.amount <= slot.max_amount:
        raise CommandError(
            f"{slot.group_name} takes 1 to {slot.max_amount} units of this type."
        )
    return PurchaseLine(
        slot.group_name,
        slot.unit_group,
        option.dcs_unit_type,
        choice.amount,
        option.price,
    )


def resolve_purchase(
    tgo: TheaterGroundObject,
    force_group_name: str,
    layout_name: str,
    choices: list[SlotChoice],
) -> TgoPurchase:
    """Checks a purchase against the layout: a slot left out is not bought.

    Raises:
        CommandError: unknown force group, layout or slot, a required slot left out,
            a unit type or an amount the slot does not take, or nothing bought.
    """
    force_group = _named_force_group(tgo, force_group_name)
    layout = _named_layout(force_group, layout_name)
    chosen = {choice.slot: choice for choice in choices}
    lines = []
    for slot in layout_slots(force_group, layout):
        choice = chosen.pop(slot.id, None)
        if choice is not None:
            lines.append(_purchase_line(slot, choice))
        elif not slot.optional:
            raise CommandError(f"{slot.group_name} is required in this layout.")
    if chosen:
        raise CommandError("This layout has no such position.")
    if not lines:
        raise CommandError("Choose at least one unit.")
    return TgoPurchase(force_group, lines)


def quote_purchase(
    game: Game, tgo: TheaterGroundObject, purchase: TgoPurchase
) -> PurchaseQuote:
    credit = resale_value(tgo)
    cost = purchase.price - credit
    return PurchaseQuote(
        purchase.price,
        credit,
        cost if game.turn else 0,
        cost <= tgo.coalition.budget or game.turn == 0,
    )


def buy_ground_object_group(
    game: Game,
    tgo: TheaterGroundObject,
    purchase: TgoPurchase,
    events: GameUpdateEvents,
) -> PurchaseQuote:
    """Replaces the group of a site, which then heads to the conflict.

    Raises:
        CommandError: the site cannot be bought, or not enough budget.
    """
    if not can_buy_or_sell(game, tgo):
        raise CommandError(f"You cannot buy units at {tgo.name}.")
    quote = quote_purchase(game, tgo, purchase)
    if not quote.affordable:
        _refuse_budget(tgo, quote.cost)
    tgo.heading = conflict_heading(game, tgo)
    tgo.coalition.budget -= quote.cost
    tgo.groups = []
    for line in purchase.lines:
        purchase.force_group.create_theater_group_for_tgo(
            tgo,
            line.unit_group,
            f"{tgo.name} ({line.group_name})",
            game,
            line.dcs_unit_type,
            line.amount,
        )
    events.update_budget()
    _tgo_changed(game, tgo, events)
    return quote

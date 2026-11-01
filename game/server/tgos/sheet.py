"""What the ground object sheet shows (WEB-08.3).

The rules are in `game.commands.groundobjects`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel

from game.commands import (
    GroundUnitStatus,
    LayoutSlot,
    PurchaseQuote,
    SlotChoice,
    UnitState,
    building_value,
    can_adjust_heading,
    can_buy_or_sell,
    can_hide_on_mfd,
    conflict_heading,
    ground_object_units,
    layout_slots,
    purchasable_force_groups,
    resale_value,
)
from game.dcs.groundunittype import GroundUnitType
from game.dcs.shipunittype import ShipUnitType
from game.theater.theatergroundobject import BuildingGroundObject
from game.theater.theatergroup import SceneryUnit, TheaterUnit
from .summary import TgoSummaryJs

if TYPE_CHECKING:
    from game import Game
    from game.armedforces.forcegroup import ForceGroup
    from game.layout.layout import TgoLayout
    from game.theater import TheaterGroundObject


class TgoUnitJs(BaseModel):
    id: int
    name: str
    #: Identifies the unit info sheet (GET /unit-info); None without a unit type.
    info_kind: Optional[Literal["ground", "ship"]]
    info_name: Optional[str]
    state: UnitState
    #: Turns before the unit is back, while it is repairing or inoperative.
    turns_remaining: int
    #: Price of the repair the player can order; None when there is none to order.
    repair_cost: Optional[float]
    #: Delay of that repair once ordered (0 = at once).
    repair_turns: int
    repair_affordable: bool

    class Config:
        title = "TgoUnit"

    @staticmethod
    def for_status(status: GroundUnitStatus, budget: float) -> TgoUnitJs:
        unit_type = status.unit.unit_type
        info_kind: Optional[Literal["ground", "ship"]] = None
        if isinstance(unit_type, GroundUnitType):
            info_kind = "ground"
        elif isinstance(unit_type, ShipUnitType):
            info_kind = "ship"
        return TgoUnitJs(
            id=status.unit.id,
            name=_unit_name(status.unit),
            info_kind=info_kind,
            info_name=unit_type.variant_id if unit_type is not None else None,
            state=status.state,
            turns_remaining=status.turns_remaining,
            repair_cost=status.repair_cost,
            repair_turns=status.repair_turns,
            repair_affordable=(
                status.repair_cost is not None and status.repair_cost <= budget
            ),
        )


def _unit_name(unit: TheaterUnit) -> str:
    if isinstance(unit, SceneryUnit):
        return unit.name
    return str(unit.unit_type or unit.type.id)


class TgoIncomeJs(BaseModel):
    #: Income of one building per turn.
    per_building: float
    #: Income per turn with every building standing.
    available: float
    #: Income per turn of the buildings standing now.
    receiving: float

    class Config:
        title = "TgoIncome"


class TgoHeadingJs(BaseModel):
    degrees: int
    can_adjust: bool
    #: Where "Head to conflict" turns the site.
    to_conflict: int

    class Config:
        title = "TgoHeading"


class TgoSheetJs(BaseModel):
    summary: TgoSummaryJs
    budget: float
    is_building_site: bool
    units: list[TgoUnitJs]
    #: Building sites of the player only.
    income: Optional[TgoIncomeJs]
    #: Not for building sites.
    heading: Optional[TgoHeadingJs]
    #: None when the site cannot be hidden on the MFD.
    hidden_on_mfd: Optional[bool]
    can_buy: bool
    #: What disbanding the group pays; 0 when it cannot be disbanded.
    disband_value: int

    class Config:
        title = "TgoSheet"

    @staticmethod
    def for_tgo(game: Game, tgo: TheaterGroundObject) -> TgoSheetJs:
        budget = tgo.coalition.budget
        is_building_site = isinstance(tgo, BuildingGroundObject)
        can_buy = can_buy_or_sell(game, tgo)
        return TgoSheetJs(
            summary=TgoSummaryJs.for_tgo(game, tgo),
            budget=budget,
            is_building_site=is_building_site,
            units=[
                TgoUnitJs.for_status(status, budget)
                for status in ground_object_units(game, tgo)
            ],
            income=_income(tgo) if is_building_site else None,
            heading=None if is_building_site else _heading(game, tgo),
            hidden_on_mfd=tgo.hide_on_mfd if can_hide_on_mfd(tgo) else None,
            can_buy=can_buy,
            disband_value=resale_value(tgo) if can_buy else 0,
        )


def _income(tgo: TheaterGroundObject) -> Optional[TgoIncomeJs]:
    if not tgo.control_point.captured.is_blue:
        return None
    value = building_value(tgo)
    statics = list(tgo.statics)
    return TgoIncomeJs(
        per_building=value,
        available=value * len(statics),
        receiving=value * sum(unit.alive for unit in statics),
    )


def _heading(game: Game, tgo: TheaterGroundObject) -> TgoHeadingJs:
    return TgoHeadingJs(
        degrees=tgo.heading.degrees,
        can_adjust=can_adjust_heading(tgo),
        to_conflict=conflict_heading(game, tgo).degrees,
    )


class SlotOptionJs(BaseModel):
    id: str
    name: str
    price: int

    class Config:
        title = "SlotOption"


class LayoutSlotJs(BaseModel):
    id: int
    group_name: str
    options: list[SlotOptionJs]
    amount: int
    max_amount: int
    optional: bool

    class Config:
        title = "LayoutSlot"

    @staticmethod
    def for_slot(slot: LayoutSlot) -> LayoutSlotJs:
        return LayoutSlotJs(
            id=slot.id,
            group_name=slot.group_name,
            options=[
                SlotOptionJs(id=option.id, name=option.name, price=option.price)
                for option in slot.options
            ],
            amount=slot.amount,
            max_amount=slot.max_amount,
            optional=slot.optional,
        )


class PurchaseLayoutJs(BaseModel):
    name: str
    slots: list[LayoutSlotJs]

    class Config:
        title = "PurchaseLayout"

    @staticmethod
    def for_layout(force_group: ForceGroup, layout: TgoLayout) -> PurchaseLayoutJs:
        return PurchaseLayoutJs(
            name=layout.name,
            slots=[
                LayoutSlotJs.for_slot(slot)
                for slot in layout_slots(force_group, layout)
            ],
        )


class PurchaseForceGroupJs(BaseModel):
    name: str
    layouts: list[PurchaseLayoutJs]

    class Config:
        title = "PurchaseForceGroup"


class TgoPurchaseOptionsJs(BaseModel):
    force_groups: list[PurchaseForceGroupJs]

    class Config:
        title = "TgoPurchaseOptions"

    @staticmethod
    def for_tgo(tgo: TheaterGroundObject) -> TgoPurchaseOptionsJs:
        return TgoPurchaseOptionsJs(
            force_groups=[
                PurchaseForceGroupJs(
                    name=force_group.name,
                    layouts=[
                        PurchaseLayoutJs.for_layout(force_group, layout)
                        for layout in force_group.layouts
                    ],
                )
                for force_group in purchasable_force_groups(tgo)
            ]
        )


class SlotChoiceJs(BaseModel):
    slot: int
    unit_type: str
    amount: int

    class Config:
        title = "SlotChoice"

    def to_choice(self) -> SlotChoice:
        return SlotChoice(self.slot, self.unit_type, self.amount)


class TgoPurchaseJs(BaseModel):
    force_group: str
    layout: str
    #: The slots to fill; a slot left out is not bought.
    choices: list[SlotChoiceJs]

    class Config:
        title = "TgoPurchase"


class PurchaseQuoteJs(BaseModel):
    price: int
    credit: int
    cost: int
    affordable: bool

    class Config:
        title = "PurchaseQuote"

    @staticmethod
    def for_quote(quote: PurchaseQuote) -> PurchaseQuoteJs:
        return PurchaseQuoteJs(
            price=quote.price,
            credit=quote.credit,
            cost=quote.cost,
            affordable=quote.affordable,
        )


class TgoHeadingChangeJs(BaseModel):
    degrees: int

    class Config:
        title = "TgoHeadingChange"


class TgoHiddenChangeJs(BaseModel):
    hidden: bool

    class Config:
        title = "TgoHiddenChange"

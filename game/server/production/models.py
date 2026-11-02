"""DTOs of the Production & repairs screen (issue #182)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import BaseModel

from game.commands.production import (
    ProductionGroup,
    ProductionItem,
    is_in_progress,
    production_items,
)

if TYPE_CHECKING:
    from game import Game


class ProductionActionJs(BaseModel):
    label: str
    #: Millions to pay; negative for a refund.
    cost: float
    affordable: bool

    class Config:
        title = "ProductionAction"


class ProductionItemJs(BaseModel):
    id: str
    group: ProductionGroup
    label: str
    detail: str
    #: None when no delay is known.
    turns: Optional[int]
    base_id: Optional[UUID]
    tgo_id: Optional[UUID]
    action: Optional[ProductionActionJs]

    class Config:
        title = "ProductionItem"

    @staticmethod
    def for_item(item: ProductionItem, budget: float) -> ProductionItemJs:
        return ProductionItemJs(
            id=item.id,
            group=item.group,
            label=item.label,
            detail=item.detail,
            turns=item.turns,
            base_id=item.base.id if item.base is not None else None,
            tgo_id=item.tgo.id if item.tgo is not None else None,
            action=(
                ProductionActionJs(
                    label=item.action.label,
                    cost=item.action.cost,
                    affordable=item.action.cost <= budget,
                )
                if item.action is not None
                else None
            ),
        )


class ProductionJs(BaseModel):
    in_progress: list[ProductionItemJs]
    to_handle: list[ProductionItemJs]
    #: Turns until the next item ends; None when no delay is known.
    next_end_turns: Optional[int]
    budget: float

    class Config:
        title = "Production"

    @staticmethod
    def for_game(game: Game) -> ProductionJs:
        budget = game.blue.budget
        items = production_items(game)
        running = [i for i in items if is_in_progress(i)]
        return ProductionJs(
            in_progress=[ProductionItemJs.for_item(i, budget) for i in running],
            to_handle=[
                ProductionItemJs.for_item(i, budget)
                for i in items
                if not is_in_progress(i)
            ],
            next_end_turns=min(
                (i.turns for i in running if i.turns is not None), default=None
            ),
            budget=budget,
        )

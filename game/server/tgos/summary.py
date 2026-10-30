"""Summary of a ground object for the map inspector (WEB-01.3)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import BaseModel

from game.server.controlpoints.summary import CountJs, distance_to_front_nm

if TYPE_CHECKING:
    from game import Game
    from game.theater import TheaterGroundObject


CATEGORY_LABELS = {"aa": "Air defense", "ewr": "EWR"}


def readable(name: str) -> str:
    """ "EarlyWarningRadar" -> "Early Warning Radar", "armor" -> "Armor"."""
    if name in CATEGORY_LABELS:
        return CATEGORY_LABELS[name]
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)
    return spaced[:1].upper() + spaced[1:]


class TgoSummaryJs(BaseModel):
    id: UUID
    name: str
    blue: bool
    sidc: str
    #: The group task when known (e.g. "LORAD"), else the TGO category.
    category: str
    control_point_id: UUID
    control_point_name: str
    distance_to_front_nm: Optional[float]
    #: Alive units / all units.
    units: CountJs
    dead: bool

    class Config:
        title = "TgoSummary"

    @staticmethod
    def for_tgo(game: Game, tgo: TheaterGroundObject) -> TgoSummaryJs:
        task = tgo.groups[0].ground_object.task if tgo.groups else None
        category = task.description if task is not None else tgo.category
        return TgoSummaryJs(
            id=tgo.id,
            name=tgo.name,
            blue=tgo.control_point.captured.is_blue,
            sidc=str(tgo.sidc()),
            category=readable(category),
            control_point_id=tgo.control_point.id,
            control_point_name=tgo.control_point.name,
            distance_to_front_nm=distance_to_front_nm(game, tgo.position),
            units=CountJs(current=tgo.alive_unit_count, total=tgo.unit_count),
            dead=tgo.is_dead,
        )

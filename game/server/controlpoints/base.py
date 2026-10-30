"""Base screen (WEB-02.1): status, air defense, intel and repairs of one base.

Same content as the Qt base menu (`qt_ui/windows/basemenu/`): its tabs, the
intel summary of its header, its runway repair button, and the building and
aircraft repairs of `game.commands.repairs`.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from game.commands.repairs import Repair, RepairKind, base_repairs
from game.theater.controlpoint import Fob
from .summary import ALL_PARKING, ControlPointSummaryJs, CountJs
from ..reports.models import UnitCountJs
from ..tgos.summary import readable

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint, TheaterGroundObject

BaseTabId = Literal["airfield", "ground-forces", "intel", "convoys"]

#: TGO categories that are air defense even without a working anti-air unit.
AIR_DEFENSE_CATEGORIES = {"aa", "ewr"}


class BaseTabJs(BaseModel):
    id: BaseTabId
    label: str

    class Config:
        title = "BaseTab"


class AirDefenseJs(BaseModel):
    id: str
    name: str
    #: The group task when known (e.g. "SHORAD"), else the TGO category.
    category: str
    units: CountJs
    #: At least one anti-air unit can fire.
    operational: bool

    class Config:
        title = "AirDefense"


class RepairJs(BaseModel):
    id: str
    kind: RepairKind
    label: str
    cost: float
    turns: int
    in_progress: bool
    affordable: bool

    class Config:
        title = "Repair"

    @staticmethod
    def from_repair(repair: Repair, budget: float) -> RepairJs:
        return RepairJs(
            id=repair.id,
            kind=repair.kind,
            label=repair.label,
            cost=repair.cost,
            turns=repair.turns,
            in_progress=repair.in_progress,
            affordable=not repair.in_progress and repair.cost <= budget,
        )


class IntelGroupJs(BaseModel):
    #: Aircraft task ("CAP", "CAS"...) or "Front line units".
    title: str
    units: list[UnitCountJs]

    class Config:
        title = "IntelGroup"


class BaseJs(BaseModel):
    summary: ControlPointSummaryJs
    budget: float
    #: Tabs of the Qt base menu for this base, in its order.
    tabs: list[BaseTabJs]
    air_defenses: list[AirDefenseJs]
    #: Orderable repairs first, then repairs in progress. Empty for an enemy base.
    repairs: list[RepairJs]
    #: Total of the orderable repairs ("Repair all"), 0 when there is none.
    repair_all_cost: float
    #: At least one orderable repair, and the budget covers them all.
    repair_all_affordable: bool
    intel: list[IntelGroupJs]

    class Config:
        title = "Base"

    @staticmethod
    def for_control_point(game: Game, cp: ControlPoint) -> BaseJs:
        budget = game.blue.budget
        repairs = base_repairs(game, cp)
        orderable = [r for r in repairs if not r.in_progress]
        repair_all_cost = sum(r.cost for r in orderable)
        return BaseJs(
            summary=ControlPointSummaryJs.for_control_point(game, cp),
            budget=budget,
            tabs=base_tabs(cp),
            air_defenses=[
                air_defense(tgo) for tgo in cp.ground_objects if is_air_defense(tgo)
            ],
            repairs=[RepairJs.from_repair(r, budget) for r in repairs],
            repair_all_cost=repair_all_cost,
            repair_all_affordable=bool(orderable) and repair_all_cost <= budget,
            intel=intel(cp),
        )


def base_tabs(cp: ControlPoint) -> list[BaseTabJs]:
    """The tabs `QBaseMenuTabs` shows for this base."""
    airfield = BaseTabJs(id="airfield", label="Airfield command")
    ground = BaseTabJs(id="ground-forces", label="Ground forces HQ")
    if not cp.captured.is_blue:
        return [
            BaseTabJs(id="intel", label="Intel"),
            BaseTabJs(id="convoys", label="Departing convoys"),
        ]
    if isinstance(cp, Fob):
        tabs = [ground]
        if cp.has_ground_spawns:
            tabs.append(airfield)
        elif cp.has_helipads:
            tabs.append(BaseTabJs(id="airfield", label="Heliport"))
        return tabs
    if cp.can_deploy_ground_units:
        return [airfield, ground]
    return [airfield]


def is_air_defense(tgo: TheaterGroundObject) -> bool:
    return tgo.category in AIR_DEFENSE_CATEGORIES or any(
        unit.is_anti_air for unit in tgo.units
    )


def air_defense(tgo: TheaterGroundObject) -> AirDefenseJs:
    task = tgo.groups[0].ground_object.task if tgo.groups else None
    category = task.description if task is not None else tgo.category
    return AirDefenseJs(
        id=str(tgo.id),
        name=tgo.name,
        category=readable(category),
        units=CountJs(current=tgo.alive_unit_count, total=tgo.unit_count),
        operational=tgo.has_aa,
    )


def intel(cp: ControlPoint) -> list[IntelGroupJs]:
    """Units present at the base, as `QIntelInfo` groups them."""
    by_task: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for unit_type, count in cp.allocated_aircraft(ALL_PARKING).present.items():
        if count:
            default_task = unit_type.dcs_unit_type.task_default
            task = (default_task.name if default_task is not None else None) or "Other"
            by_task[task][unit_type.display_name] += count
    groups = [(task, by_task[task]) for task in sorted(by_task)]
    front_line: dict[str, int] = defaultdict(int)
    for ground_type, count in cp.base.armor.items():
        if count:
            front_line[ground_type.display_name] += count
    groups.append(("Front line units", front_line))
    return [
        IntelGroupJs(
            title=title,
            units=[
                UnitCountJs(name=name, count=count)
                for name, count in sorted(units.items())
            ],
        )
        for title, units in groups
    ]

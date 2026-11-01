"""Repairs ordered from a base (WEB-02.1).

The repairs the player can order at one of their bases, with the rules of the Qt
windows that offered them until now:

- the runway (`QBaseMenu2`): `RUNWAY_REPAIR_COST`, `RUNWAY_REPAIR_TURNS` turns;
- destroyed buildings of the base's building ground objects, e.g. its depots
  (`QBuildingInfo`): `TheaterGroundObject.repair_cost()` per building,
  `building_repair_turns()` turns;
- aircraft in maintenance after persistent damage (`SquadronDialog`, PER-01.2):
  `Squadron.expedited_repair_cost`, at once, only with the
  `expedited_aircraft_repair` setting.

Repairs already running (or aircraft maintenance that cannot be paid for) are
listed too, as `in_progress`, so that the base screen shows every delay.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, Literal

from game.config import RUNWAY_REPAIR_COST, RUNWAY_REPAIR_TURNS
from game.theater.repairs import begin_repair, building_repair_turns
from game.theater.theatergroundobject import BuildingGroundObject
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.sim import GameUpdateEvents
    from game.squadrons import Squadron
    from game.theater import ControlPoint, TheaterGroundObject

RepairKind = Literal["runway", "buildings", "aircraft"]

#: Id of the runway repair of a base.
RUNWAY_REPAIR_ID = "runway"


@dataclass(frozen=True)
class Repair:
    #: Stable id of the repair at its base, passed back to `order_repair`.
    id: str
    kind: RepairKind
    label: str
    #: Price in millions; 0 for a repair in progress.
    cost: float
    #: Turns until repaired: the delay once ordered (0 = at once), or the turns
    #: remaining for a repair in progress.
    turns: int
    #: Already running, or not something the player can pay for: not orderable.
    in_progress: bool


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _runway_repairs(cp: ControlPoint) -> Iterator[Repair]:
    if not cp.runway_is_destroyable:
        return
    status = cp.runway_status
    if status.repair_turns_remaining is not None:
        yield Repair(
            RUNWAY_REPAIR_ID,
            "runway",
            "Runway",
            0,
            status.repair_turns_remaining,
            True,
        )
    elif cp.runway_can_be_repaired:
        yield Repair(
            RUNWAY_REPAIR_ID,
            "runway",
            "Runway",
            RUNWAY_REPAIR_COST,
            RUNWAY_REPAIR_TURNS,
            False,
        )


def _building_repairs(game: Game, cp: ControlPoint) -> Iterator[Repair]:
    for tgo in cp.ground_objects:
        if not isinstance(tgo, BuildingGroundObject):
            continue
        price = tgo.repair_cost()
        if price <= 0:
            # Same as QBuildingInfo: buildings without value are not repairable.
            continue
        dead = [unit for unit in tgo.statics if not unit.alive]
        waiting = [unit for unit in dead if unit.repair_turns_remaining is None]
        repairing = [
            unit.repair_turns_remaining
            for unit in dead
            if unit.repair_turns_remaining is not None
        ]
        if waiting:
            yield Repair(
                f"tgo:{tgo.id}",
                "buildings",
                f"{tgo.name}: {_plural(len(waiting), 'building')}",
                price * len(waiting),
                building_repair_turns(tgo.category, game.settings),
                False,
            )
        if repairing:
            yield Repair(
                f"tgo:{tgo.id}:repairing",
                "buildings",
                f"{tgo.name}: {_plural(len(repairing), 'building')}",
                0,
                max(repairing),
                True,
            )


def _aircraft_repairs(game: Game, cp: ControlPoint) -> Iterator[Repair]:
    for squadron in cp.squadrons:
        count = squadron.aircraft_in_maintenance
        if not count:
            continue
        label = (
            f"{_plural(count, 'damaged ' + squadron.aircraft.display_name)}"
            f" ({squadron.name})"
        )
        summary = squadron.maintenance_summary
        turns_left = max((turns for _, turns in summary), default=1)
        if game.settings.expedited_aircraft_repair:
            yield Repair(
                f"squadron:{squadron.id}",
                "aircraft",
                label,
                squadron.expedited_repair_cost,
                0,
                False,
            )
        else:
            yield Repair(
                f"squadron:{squadron.id}", "aircraft", label, 0, turns_left, True
            )


def base_repairs(game: Game, cp: ControlPoint) -> list[Repair]:
    """Repairs of a player base, orderable first; nothing for another base."""
    if not cp.captured.is_blue:
        return []
    repairs = [
        *_runway_repairs(cp),
        *_building_repairs(game, cp),
        *_aircraft_repairs(game, cp),
    ]
    return sorted(repairs, key=lambda r: r.in_progress)


def _apply(
    game: Game, cp: ControlPoint, repair: Repair, events: GameUpdateEvents
) -> None:
    game.blue.budget -= repair.cost
    if repair.kind == "runway":
        cp.begin_runway_repair()
        events.update_control_point(cp)
    elif repair.kind == "buildings":
        tgo = _ground_object(cp, repair.id)
        for unit in tgo.statics:
            if not unit.alive and unit.repair_turns_remaining is None:
                begin_repair(game, unit, events)
        events.update_tgo(tgo)
    else:
        _squadron(cp, repair.id).expedite_maintenance()
    events.update_budget()


def _ground_object(cp: ControlPoint, repair_id: str) -> TheaterGroundObject:
    return next(tgo for tgo in cp.ground_objects if f"tgo:{tgo.id}" == repair_id)


def _squadron(cp: ControlPoint, repair_id: str) -> Squadron:
    return next(s for s in cp.squadrons if f"squadron:{s.id}" == repair_id)


def _require_player_base(cp: ControlPoint) -> None:
    if not cp.captured.is_blue:
        raise CommandError(f"{cp.name} is not your base: you cannot repair it.")


def _refuse_budget(game: Game, cost: float, what: str) -> None:
    if cost > game.blue.budget:
        raise CommandError(
            f"{what} costs ${cost:g}M but you have only "
            f"${game.blue.budget:g}M available."
        )


def order_repair(
    game: Game, cp: ControlPoint, repair_id: str, events: GameUpdateEvents
) -> Repair:
    """Pays for one repair of `base_repairs` and starts it.

    Raises:
        CommandError: not a player base, nothing to repair under this id (unknown
            or already repairing), or not enough budget.
    """
    _require_player_base(cp)
    repairs = {r.id: r for r in base_repairs(game, cp) if not r.in_progress}
    repair = repairs.get(repair_id)
    if repair is None:
        raise CommandError("Nothing to repair there, or the repair is underway.")
    _refuse_budget(game, repair.cost, f"Repairing {repair.label}")
    _apply(game, cp, repair, events)
    return repair


def order_all_repairs(
    game: Game, cp: ControlPoint, events: GameUpdateEvents
) -> list[Repair]:
    """Pays for every orderable repair of the base at once.

    Raises:
        CommandError: not a player base, nothing to repair, or the total is more
            than the budget (then nothing is repaired).
    """
    _require_player_base(cp)
    repairs = [r for r in base_repairs(game, cp) if not r.in_progress]
    if not repairs:
        raise CommandError(f"Nothing at {cp.name} needs a repair.")
    _refuse_budget(game, sum(r.cost for r in repairs), "Repairing everything")
    for repair in repairs:
        _apply(game, cp, repair, events)
    return repairs

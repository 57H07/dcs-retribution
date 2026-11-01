"""Game commands: the business side of player actions (WEB-00.5).

A command mutates `Game` and is shared by the API routes (`game/server/**/routes.py`)
and the remaining Qt widgets, so that both front ends apply the same rules. Commands
know nothing about HTTP or Qt: they raise `CommandError` when the action is not
allowed, which the server turns into a 4xx response (see `game/server/app.py`).

Callers hold the global game lock (`game.gamelock`) while running a command.
"""

from .aircraftorders import (
    AircraftOrder,
    AircraftPurchaseAdapter,
    SquadronChoice,
    cancel_aircraft_orders,
    change_aircraft_order,
    create_squadron,
    max_aircraft_to_add,
    max_aircraft_to_remove,
    order_aircraft,
    squadron_choices,
)
from .errors import CommandError
from .mission import (
    MissionSim,
    fix_past_tots,
    fix_tots,
    flights_missing_pilots,
    generate_mission,
    max_player_count,
    packages_starting_in_the_past,
)
from .missionresult import (
    MissionResultSnapshot,
    MissionResultStatus,
    MissionResultWaiter,
    ResultSim,
    abort_mission,
    accept_and_report,
    accept_results,
)
from .repairs import (
    RUNWAY_REPAIR_ID,
    Repair,
    base_repairs,
    order_all_repairs,
    order_repair,
)
from .sim import SpeedControlledSim, set_sim_speed
from .turn import skip_turn

__all__ = [
    "AircraftOrder",
    "AircraftPurchaseAdapter",
    "CommandError",
    "RUNWAY_REPAIR_ID",
    "Repair",
    "MissionResultSnapshot",
    "MissionResultStatus",
    "MissionResultWaiter",
    "MissionSim",
    "ResultSim",
    "SpeedControlledSim",
    "SquadronChoice",
    "abort_mission",
    "accept_and_report",
    "accept_results",
    "base_repairs",
    "cancel_aircraft_orders",
    "change_aircraft_order",
    "create_squadron",
    "fix_past_tots",
    "fix_tots",
    "flights_missing_pilots",
    "generate_mission",
    "max_aircraft_to_add",
    "max_aircraft_to_remove",
    "max_player_count",
    "order_aircraft",
    "order_all_repairs",
    "order_repair",
    "packages_starting_in_the_past",
    "set_sim_speed",
    "skip_turn",
    "squadron_choices",
]

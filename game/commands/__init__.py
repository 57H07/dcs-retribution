"""Game commands: the business side of player actions (WEB-00.5).

A command mutates `Game` and is shared by the API routes (`game/server/**/routes.py`)
and the remaining Qt widgets, so that both front ends apply the same rules. Commands
know nothing about HTTP or Qt: they raise `CommandError` when the action is not
allowed, which the server turns into a 4xx response (see `game/server/app.py`).

Callers hold the global game lock (`game.gamelock`) while running a command.
"""

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
from .sim import SpeedControlledSim, set_sim_speed
from .turn import skip_turn

__all__ = [
    "CommandError",
    "MissionSim",
    "SpeedControlledSim",
    "fix_past_tots",
    "fix_tots",
    "flights_missing_pilots",
    "generate_mission",
    "max_player_count",
    "packages_starting_in_the_past",
    "set_sim_speed",
    "skip_turn",
]

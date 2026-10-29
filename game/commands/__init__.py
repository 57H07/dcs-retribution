"""Game commands: the business side of player actions (WEB-00.5).

A command mutates `Game` and is shared by the API routes (`game/server/**/routes.py`)
and the remaining Qt widgets, so that both front ends apply the same rules. Commands
know nothing about HTTP or Qt: they raise `CommandError` when the action is not
allowed, which the server turns into a 4xx response (see `game/server/app.py`).

Callers hold the global game lock (`game.gamelock`) while running a command.
"""

from .errors import CommandError
from .turn import skip_turn

__all__ = ["CommandError", "skip_turn"]

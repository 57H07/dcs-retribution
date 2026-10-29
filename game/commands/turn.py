from __future__ import annotations

from typing import TYPE_CHECKING

from game.profiling import logged_duration
from .errors import CommandError

if TYPE_CHECKING:
    from game.game import Game, TurnState


def skip_turn(game: Game) -> TurnState:
    """Skip the current turn without flying it ("Pass Turn" / "Begin Campaign").

    Ends the turn, starts the next one, publishes the resulting game update events
    (with `new_turn` set, so that every open web screen reloads its state) and
    autosaves.

    Returns the campaign state once the new turn has started.

    Raises:
        CommandError: the campaign is already won or lost.
    """
    from game.game import TurnState

    if game.check_win_loss() is not TurnState.CONTINUE:
        raise CommandError("The campaign is over: no further turn can be played.")
    with logged_duration("Skipping turn"):
        game.pass_turn(no_action=True)
    return game.check_win_loss()

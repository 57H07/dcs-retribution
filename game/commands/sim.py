"""Simulation speed (WEB-01.1), shared by the web UI and the Qt controls."""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

from game.sim.simspeedsetting import SimSpeedSetting
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game


class SpeedControlledSim(Protocol):
    """The part of the simulation the speed controls drive (`SimController`)."""

    @property
    def completed(self) -> bool: ...

    def set_simulation_speed(self, simulation_speed: SimSpeedSetting) -> None: ...


def set_sim_speed(game: Game, sim: SpeedControlledSim, speed: SimSpeedSetting) -> None:
    """Pause the simulation or run it at `speed`.

    Raises:
        CommandError: the campaign has not begun, or the simulation is complete
            (it can only stay paused).
    """
    if speed is SimSpeedSetting.PAUSED:
        sim.set_simulation_speed(speed)
        return
    if game.turn == 0:
        raise CommandError("Begin the campaign before running the simulation.")
    if sim.completed:
        raise CommandError("The simulation of this turn is complete.")
    sim.set_simulation_speed(speed)

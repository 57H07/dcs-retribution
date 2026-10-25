"""Player pilot careers (PER-03.2).

A career is a player pilot together with the squadron they belong to. The
pilot's ``PilotRecord`` is the logbook; this module only finds careers, so no
extra state is saved and any number of careers can exist (one per player pilot,
e.g. for multiplayer squadrons). The UI exposes one: ``player_career``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from .pilot import Pilot, PilotRecord

if TYPE_CHECKING:
    from .airwing import AirWing
    from .squadron import Squadron


@dataclass(frozen=True)
class Career:
    pilot: Pilot
    squadron: Squadron

    @property
    def logbook(self) -> PilotRecord:
        return self.pilot.record


def careers(air_wing: AirWing) -> list[Career]:
    """Every player pilot of the air wing, dead ones included.

    Living pilots come first, then squadron and roster order.
    """
    found = [
        Career(pilot, squadron)
        for squadron in air_wing.iter_squadrons()
        for pilot in squadron.current_roster
        if pilot.player
    ]
    found.sort(key=lambda career: not career.pilot.alive)
    return found


def player_career(air_wing: AirWing) -> Optional[Career]:
    """The career shown to the player: the first one found, if any."""
    found = careers(air_wing)
    return found[0] if found else None

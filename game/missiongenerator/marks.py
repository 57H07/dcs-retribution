"""Which ground objects get an F10 map marker (`Settings.generate_marks`).

By default every ground object of the theater is marked. With
`Settings.reduced_marks`, only those that matter for the turn keep theirs:
near a front line, aimed at by a blue package, at a base with an active front,
or the target of a campaign objective in progress.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from shapely.geometry import LineString, Point as ShapelyPoint

from game.objectives import aimed_at
from game.utils import nautical_miles

if TYPE_CHECKING:
    from game.game import Game
    from game.theater.theatergroundobject import TheaterGroundObject


class MarkFilter:
    def __init__(self, game: Game) -> None:
        self.game = game
        self.reduced = game.settings.reduced_marks
        self.range_m = nautical_miles(game.settings.reduced_marks_range_nm).meters
        self.fronts = [
            LineString([(p.x, p.y) for p in front.points])
            for front in game.theater.conflicts()
        ]
        self.package_targets = [p.target for p in game.blue.ato.packages]

    def marks(self, tgo: TheaterGroundObject) -> bool:
        if not self.reduced:
            return True
        cp = tgo.control_point
        return (
            cp.has_active_frontline
            or self._near_front(tgo)
            or any(target is tgo for target in self.package_targets)
            or bool(aimed_at(self.game, tgo.id))
            or bool(aimed_at(self.game, cp.id))
        )

    def _near_front(self, tgo: TheaterGroundObject) -> bool:
        where = ShapelyPoint(tgo.position.x, tgo.position.y)
        return any(front.distance(where) <= self.range_m for front in self.fronts)

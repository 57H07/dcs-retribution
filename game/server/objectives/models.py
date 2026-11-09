"""The campaign objectives as the API serves them (#194)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.objectives import ObjectiveState, expected_reward, progress, targets
from game.server.leaflet import LeafletPoint

if TYPE_CHECKING:
    from game import Game
    from game.objectives import CampaignObjective


class ObjectiveTargetJs(BaseModel):
    """A base or ground object of an objective, for the map."""

    id: UUID
    name: str
    position: LeafletPoint
    #: Still to destroy, capture or keep.
    remaining: bool

    class Config:
        title = "ObjectiveTarget"


class CampaignObjectiveJs(BaseModel):
    title: str
    #: "capture", "hold", "destroy" or "survive".
    kind: str
    target: str
    #: "In progress", "Met" or "Missed".
    state: str
    #: Capture and destroy: the last turn; hold and survive: the turn to reach.
    deadline: int | None
    #: Turns left before the deadline, this one included; in progress only.
    turns_left: int | None
    #: Destroy: targets destroyed out of the total.
    done: int | None
    total: int | None
    #: What the campaign promises, before the settings and the caps.
    reward: str
    #: In progress: what it would grant if met now, under the player's settings
    #: and the caps at today's income. Empty otherwise.
    expected: str
    #: What the reward actually gave, once met.
    granted: str
    resolved_turn: int | None
    #: The bases or ground objects it is about.
    targets: list[ObjectiveTargetJs]

    class Config:
        title = "CampaignObjective"

    @staticmethod
    def from_objective(objective: CampaignObjective, game: Game) -> CampaignObjectiveJs:
        state = progress(objective, game)
        return CampaignObjectiveJs(
            title=objective.title,
            kind=objective.kind.value,
            target=objective.target,
            state=objective.state.value,
            deadline=objective.deadline,
            turns_left=state.turns_left,
            done=state.done,
            total=state.total,
            reward=objective.reward.describe(),
            expected=(
                expected_reward(objective, game)
                if objective.state is ObjectiveState.IN_PROGRESS
                else ""
            ),
            granted=objective.granted,
            resolved_turn=objective.resolved_turn,
            targets=[
                ObjectiveTargetJs(
                    id=t.id,
                    name=t.name,
                    position=t.position.latlng(),
                    remaining=t.remaining,
                )
                for t in targets(objective, game)
            ],
        )


class ObjectivesSummaryJs(BaseModel):
    met: int
    missed: int
    total: int
    #: The objectives in progress, the nearest deadline first.
    in_progress: list[CampaignObjectiveJs]

    class Config:
        title = "ObjectivesSummary"

    @staticmethod
    def from_game(game: Game) -> ObjectivesSummaryJs | None:
        """None when the campaign has no objective."""
        objectives = game.objectives.objectives
        if not objectives:
            return None
        return ObjectivesSummaryJs(
            met=sum(o.state is ObjectiveState.MET for o in objectives),
            missed=sum(o.state is ObjectiveState.MISSED for o in objectives),
            total=len(objectives),
            in_progress=sorted(
                (
                    CampaignObjectiveJs.from_objective(o, game)
                    for o in objectives
                    if o.state is ObjectiveState.IN_PROGRESS
                ),
                key=lambda o: (o.turns_left is None, o.turns_left or 0),
            ),
        )


class CampaignObjectivesJs(BaseModel):
    turn: int
    objectives: list[CampaignObjectiveJs]

    class Config:
        title = "CampaignObjectives"

    @staticmethod
    def from_game(game: Game) -> CampaignObjectivesJs:
        return CampaignObjectivesJs(
            turn=game.turn,
            objectives=[
                CampaignObjectiveJs.from_objective(o, game)
                for o in game.objectives.objectives
            ],
        )

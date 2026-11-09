"""The campaign objectives as the API serves them (#194)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from game.objectives import ObjectiveState, progress

if TYPE_CHECKING:
    from game import Game
    from game.objectives import CampaignObjective


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
    #: What the campaign promises, before the caps.
    reward: str
    #: What the reward actually gave, once met.
    granted: str
    resolved_turn: int | None

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
            granted=objective.granted,
            resolved_turn=objective.resolved_turn,
        )


class ObjectivesSummaryJs(BaseModel):
    met: int
    missed: int
    total: int

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

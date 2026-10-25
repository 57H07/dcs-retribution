"""Airlift cargo delivery and loss rules (TRN-01.1, #28)."""

import uuid
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from dcs import Point

from game.debriefing import AirLosses, Debriefing, GroundLosses
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.sim.simulationresults import SimulationResults
from game.theater import Player
from game.transfers import AirliftPlanner, TransferOrder
from game.unitmap import FlyingUnit
from game.utils import nautical_miles


def _cp(name: str, x: float, captured: Player = Player.BLUE) -> Any:
    cp = MagicMock()
    cp.name = name
    cp.captured = captured
    cp.position = Point(x, 0, None)  # type: ignore[arg-type]
    cp.is_friendly.side_effect = lambda player: player == captured
    return cp


def _transfer(units: dict[Any, int]) -> TransferOrder:
    return TransferOrder(_cp("A", 0), _cp("B", 1000), dict(units))


def _empty_debriefing() -> Debriefing:
    debriefing = Debriefing.__new__(Debriefing)
    debriefing.air_losses = AirLosses(player=[], enemy=[])
    debriefing.ground_losses = GroundLosses()
    return debriefing


def _killed_flight(
    transfer: TransferOrder | None, pilots: int = 2
) -> SimulationResults:
    flight = SimpleNamespace(
        id=uuid.uuid4(),
        cargo=transfer,
        squadron=SimpleNamespace(player=Player.BLUE),
    )
    results = SimulationResults()
    for _ in range(pilots):
        results.air_losses.append(FlyingUnit(cast(Any, flight), MagicMock()))
    return results


def test_auto_resolved_shoot_down_loses_the_whole_cargo() -> None:
    tank, apc = MagicMock(name="tank"), MagicMock(name="apc")
    transfer = _transfer({tank: 2, apc: 1})
    debriefing = _empty_debriefing()

    # Two pilots of the same flight killed: the cargo must only be counted once.
    debriefing.merge_simulation_results(_killed_flight(transfer, pilots=2))

    assert len(debriefing.air_losses.player) == 2
    assert len(debriefing.ground_losses.player_airlifts) == 1
    MissionResultsProcessor.commit_airlift_losses(debriefing)
    assert transfer.size == 0


def test_auto_resolved_loss_without_cargo_has_no_airlift_loss() -> None:
    debriefing = _empty_debriefing()
    debriefing.merge_simulation_results(_killed_flight(None))
    assert debriefing.ground_losses.player_airlifts == []
    assert debriefing.ground_losses.enemy_airlifts == []


def test_helicopter_drop_off_leg_is_range_checked() -> None:
    origin = _cp("Origin", 0)
    far_destination = _cp("Far", nautical_miles(150).meters)
    origin.can_operate.return_value = True
    far_destination.can_operate.return_value = True
    transfer = TransferOrder(origin, far_destination, {MagicMock(): 1})

    planner = AirliftPlanner.__new__(AirliftPlanner)
    planner.transfer = transfer
    planner.next_stop = far_destination

    helo = MagicMock()
    helo.capable_of.return_value = True
    helo.dcs_unit_type.helicopter = True

    # Home base next to the pickup: only the pickup -> drop-off leg exceeds the
    # helicopter range, which used to be measured from the pickup to itself.
    assert not planner.compatible_with_mission(helo, origin)

    near_destination = _cp("Near", nautical_miles(50).meters)
    near_destination.can_operate.return_value = True
    planner.next_stop = near_destination
    assert planner.compatible_with_mission(helo, origin)

"""CSAR-01 gaps on planning and rescue: escorts, SAM avoidance, hoist at sea,
delivery-only AI rescues and front proximity (#65, #66, #67, #68, #71)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional, cast
from unittest.mock import MagicMock, patch

import pytest
from dcs.mapping import Point
from dcs.terrain import Terrain

from game.ato.flighttype import FlightType
from game.squadrons.csarservice import CsarService
from game.squadrons.downedpilot import DownedPilot
from game.squadrons.pilot import Pilot
from game.theater.player import Player
from game.utils import nautical_miles

_TERRAIN = MagicMock(spec=Terrain)
_NM = nautical_miles(1).meters


# ---------------------------------------------------------------------------
# #71: front proximity is measured to the whole front line
# ---------------------------------------------------------------------------


def _survival_game(front_points: list[Point]) -> Any:
    game = MagicMock()
    game.settings = SimpleNamespace(
        csar_survival_turns=3,
        csar_survival_turns_hostile=2,
    )
    game.theater.closest_control_point.return_value.is_friendly.return_value = True
    # The midpoint is far from the pilot; only the route passes close by.
    front = SimpleNamespace(
        position=Point(0.0, 500 * _NM, _TERRAIN), points=front_points
    )
    game.theater.conflicts.return_value = [front]
    return game


def test_pilot_near_one_end_of_a_long_front_gets_the_hostile_survival_time() -> None:
    game = _survival_game(
        [Point(0.0, 10 * _NM, _TERRAIN), Point(0.0, 200 * _NM, _TERRAIN)]
    )

    turns = CsarService(game)._survival_turns(Point(0.0, 0.0, _TERRAIN), Player.BLUE)

    assert turns == 2


def test_pilot_far_from_the_whole_front_gets_the_normal_survival_time() -> None:
    game = _survival_game(
        [Point(0.0, 100 * _NM, _TERRAIN), Point(0.0, 200 * _NM, _TERRAIN)]
    )

    turns = CsarService(game)._survival_turns(Point(0.0, 0.0, _TERRAIN), Player.BLUE)

    assert turns == 3


# ---------------------------------------------------------------------------
# #65: CAS escort for CSAR packages
# ---------------------------------------------------------------------------


def _downed_at(position: Point, player: Player = Player.BLUE) -> DownedPilot:
    squadron = MagicMock()
    squadron.coalition.downed_pilots = []
    squadron.coalition.game.settings.csar_single_flight = False
    downed = DownedPilot(
        pilot=Pilot("Rescuee"),
        squadron=squadron,
        _position=position,
        player=player,
        turn_downed=1,
        turns_remaining=3,
        was_player=False,
        aircraft_name="F/A-18C Hornet",
    )
    squadron.coalition.downed_pilots.append(downed)
    return downed


def _planning_state(
    target: DownedPilot,
    *,
    cas_escort: bool = True,
    front_lines: Optional[list[Any]] = None,
    armour: Optional[list[Point]] = None,
) -> Any:
    from game.commander.theaterstate import TheaterState

    state = TheaterState.__new__(TheaterState)
    state.csar_targets = [target]
    state.csar_flights_planned = 0
    state.enemy_air_defenses = []
    state.enemy_ships = []
    state.active_front_lines = front_lines or []
    battle_positions = SimpleNamespace(
        in_priority_order=[SimpleNamespace(position=p) for p in armour or []]
    )
    state.enemy_battle_positions = {MagicMock(): cast(Any, battle_positions)}
    state.context = cast(
        Any,
        SimpleNamespace(
            settings=SimpleNamespace(
                max_csar_flights=2,
                csar_cluster_radius=0,
                csar_cas_escort=cas_escort,
            )
        ),
    )
    return state


def _proposed_flights(task: Any, state: Any) -> list[Any]:
    """Runs the CSAR preconditions with the IADS check and fulfilment stubbed,
    then returns what the task proposes."""
    from game.commander.tasks.primitive.csar import PlanCsar

    with patch.object(
        PlanCsar, "target_area_preconditions_met", return_value=True
    ), patch(
        "game.commander.tasks.packageplanningtask.PackagePlanningTask"
        ".preconditions_met",
        return_value=True,
    ):
        assert task.preconditions_met(state)
    task.propose_flights()
    return list(task.flights)


def _front_line_through(*points: Point) -> Any:
    return SimpleNamespace(points=list(points))


def test_csar_package_near_the_front_proposes_a_cas_escort() -> None:
    from game.commander.missionproposals import EscortType
    from game.commander.tasks.primitive.csar import PlanCsar

    target = _downed_at(Point(0.0, 0.0, _TERRAIN))
    front = _front_line_through(
        Point(10 * _NM, -50 * _NM, _TERRAIN), Point(10 * _NM, 50 * _NM, _TERRAIN)
    )
    state = _planning_state(target, front_lines=[front])

    flights = _proposed_flights(PlanCsar(target), state)

    cas = [f for f in flights if f.task is FlightType.CAS]
    assert len(cas) == 1
    # An escort, so optional: pruned or skipped rather than scrubbing the rescue.
    assert cas[0].escort_type is EscortType.Ground
    # The rest of the package is unchanged.
    assert flights[0].task is FlightType.CSAR
    assert {f.task for f in flights} >= {FlightType.ESCORT, FlightType.SEAD_ESCORT}


def test_csar_package_near_enemy_armour_proposes_a_cas_escort() -> None:
    from game.commander.tasks.primitive.csar import PlanCsar

    target = _downed_at(Point(0.0, 0.0, _TERRAIN))
    state = _planning_state(target, armour=[Point(5 * _NM, 0.0, _TERRAIN)])

    flights = _proposed_flights(PlanCsar(target), state)

    assert FlightType.CAS in {f.task for f in flights}


def test_csar_package_far_from_ground_forces_has_no_cas_escort() -> None:
    from game.commander.tasks.primitive.csar import PlanCsar

    target = _downed_at(Point(0.0, 0.0, _TERRAIN))
    front = _front_line_through(
        Point(100 * _NM, -50 * _NM, _TERRAIN), Point(100 * _NM, 50 * _NM, _TERRAIN)
    )
    state = _planning_state(
        target, front_lines=[front], armour=[Point(80 * _NM, 0.0, _TERRAIN)]
    )

    flights = _proposed_flights(PlanCsar(target), state)

    assert FlightType.CAS not in {f.task for f in flights}


def test_cas_escort_needs_the_setting() -> None:
    from game.commander.tasks.primitive.csar import PlanCsar
    from game.settings import Settings

    assert Settings().csar_cas_escort is False
    target = _downed_at(Point(0.0, 0.0, _TERRAIN))
    front = _front_line_through(Point(0.0, 0.0, _TERRAIN), Point(0.0, _NM, _TERRAIN))
    state = _planning_state(target, cas_escort=False, front_lines=[front])

    flights = _proposed_flights(PlanCsar(target), state)

    assert FlightType.CAS not in {f.task for f in flights}


def test_downed_pilot_offers_cas_as_well_as_cap_and_escorts() -> None:
    downed = _downed_at(Point(0.0, 0.0, _TERRAIN))

    types = set(downed.mission_types(Player.BLUE))

    assert {
        FlightType.CSAR,
        FlightType.CAS,
        FlightType.TARCAP,
        FlightType.ESCORT,
        FlightType.SEAD_ESCORT,
    } <= types
    assert list(downed.mission_types(Player.RED)) == []


def test_cas_escort_covers_the_pickup() -> None:
    """A CAS flight against a downed pilot flies a short line across the
    approach, centred on the pilot, which is where its engagement zone goes."""
    from shapely.geometry import Point as ShapelyPoint

    from game.ato.flightplans import cas

    target = _downed_at(Point(0.0, 0.0, _TERRAIN))
    flight = MagicMock()
    flight.package.target = target
    flight.departure.position = Point(-50 * _NM, 0.0, _TERRAIN)
    flight.unit_type.dcs_unit_type.helicopter = False

    with patch.object(cas, "WaypointBuilder") as waypoint_builder, patch.object(
        cas, "IpSolver"
    ) as ip_solver, patch.object(cas, "waypoint_debug_directory"):
        ip_solver.return_value.solve.return_value = ShapelyPoint(-20 * _NM, 0.0)
        cas.Builder(flight).layout(dump_debug_info=False)

    ends = [c.args[0] for c in waypoint_builder.return_value.cas.call_args_list]
    assert len(ends) == 2
    start, end = ends
    midpoint = (start + end) / 2
    assert midpoint.distance_to_point(target.position) < 1
    assert start.distance_to_point(end) == pytest.approx(
        2 * cas.CSAR_COVER_HALF_LENGTH.meters
    )
    # Across the approach (which runs along x), not along it.
    assert abs(start.x - end.x) < 1


def test_csar_with_a_cas_escort_is_still_a_csar_package() -> None:
    from game.ato.package import Package

    package = Package.__new__(Package)
    package.flights = cast(
        Any,
        [
            SimpleNamespace(flight_type=FlightType.CAS),
            SimpleNamespace(flight_type=FlightType.CSAR),
        ],
    )

    assert package.primary_task is FlightType.CSAR


def _fulfiller_planning(escort_available: bool) -> Any:
    """Plans a CSAR mission with a CAS escort, the escort squadron existing but
    (unless escort_available) having no aircraft in range."""
    from game.commander.missionproposals import (
        EscortType,
        ProposedFlight,
        ProposedMission,
    )
    from game.commander.packagefulfiller import PackageFulfiller

    coalition = MagicMock()
    coalition.air_wing.can_auto_plan.return_value = True
    threats = coalition.opponent.threat_zone
    threats.waypoints_threatened_by_aircraft.return_value = False
    threats.waypoints_threatened_by_radar_sam.return_value = False
    settings = SimpleNamespace(
        auto_ato_player_missions_asap=False, default_start_type="Cold"
    )
    fulfiller = PackageFulfiller(
        coalition, MagicMock(), MagicMock(), cast(Any, settings)
    )

    builder = MagicMock()
    builder.package.flights = [MagicMock()]
    builder.plan_flight.side_effect = lambda proposed, *_args, **_kwargs: (
        proposed.task is FlightType.CSAR or escort_available
    )
    package = MagicMock()
    package.has_players = False
    builder.build.return_value = package

    mission = ProposedMission(
        MagicMock(),
        [
            ProposedFlight(FlightType.CSAR, 2),
            ProposedFlight(FlightType.CAS, 2, EscortType.Ground),
        ],
    )
    with patch(
        "game.commander.packagefulfiller.PackageBuilder", return_value=builder
    ), patch("game.commander.packagefulfiller.ObjectiveDistanceCache"):
        result = fulfiller.plan_mission(mission, 1, MagicMock(), MagicMock())
    return result, builder, coalition


def test_csar_is_planned_when_the_cas_escort_has_no_aircraft() -> None:
    result, builder, coalition = _fulfiller_planning(escort_available=False)

    assert result is not None
    builder.release_planned_aircraft.assert_not_called()
    # An optional escort is no reason to buy aircraft either.
    coalition.add_procurement_request.assert_not_called()


def test_cas_escort_is_planned_when_aircraft_are_available() -> None:
    result, builder, _ = _fulfiller_planning(escort_available=True)

    assert result is not None
    planned = [call.args[0].task for call in builder.plan_flight.call_args_list]
    assert planned == [FlightType.CSAR, FlightType.CAS]


# ---------------------------------------------------------------------------
# #66: the autoplanner keeps CSAR routes out of SAM zones
# ---------------------------------------------------------------------------


def _sam(x_nm: float, range_nm: float) -> Any:
    from game.data.groups import GroupTask

    sam = MagicMock()
    sam.position = Point(x_nm * _NM, 0.0, _TERRAIN)
    sam.task = GroupTask.MERAD
    sam.max_threat_range.return_value = nautical_miles(range_nm)
    sam.max_detection_range.return_value = nautical_miles(range_nm)
    sam.distance_to.side_effect = lambda target: sam.position.distance_to_point(
        target.position
    )
    return sam


def _sam_state(target: DownedPilot, sam: Any, aggressiveness: int = 0) -> Any:
    from shapely.geometry import Point as ShapelyPoint, Polygon

    from game.threatzones import ThreatZones

    state = _planning_state(target, cas_escort=False)
    state.enemy_air_defenses = [sam]
    state.threatening_air_defenses = []
    state.detecting_air_defenses = []
    ring = ShapelyPoint(sam.position.x, sam.position.y).buffer(
        sam.max_threat_range.return_value.meters
    )
    state.threat_zones = ThreatZones(MagicMock(), Polygon(), ring, ring)
    state.context.coalition = MagicMock()
    state.context.coalition.player = Player.BLUE
    state.context.coalition.game.settings = SimpleNamespace(
        ownfor_autoplanner_aggressiveness=aggressiveness,
        opfor_autoplanner_aggressiveness=aggressiveness,
    )
    return state


def _planned_package(*route_nm: tuple[float, float]) -> Any:
    """A CSAR package whose helicopters fly through these (x, y) points (nm)."""
    from game.ato.flightwaypointtype import FlightWaypointType

    waypoints = [
        SimpleNamespace(
            position=Point(x * _NM, y * _NM, _TERRAIN),
            waypoint_type=FlightWaypointType.NAV,
        )
        for x, y in route_nm
    ]
    # Not flown, so never a reason to cancel: right on top of the SAM.
    waypoints.append(
        SimpleNamespace(
            position=Point(50 * _NM, 0.0, _TERRAIN),
            waypoint_type=FlightWaypointType.BULLSEYE,
        )
    )
    flight = MagicMock()
    flight.flight_type = FlightType.CSAR
    flight.flight_plan.waypoints = waypoints
    package = MagicMock()
    package.flights = [flight]
    package.remove_flight.side_effect = package.flights.remove
    return package, flight


def _plan_with_route(task: Any, state: Any, package: Any) -> bool:
    from game.commander.tasks.packageplanningtask import PackagePlanningTask

    def fulfil(self: Any, _state: Any) -> bool:
        self.package = package
        return True

    with patch.object(PackagePlanningTask, "preconditions_met", fulfil):
        return bool(task.preconditions_met(state))


def test_csar_route_through_a_sam_ring_is_not_planned() -> None:
    from game.commander.tasks.primitive.csar import PlanCsar

    target = _downed_at(Point(100 * _NM, 0.0, _TERRAIN))
    sam = _sam(50, 10)
    state = _sam_state(target, sam)
    package, flight = _planned_package((0, 0), (100, 0), (0, 0))
    task = PlanCsar(target)

    assert not _plan_with_route(task, state, package)

    # Aircraft go back to the inventory...
    package.remove_flight.assert_called_once_with(flight)
    assert task.package is None
    # ...the pilot stays on the board for a later turn...
    assert target in state.csar_targets
    assert state.csar_flights_planned == 0
    # ...and the SAM in the way is a threat worth clearing.
    assert sam in state.threatening_air_defenses


def test_csar_route_around_a_sam_ring_is_planned() -> None:
    from game.commander.tasks.primitive.csar import PlanCsar

    target = _downed_at(Point(100 * _NM, 0.0, _TERRAIN))
    state = _sam_state(target, _sam(50, 10))
    # Detour 30 nm north of the SAM, out and back.
    package, _ = _planned_package((0, 0), (50, 30), (100, 0), (50, 30), (0, 0))

    assert _plan_with_route(PlanCsar(target), state, package)


def test_pilot_inside_a_sam_ring_gets_no_csar_even_at_full_aggressiveness() -> None:
    from game.commander.tasks.primitive.csar import PlanCsar

    target = _downed_at(Point(52 * _NM, 0.0, _TERRAIN))
    sam = _sam(50, 10)
    state = _sam_state(target, sam, aggressiveness=100)
    package, _ = _planned_package((0, 0), (52, 0), (0, 0))

    assert not _plan_with_route(PlanCsar(target), state, package)
    assert target in state.csar_targets
    assert sam in state.threatening_air_defenses

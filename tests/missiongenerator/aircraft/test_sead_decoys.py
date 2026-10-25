"""BUG-01: SEAD decoys (TALD) are released at the decoy release point."""

from typing import Any
from unittest.mock import MagicMock

from dcs.task import AttackGroup, Expend, WeaponType as DcsWeaponType

from game.data.weapons import WeaponType
from game.missiongenerator.aircraft.waypoints.decoyrelease import (
    DecoyReleaseBuilder,
)
from game.missiongenerator.aircraft.waypoints.seadingress import SeadIngressBuilder
from game.theater import TheaterGroundObject


def _builder(cls: type, carries_decoys: bool) -> tuple[Any, Any]:
    # Bypass __init__ (it needs a full mission/flight); only add_tasks() and the
    # collaborators it consults are exercised.
    group = MagicMock()
    group.group_name = "sam-group"
    target = MagicMock(spec=TheaterGroundObject)
    target.groups = [group]
    target.position = MagicMock()
    target.position.heading_between_point.return_value = 90.0

    miz_group = MagicMock()
    miz_group.id = 7

    builder: Any = object.__new__(cls)
    builder.register_special_strike_points = MagicMock()
    builder.register_special_ingress_points = MagicMock()
    builder.waypoint = MagicMock()
    builder.package = MagicMock()
    builder.package.target = target
    builder.flight = MagicMock()
    builder.flight.any_member_has_weapon_of_type.side_effect = (
        lambda weapon_type: carries_decoys and weapon_type is WeaponType.DECOY
    )
    builder.mission = MagicMock()
    builder.mission.find_group.return_value = miz_group

    waypoint = MagicMock()
    waypoint.tasks = []
    waypoint.alt = 6000
    return builder, waypoint


def _attacks_with(tasks: list[Any], weapon_type: DcsWeaponType) -> list[AttackGroup]:
    return [
        t
        for t in tasks
        if isinstance(t, AttackGroup) and t.params["weaponType"] == weapon_type.value
    ]


def test_ingress_never_releases_decoys() -> None:
    builder, waypoint = _builder(SeadIngressBuilder, carries_decoys=True)

    builder.add_tasks(waypoint)

    assert not _attacks_with(waypoint.tasks, DcsWeaponType.Decoy)


def test_ingress_keeps_arm_task_expending_all() -> None:
    builder, waypoint = _builder(SeadIngressBuilder, carries_decoys=True)

    builder.add_tasks(waypoint)

    arm_tasks = _attacks_with(waypoint.tasks, DcsWeaponType.ARM)
    assert len(arm_tasks) == 1
    assert arm_tasks[0].params["expend"] == Expend.All.value
    assert arm_tasks[0].params["groupId"] == 7


def test_release_point_releases_decoys_with_climb() -> None:
    builder, waypoint = _builder(DecoyReleaseBuilder, carries_decoys=True)

    builder.add_tasks(waypoint)

    decoy_tasks = _attacks_with(waypoint.tasks, DcsWeaponType.Decoy)
    assert len(decoy_tasks) == 1
    assert decoy_tasks[0].params["groupId"] == 7
    assert decoy_tasks[0].params["expend"] == Expend.All.value
    assert decoy_tasks[0].params["altitude"] == 9000


def test_flight_without_decoys_gets_no_decoy_task() -> None:
    builder, waypoint = _builder(DecoyReleaseBuilder, carries_decoys=False)

    builder.add_tasks(waypoint)

    assert waypoint.tasks == []

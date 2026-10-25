"""BUG-01: SEAD flights carrying decoys get a DECOY RELEASE waypoint."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.flightplans.formationattack import FormationAttackLayout
from game.ato.flightplans.sead import Builder as SeadBuilder
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.data.weapons import WeaponType
from game.settings import Settings
from game.utils import nautical_miles

TERRAIN = Caucasus()


def _point(x: float, y: float = 0) -> Point:
    return Point(x, y, TERRAIN)


def _wpt(name: str, kind: FlightWaypointType, position: Point) -> FlightWaypoint:
    return FlightWaypoint(name, kind, position)


def test_default_release_distance_is_15_nm() -> None:
    assert Settings().sead_decoy_release_distance == 15


def test_release_point_at_configured_distance_towards_ingress() -> None:
    target = _point(0)
    ingress = _point(nautical_miles(40).meters)

    release = WaypointBuilder.decoy_release_point(target, ingress, nautical_miles(15))

    assert release.distance_to_point(target) == pytest.approx(
        nautical_miles(15).meters, rel=1e-6
    )
    assert release.distance_to_point(ingress) == pytest.approx(
        nautical_miles(25).meters, rel=1e-6
    )


def test_release_point_never_beyond_ingress() -> None:
    target = _point(0)
    ingress = _point(nautical_miles(10).meters)

    release = WaypointBuilder.decoy_release_point(target, ingress, nautical_miles(15))

    assert release.distance_to_point(target) < ingress.distance_to_point(target)


def _sead_builder(carries_decoys: bool) -> Any:
    builder: Any = object.__new__(SeadBuilder)
    flight = MagicMock()
    flight.is_helo = False
    flight.flight_type = FlightType.SEAD
    flight.any_member_has_weapon_of_type.side_effect = (
        lambda weapon_type: carries_decoys and weapon_type is WeaponType.DECOY
    )
    builder.flight = flight
    builder._hold_point = MagicMock()
    builder._get_split = MagicMock()
    builder._build_refuel = MagicMock(return_value=None)
    return builder


@patch("game.ato.flightplans.formationattack.WaypointBuilder")
def test_flight_with_decoys_gets_release_waypoint(waypoint_builder: Any) -> None:
    builder = _sead_builder(carries_decoys=True)

    layout = builder.layout()

    wb = waypoint_builder.return_value
    wb.decoy_release.assert_called_once_with(builder.flight.package.target)
    assert layout.decoy_release is wb.decoy_release.return_value


@patch("game.ato.flightplans.formationattack.WaypointBuilder")
def test_flight_without_decoys_gets_no_release_waypoint(
    waypoint_builder: Any,
) -> None:
    builder = _sead_builder(carries_decoys=False)

    layout = builder.layout()

    waypoint_builder.return_value.decoy_release.assert_not_called()
    assert layout.decoy_release is None


def _layout(initial_nm: float, release_nm: float | None) -> FormationAttackLayout:
    def at(nm: float) -> Point:
        return _point(nautical_miles(nm).meters)

    return FormationAttackLayout(
        departure=_wpt("TAKEOFF", FlightWaypointType.TAKEOFF, at(100)),
        hold=None,
        nav_to=[],
        join=_wpt("JOIN", FlightWaypointType.JOIN, at(60)),
        split=_wpt("SPLIT", FlightWaypointType.SPLIT, at(60)),
        refuel=None,
        nav_from=[],
        arrival=_wpt("LAND", FlightWaypointType.LANDING_POINT, at(100)),
        divert=None,
        bullseye=_wpt("BULLSEYE", FlightWaypointType.BULLSEYE, at(0)),
        custom_waypoints=[],
        ingress=_wpt("INGRESS", FlightWaypointType.INGRESS_SEAD, at(40)),
        targets=[_wpt("TARGET", FlightWaypointType.TARGET_GROUP_LOC, at(0))],
        initial=_wpt("SEAD Search", FlightWaypointType.NAV, at(initial_nm)),
        decoy_release=(
            None
            if release_nm is None
            else _wpt("DECOY RELEASE", FlightWaypointType.DECOY_RELEASE, at(release_nm))
        ),
    )


def _names(layout: FormationAttackLayout) -> list[str]:
    return [w.name for w in layout.iter_waypoints()]


@pytest.mark.parametrize(
    "initial_nm,release_nm,expected",
    [
        (10, 15, ["INGRESS", "DECOY RELEASE", "SEAD Search", "TARGET"]),
        (30, 15, ["INGRESS", "SEAD Search", "DECOY RELEASE", "TARGET"]),
    ],
)
def test_release_waypoint_between_ingress_and_target(
    initial_nm: float, release_nm: float, expected: list[str]
) -> None:
    names = _names(_layout(initial_nm, release_nm))

    start = names.index("INGRESS")
    assert names[start : start + 4] == expected


def test_layout_without_decoys_has_no_release_waypoint() -> None:
    layout = _layout(10, None)

    assert all(
        w.waypoint_type is not FlightWaypointType.DECOY_RELEASE
        for w in layout.iter_waypoints()
    )

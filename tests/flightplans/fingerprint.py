"""Stable, human-readable fingerprint of planned flight plans (W16).

Only what the player sees and what mission generation consumes is kept:
waypoints (type, name, position, altitude, times), the package TOT, each
flight's startup/takeoff/landing times and the loadout of every pylon of every
member. Random identifiers (UUIDs, pilot ids) are left out.

Positions are rounded to the meter, altitudes to the foot and times to the
second so the reference does not churn on float noise.
"""

from __future__ import annotations

import difflib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from game.ato import Flight, FlightWaypoint, Package

REFERENCE_DIR = Path(__file__).resolve().parents[1] / "data" / "flightplans"

#: Set to ``1`` to rewrite the stored references instead of comparing.
UPDATE_ENV_VAR = "UPDATE_FLIGHTPLAN_FINGERPRINTS"


def _time(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat(timespec="seconds")


def _waypoint(flight: Flight, waypoint: FlightWaypoint) -> dict[str, Any]:
    plan = flight.flight_plan
    return {
        "type": waypoint.waypoint_type.name,
        "name": waypoint.name,
        "x": round(waypoint.position.x),
        "y": round(waypoint.position.y),
        "alt_ft": round(waypoint.alt.feet),
        "alt_type": waypoint.alt_type,
        "tot": _time(plan.tot_for_waypoint(waypoint)),
        "depart": _time(plan.depart_time_for_waypoint(waypoint)),
    }


def _loadouts(flight: Flight) -> list[dict[str, Any]]:
    loadouts = []
    for member in flight.iter_members():
        loadout = member.loadout
        loadouts.append(
            {
                "name": loadout.name,
                "pylons": {
                    str(pylon): None if weapon is None else weapon.clsid
                    for pylon, weapon in sorted(loadout.pylons.items())
                },
            }
        )
    return loadouts


def _flight(flight: Flight) -> dict[str, Any]:
    plan = flight.flight_plan
    return {
        "task": flight.flight_type.value,
        "aircraft": flight.unit_type.display_name,
        "squadron": flight.squadron.name,
        "departure": flight.departure.name,
        "arrival": flight.arrival.name,
        "divert": None if flight.divert is None else flight.divert.name,
        "count": flight.count,
        "start_type": flight.start_type.value,
        "flight_plan": type(plan).__name__,
        "startup": _time(plan.startup_time()),
        "takeoff": _time(plan.takeoff_time()),
        "tot": _time(plan.tot),
        "landing": _time(plan.landing_time),
        "waypoints": [_waypoint(flight, w) for w in plan.waypoints],
        "loadouts": _loadouts(flight),
    }


def fingerprint_package(package: Package) -> dict[str, Any]:
    return {
        "target": package.target.name,
        "target_type": type(package.target).__name__,
        "primary_task": (
            None if package.primary_task is None else package.primary_task.value
        ),
        "auto_asap": package.auto_asap,
        "tot": _time(package.time_over_target),
        "flights": [_flight(f) for f in package.flights],
    }


def to_json(fingerprint: dict[str, Any]) -> str:
    return json.dumps(fingerprint, indent=2, ensure_ascii=False) + "\n"


def reference_path(scenario: str) -> Path:
    return REFERENCE_DIR / f"{scenario}.json"


def update_requested() -> bool:
    return os.environ.get(UPDATE_ENV_VAR, "") not in ("", "0")


def compare_to_reference(scenario: str, fingerprint: dict[str, Any]) -> Optional[str]:
    """Compares against the stored reference, or rewrites it on request.

    Returns None when they match (or after an update), else a unified diff.
    """
    path = reference_path(scenario)
    actual = to_json(fingerprint)
    if update_requested():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8", newline="\n")
        return None
    if not path.exists():
        return (
            f"No reference fingerprint at {path}. Run the test with "
            f"{UPDATE_ENV_VAR}=1 to create it."
        )
    expected = path.read_text(encoding="utf-8")
    if expected == actual:
        return None
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=f"reference/{path.name}",
            tofile=f"actual/{path.name}",
        )
    )
    return (
        f"Flight plans of scenario '{scenario}' changed. If the change is "
        f"intended, refresh the reference with {UPDATE_ENV_VAR}=1 and review the "
        f"JSON diff in the PR.\n{diff}"
    )

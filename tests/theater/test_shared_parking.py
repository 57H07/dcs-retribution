"""Regression tests: fixed wing and helicopter parking share one pool.

Helicopters and VTOL aircraft count every slot of a base, fixed wing aircraft
only the fixed wing ones. Turn 0 fill and deliveries used to count the fixed
wing pool alone, overfilling the base, and loading the save then trimmed the
helicopter/VTOL squadrons without a word (AV-8B 8 -> 0 at Incirlik).
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from game.migrator import Migrator
from game.theater import ParkingType
from game.theater.controlpoint import ControlPoint

FIXED_WING_ONLY = ParkingType(fixed_wing=True)
FIXED_WING_STOL = ParkingType(fixed_wing=True, fixed_wing_stol=True)
ALL_TYPES = ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)


class _Base:
    """A base with 10 fixed wing slots, 2 ground spawns and 2 helipads."""

    def __init__(self, fixed_wing: int, rotary_wing: int) -> None:
        self.fixed_wing = fixed_wing
        self.rotary_wing = rotary_wing

    def unclaimed_parking(self, parking_type: ParkingType) -> int:
        return ControlPoint.unclaimed_parking(cast(ControlPoint, self), parking_type)

    def _unclaimed_parking_in(self, parking_type: ParkingType) -> int:
        return ControlPoint._unclaimed_parking_in(
            cast(ControlPoint, self), parking_type
        )

    def total_aircraft_parking(self, parking_type: ParkingType) -> int:
        total = 10
        if parking_type.include_fixed_wing_stol:
            total += 2
        if parking_type.include_rotary_wing:
            total += 2
        return total

    def allocated_aircraft(self, parking_type: ParkingType) -> Any:
        total = self.fixed_wing
        if parking_type.include_rotary_wing:
            total += self.rotary_wing
        return SimpleNamespace(total=total)


def test_fixed_wing_room_leaves_the_slots_helicopters_use() -> None:
    # 6 jets + 7 helicopters: 1 of the 14 slots left in all.
    base = _Base(fixed_wing=6, rotary_wing=7)
    assert base.unclaimed_parking(ALL_TYPES) == 1
    # The fixed wing pool alone has 4 (or 6) free slots, but filling them
    # would overfill the base.
    assert base.unclaimed_parking(FIXED_WING_ONLY) == 1
    assert base.unclaimed_parking(FIXED_WING_STOL) == 1


def test_fixed_wing_room_is_still_capped_by_fixed_wing_slots() -> None:
    base = _Base(fixed_wing=9, rotary_wing=0)
    assert base.unclaimed_parking(FIXED_WING_ONLY) == 1
    assert base.unclaimed_parking(FIXED_WING_STOL) == 3
    assert base.unclaimed_parking(ALL_TYPES) == 5


def test_filling_jets_then_helicopters_never_overfills() -> None:
    base = _Base(fixed_wing=0, rotary_wing=0)
    base.fixed_wing = base.unclaimed_parking(FIXED_WING_STOL)
    base.rotary_wing = base.unclaimed_parking(ALL_TYPES)
    assert base.fixed_wing + base.rotary_wing == 14
    # And in the other order, which used to let the jets take helipad room.
    base = _Base(fixed_wing=0, rotary_wing=0)
    base.rotary_wing = 8
    base.fixed_wing = base.unclaimed_parking(FIXED_WING_STOL)
    assert base.fixed_wing + base.rotary_wing == 14
    assert base.unclaimed_parking(ALL_TYPES) == 0


def _squadron(owned: int, cp: MagicMock) -> MagicMock:
    s = MagicMock()
    s.owned_aircraft = owned
    s.location = cp
    s.aircraft.task_priorities = {"CAS": 1}
    s.aircraft.helicopter = True
    s.coalition.game.settings.ground_start_ai_planes = False
    return s


def _migrate_squadrons(cp: MagicMock) -> None:
    m = Migrator.__new__(Migrator)
    m.game = MagicMock()
    m.game.theater.controlpoints = [cp]
    m.game.coalitions = []
    m.is_liberation = False
    m._update_squadrons()


def test_loading_an_overfilled_base_keeps_its_aircraft(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cp = MagicMock()
    cp.__str__.return_value = "Incirlik"  # type: ignore[attr-defined]
    cp.unclaimed_parking.return_value = -13
    harriers, apaches = _squadron(8, cp), _squadron(6, cp)
    cp.squadrons = [harriers, apaches]

    with caplog.at_level(logging.WARNING):
        _migrate_squadrons(cp)

    assert harriers.owned_aircraft == 8
    assert apaches.owned_aircraft == 6
    assert "Incirlik holds 13 more aircraft" in caplog.text


def test_loading_resets_a_negative_aircraft_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cp = MagicMock()
    cp.unclaimed_parking.return_value = 5
    corrupted = _squadron(-2, cp)
    cp.squadrons = [corrupted]

    with caplog.at_level(logging.WARNING):
        _migrate_squadrons(cp)

    assert corrupted.owned_aircraft == 0
    assert "reset to 0" in caplog.text

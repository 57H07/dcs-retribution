"""Regression tests for BUG-05: duplicate pilots after squadron transfers.

Repeatedly planning, changing and cancelling a squadron transfer must leave
every pilot and every aircraft accounted for exactly once: either free in the
squadron, or assigned to exactly one flight.
"""

from __future__ import annotations

import copy
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from dcs.planes import AJS37
from dcs.terrain.caucasus import Caucasus

from game import persistency
from game.ato.airtaaskingorder import AirTaskingOrder
from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.ato.starttype import StartType
from game.db.database import Database
from game.dcs.aircrafttype import AircraftType
from game.dcs.countries import country_with_name
from game.settings import Settings
from game.squadrons import Pilot, Squadron
from game.squadrons.operatingbases import OperatingBases
from game.squadrons.transferparking import transfer_parking
from game.theater.player import Player

NOW = datetime(2026, 1, 1, 12)


def _control_point(name: str) -> MagicMock:
    cp = MagicMock(name=name)
    cp.name = name
    cp.is_friendly.return_value = True
    cp.can_operate.return_value = True
    cp.unclaimed_parking.return_value = 100
    cp.required_aircraft_start_type = None
    cp.is_fleet = False
    return cp


@pytest.fixture(autouse=True)
def _no_flight_plans(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Default loadouts read the saved-games folder; point it at a throwaway dir.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16884)
    # Routing is irrelevant to pilot/aircraft bookkeeping and needs a theater.
    monkeypatch.setattr(Flight, "recreate_flight_plan", lambda self: None)
    monkeypatch.setattr(Package, "set_tot_asap", lambda self, now: None)


@pytest.fixture
def home() -> MagicMock:
    return _control_point("Home")


@pytest.fixture
def squadron(home: MagicMock) -> Squadron:
    settings = Settings()
    settings.enable_squadron_pilot_limits = True
    settings.squadron_pilot_limit = 12
    coalition = MagicMock()
    coalition.player = Player.BLUE
    coalition.ato = AirTaskingOrder()
    coalition.game.settings = settings
    coalition.faction.locales = None
    aircraft = next(AircraftType.for_dcs_type(AJS37))
    squadron = Squadron(
        name="test",
        nickname=None,
        country=country_with_name("Sweden"),
        role="test",
        aircraft=aircraft,
        max_size=16,
        livery=None,
        livery_set=[],
        primary_task=FlightType.STRIKE,
        auto_assignable_mission_types=set(aircraft.iter_task_capabilities()),
        radio_presets={},
        operating_bases=OperatingBases.default_for_aircraft(aircraft),
        female_pilot_percentage=0,
        pilot_pool=[],
        coalition=coalition,
        flight_db=Database(),
        settings=settings,
        location=home,
    )
    squadron.populate_for_turn_0(squadrons_start_full=False)
    squadron.owned_aircraft = 6
    squadron.untasked_aircraft = 6
    return squadron


def _flights(squadron: Squadron) -> Iterator[Flight]:
    for package in squadron.coalition.ato.packages:
        for flight in package.flights:
            if flight.squadron == squadron:
                yield flight


def _assert_consistent(squadron: Squadron) -> None:
    flights = list(_flights(squadron))
    assigned = [p for f in flights for p in f.roster.iter_pilots() if p is not None]
    everyone: list[Pilot] = squadron.available_pilots + assigned
    duplicates = [p for p, n in Counter(map(id, everyone)).items() if n > 1]
    assert not duplicates, "a pilot is free or assigned more than once"
    assert len(everyone) == len(squadron.active_pilots)
    assert squadron.untasked_aircraft + sum(f.count for f in flights) == (
        squadron.owned_aircraft
    )


def _ferry_destinations(squadron: Squadron) -> list[Any]:
    return [
        f.package.target
        for f in _flights(squadron)
        if f.flight_type is FlightType.FERRY
    ]


def test_repeated_transfers_keep_pilots_and_aircraft_unique(
    squadron: Squadron, home: MagicMock
) -> None:
    alpha, bravo = _control_point("Alpha"), _control_point("Bravo")
    for destination in [alpha, bravo, alpha, bravo, alpha]:
        squadron.plan_relocation(destination, NOW)
        _assert_consistent(squadron)
        assert set(_ferry_destinations(squadron)) == {destination}
        squadron.cancel_relocation()
        _assert_consistent(squadron)
        assert _ferry_destinations(squadron) == []
        squadron.plan_relocation(destination, NOW)
    _assert_consistent(squadron)


def test_retargeting_a_transfer_drops_every_stale_ferry_flight(
    squadron: Squadron,
) -> None:
    """An empty package ahead of the ferry package (e.g. one whose flights the
    player deleted by hand) made ``cancel_ferry_flights`` skip the ferry package,
    because it removed packages from the list it was iterating."""
    alpha, bravo = _control_point("Alpha"), _control_point("Bravo")
    ato = squadron.coalition.ato
    squadron.plan_relocation(alpha, NOW)
    ato.packages.insert(0, Package(_control_point("Empty"), squadron.flight_db))
    squadron.plan_relocation(bravo, NOW)
    assert set(_ferry_destinations(squadron)) == {bravo}
    _assert_consistent(squadron)


def test_skipped_flight_is_not_returned_twice(squadron: Squadron) -> None:
    """Mission generation returns the crew of a flight it cannot spawn (runway
    out of service) but leaves the flight in its package. If generation is then
    retried, or the flight deleted, its pilots and aircraft were returned a
    second time: duplicated pilots and an inflated aircraft count."""
    squadron.plan_relocation(_control_point("Alpha"), NOW)
    flight = next(_flights(squadron))
    flight.return_pilots_and_aircraft()
    flight.return_pilots_and_aircraft()
    flight.package.remove_flight(flight)
    _assert_consistent(squadron)


def test_returning_a_free_pilot_does_not_duplicate_it(squadron: Squadron) -> None:
    pilot = squadron.available_pilots[0]
    squadron.return_pilot(pilot)
    squadron.return_pilots([pilot])
    assert squadron.available_pilots.count(pilot) == 1


class _SameNameFaker:
    """Returns ``repeats`` copies of one name before moving on to fresh ones."""

    def __init__(self, repeats: int) -> None:
        self.repeats = repeats
        self.calls = 0

    def name_male(self) -> str:
        self.calls += 1
        return "Ulf Johansson" if self.calls <= self.repeats else f"Pilot {self.calls}"

    name_female = name_male


def test_recruits_never_share_a_name_with_squadron_mates(
    squadron: Squadron, monkeypatch: pytest.MonkeyPatch
) -> None:
    faker = _SameNameFaker(repeats=5)
    monkeypatch.setattr(Squadron, "faker", property(lambda self: faker))
    squadron.current_roster.clear()
    squadron.available_pilots.clear()
    squadron._recruit_pilots(3)
    names = [p.name for p in squadron.current_roster]
    assert len(names) == 3
    assert len(set(names)) == 3


def _airfield(squadron: Squadron, others: list[Squadron]) -> MagicMock:
    cp = _control_point("Batumi")
    cp.dcs_airport = Caucasus().airports["Batumi"]  # 10 slots for an AJS37
    cp.total_aircraft_parking.return_value = 0  # no helipads / ground spawns
    cp.squadrons = []
    cp.coalition.air_wing.iter_squadrons.side_effect = lambda: iter([squadron, *others])
    cp.coalition.game.settings = squadron.settings
    return cp


def _twin(squadron: Squadron) -> Squadron:
    twin = copy.copy(squadron)
    twin.id = uuid4()
    return twin


def test_room_shown_for_a_planned_transfer_ignores_the_squadron_itself(
    squadron: Squadron,
) -> None:
    """Reopening the dialog of a squadron already transferring to a base used
    to count its own aircraft against it: the transfer looked impossible."""
    other = _twin(squadron)
    batumi = _airfield(squadron, [other])
    assert transfer_parking(squadron, batumi).room == 10
    squadron.plan_relocation(batumi, NOW)
    assert transfer_parking(squadron, batumi).room == 10
    other.destination = batumi
    # The other squadron's 6 aircraft are taken; ours are not counted.
    assert transfer_parking(squadron, batumi).room == 4
    assert transfer_parking(other, batumi).room == 4


def test_room_at_a_base_without_dcs_airport_ignores_the_squadron_itself(
    squadron: Squadron,
) -> None:
    farp = _control_point("FARP")
    farp.dcs_airport = None
    farp.coalition.game.settings = squadron.settings
    farp.squadrons = []
    farp.coalition.air_wing.iter_squadrons.side_effect = lambda: iter([squadron])
    farp.unclaimed_parking.return_value = 10
    assert transfer_parking(squadron, farp).room == 10
    squadron.plan_relocation(farp, NOW)
    # unclaimed_parking() would now count the squadron's own 6 aircraft.
    farp.unclaimed_parking.return_value = 4
    assert transfer_parking(squadron, farp).room == 10

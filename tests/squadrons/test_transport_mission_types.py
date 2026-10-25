"""TRN-01.6: squadron ``mission_types`` are respected, including Transport."""

from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import yaml

from game.ato.flighttype import FlightType
from game.campaignloader.campaignairwingconfig import SquadronConfig
from game.campaignloader.defaultsquadronassigner import (
    DefaultSquadronAssigner,
    campaign_auto_assignable_mission_types,
)
from game.dcs.aircrafttype import AircraftType
from game.squadrons.airwing import AirWing
from game.squadrons.squadron import Squadron
from game.squadrons.squadrondef import SquadronDef

SQUADRONS_DIR = Path(__file__).parents[2] / "resources" / "squadrons"


def _transport_aircraft() -> AircraftType:
    """A transport-capable airframe that can also fly another task (e.g. UH-1H)."""
    for aircraft in AircraftType.priority_list_for_task(FlightType.TRANSPORT):
        if len(set(aircraft.iter_task_capabilities())) > 1:
            return aircraft
    raise AssertionError("no multi-role transport airframe")


def _squadron_def(
    tmp_path: Path, aircraft: AircraftType, mission_types: Optional[list[str]]
) -> SquadronDef:
    data: dict[str, object] = {
        "name": "Test Sqn",
        "country": "USA",
        "role": "test",
        "aircraft": aircraft.variant_id,
    }
    if mission_types is not None:
        data["mission_types"] = mission_types
    path = tmp_path / "sqn.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return SquadronDef.from_yaml(path)


def _non_transport_mission(aircraft: AircraftType) -> FlightType:
    other = next(
        (t for t in aircraft.iter_task_capabilities() if t is not FlightType.TRANSPORT),
        None,
    )
    assert other is not None, "test needs a transport airframe with another task"
    return other


def _squadron(aircraft: AircraftType, auto_set: set[FlightType]) -> Squadron:
    sqn: Squadron = object.__new__(Squadron)
    sqn.aircraft = aircraft
    sqn.auto_assignable_mission_types = set(auto_set)
    sqn.location = MagicMock()
    return sqn


def test_def_without_transport_cannot_be_auto_assigned_transport(
    tmp_path: Path,
) -> None:
    aircraft = _transport_aircraft()
    other = _non_transport_mission(aircraft)
    sqn_def = _squadron_def(tmp_path, aircraft, [other.value])
    assert sqn_def.capable_of(FlightType.TRANSPORT)
    assert not sqn_def.can_auto_assign(FlightType.TRANSPORT)


def test_def_with_transport_can_be_auto_assigned_transport(tmp_path: Path) -> None:
    aircraft = _transport_aircraft()
    sqn_def = _squadron_def(tmp_path, aircraft, [FlightType.TRANSPORT.value])
    assert sqn_def.can_auto_assign(FlightType.TRANSPORT)


def test_squadron_without_transport_not_offered_for_transport_flight() -> None:
    # AirliftPlanner picks squadrons through AirWing.auto_assignable_for_task_at.
    aircraft = _transport_aircraft()
    other = _non_transport_mission(aircraft)
    without = _squadron(aircraft, {other})
    with_transport = _squadron(aircraft, {FlightType.TRANSPORT})
    with_transport.location = without.location

    air_wing: AirWing = object.__new__(AirWing)
    air_wing.squadrons = {aircraft: [without, with_transport]}

    offered = list(
        air_wing.auto_assignable_for_task_at(FlightType.TRANSPORT, without.location)
    )
    assert offered == [with_transport]


def test_campaign_secondaries_are_limited_by_squadron_mission_types(
    tmp_path: Path,
) -> None:
    aircraft = _transport_aircraft()
    other = _non_transport_mission(aircraft)
    sqn_def = _squadron_def(tmp_path, aircraft, [other.value])
    config = SquadronConfig(
        primary=other,
        secondary=list(FlightType),  # `secondary: any`
        aircraft=[],
        max_size=4,
        name=None,
        nickname=None,
        female_pilot_percentage=None,
        aircraft_type=None,
    )
    auto = campaign_auto_assignable_mission_types(sqn_def, config)
    assert FlightType.TRANSPORT not in auto
    assert other in auto


def test_campaign_primary_is_kept_even_if_not_in_mission_types(
    tmp_path: Path,
) -> None:
    # A campaign that explicitly names a squadron for a primary task wins.
    aircraft = _transport_aircraft()
    other = _non_transport_mission(aircraft)
    sqn_def = _squadron_def(tmp_path, aircraft, [other.value])
    config = SquadronConfig(
        primary=FlightType.TRANSPORT,
        secondary=[],
        aircraft=[],
        max_size=4,
        name=None,
        nickname=None,
        female_pilot_percentage=None,
        aircraft_type=None,
    )
    assert campaign_auto_assignable_mission_types(sqn_def, config) == {
        FlightType.TRANSPORT
    }


def test_random_squadron_selection_requires_primary_in_mission_types(
    tmp_path: Path,
) -> None:
    aircraft = _transport_aircraft()
    other = _non_transport_mission(aircraft)
    sqn_def = _squadron_def(tmp_path, aircraft, [other.value])
    control_point = MagicMock()
    control_point.can_operate.return_value = True
    sqn_def.operating_bases = MagicMock(shore=True, carrier=True, lha=True)

    assert not DefaultSquadronAssigner.squadron_compatible_with(
        sqn_def, FlightType.TRANSPORT, control_point
    )
    assert DefaultSquadronAssigner.squadron_compatible_with(
        sqn_def, other, control_point
    )
    # Explicitly named squadrons ignore the restriction (campaign author's choice).
    assert DefaultSquadronAssigner.squadron_compatible_with(
        sqn_def, FlightType.TRANSPORT, control_point, ignore_base_preference=True
    )


def test_all_shipped_squadron_definitions_load() -> None:
    # The parser now rejects unknown mission types: every shipped file must be valid.
    paths = sorted(SQUADRONS_DIR.glob("*/*.yaml"))
    assert paths
    for path in paths:
        sqn_def = SquadronDef.from_yaml(path)
        assert sqn_def.auto_assignable_mission_types <= set(
            sqn_def.aircraft.iter_task_capabilities()
        ), path

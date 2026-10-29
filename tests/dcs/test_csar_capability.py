import pytest

from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType


@pytest.mark.parametrize("name", ["SA342M", "SA342L", "AH-64D", "Ka-50"])
def test_helicopter_without_dcs_transport_task_is_not_csar_capable(
    name: str,
) -> None:
    # Mission generation configures CSAR flights with the DCS Transport task and
    # aborts for a type that cannot take it.
    from dcs.helicopters import helicopter_map

    priorities = AircraftType.get_task_priorities({}, helicopter_map[name], 2)
    assert FlightType.CSAR not in priorities


def test_transport_capable_helicopter_is_csar_capable() -> None:
    from dcs.helicopters import helicopter_map

    priorities = AircraftType.get_task_priorities(
        {"tasks": {"Transport": 100}}, helicopter_map["UH-1H"], 8
    )
    assert FlightType.CSAR in priorities

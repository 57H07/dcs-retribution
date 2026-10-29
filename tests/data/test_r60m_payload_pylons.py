"""Our customized R-60M payloads must use a CLSID the pylon accepts.

Su-17M4, Su-24M and MiG-25PD payloads used to carry legacy R-60M CLSIDs that
pydcs does not list for those pylons, so every generated flight logged
"Pylon N cannot equip R-60M" for each pylon of each aircraft.
"""

import datetime
import json
from pathlib import Path
from typing import Any, Iterator, Optional

import pytest
from dcs import lua, task

from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon
from game.dcs.aircrafttype import AircraftType
from game.factions.faction import Faction

PAYLOADS_DIR = Path("resources/customized_payloads")


def _payloads(lua_name: str) -> Iterator[Loadout]:
    lua_globals: dict[str, Any] = {
        str(v.internal_name): v.id for v in task.MainTask.map.values()
    }
    text = (PAYLOADS_DIR / lua_name).read_text(encoding="utf-8")
    unit_payloads = lua.loads(text, _globals=lua_globals)["unitPayloads"]
    for payload in unit_payloads["payloads"].values():
        pylons: dict[int, Optional[Weapon]] = {}
        for pylon in payload["pylons"].values():
            weapon = Weapon.with_clsid(pylon["CLSID"])
            assert weapon is not None, pylon["CLSID"]
            pylons[pylon["num"]] = weapon
        yield Loadout(payload["name"], pylons, date=None)


def _incompatible(aircraft: AircraftType, loadout: Loadout) -> list[str]:
    return [
        f"{loadout.name}: pylon {number} {weapon.name}"
        for number, weapon in loadout.pylons.items()
        if weapon is not None
        and not Pylon.for_aircraft(aircraft, number).can_equip(weapon)
    ]


@pytest.mark.parametrize(
    "aircraft_name,lua_name",
    [
        ("Su-17M4 Fitter-K", "Su-17M4.lua"),
        ("Su-24M Fencer-D", "Su-24M.lua"),
        ("MiG-25PD Foxbat-E", "MiG-25PD.lua"),
    ],
)
def test_r60m_payloads_fit_their_pylons_with_and_without_date_restriction(
    aircraft_name: str, lua_name: str
) -> None:
    aircraft = AircraftType.named(aircraft_name)
    with Path("resources/factions/russia_1975.json").open(encoding="utf-8") as data:
        faction = Faction.from_dict(json.load(data))

    errors = []
    for loadout in _payloads(lua_name):
        errors += _incompatible(aircraft, loadout)
        degraded = loadout.degrade_for_date(
            aircraft, datetime.date(1975, 1, 1), faction
        )
        errors += _incompatible(aircraft, degraded)
        # R-60M (1982) is not period-correct in 1975: it must be degraded away.
        assert all(
            w is None or w.weapon_group.name not in ("R-60M", "R-60M x 2")
            for w in degraded.pylons.values()
        )

    assert not errors

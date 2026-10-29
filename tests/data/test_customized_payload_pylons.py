"""Every customized payload must only use CLSIDs that its pylons accept.

A payload CLSID that pydcs does not list for a pylon makes mission generation log
"Pylon N cannot equip <weapon>" for every flight that uses it (e.g. legacy R-60M
CLSIDs on the Su-17M4, Su-24M and MiG-25PD), and a CLSID pydcs does not know at
all makes Retribution skip the whole payload. Date restriction must not
introduce such mismatches either.
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

_NO_AIRCRAFT_TYPE = (
    "no Retribution aircraft type uses this unitType, so the payload is never loaded"
)

# Payload files whose unitType Retribution does not know, with the reason.
UNCHECKED_FILES: dict[str, str] = {
    "CH_Mi28N.lua": _NO_AIRCRAFT_TYPE,
    "FA-18C.lua": _NO_AIRCRAFT_TYPE + " (legacy F/A-18C, not FA-18C_hornet)",
    "L-39C.lua": _NO_AIRCRAFT_TYPE,
    "Rafale_A_S.lua": _NO_AIRCRAFT_TYPE,
    "Rafale_B.lua": _NO_AIRCRAFT_TYPE,
    "Rafale_M.lua": _NO_AIRCRAFT_TYPE,
    "VSN_F4E.lua": _NO_AIRCRAFT_TYPE,
    "vwv_sh2f.lua": _NO_AIRCRAFT_TYPE,
}

_MOD_PYLONS = (
    "mod aircraft: its pydcs definition does not list this store on this pylon "
    "and offers no equivalent"
)

# (payload file, CLSID) mismatches that cannot be fixed in our data, with the reason.
ALLOWED_MISMATCHES: dict[tuple[str, str], str] = {
    ("F-16A.lua", "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}"): _MOD_PYLONS,
    ("F-16A MLU.lua", "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}"): _MOD_PYLONS,
    ("F-16D_50.lua", "{IDF Mods Project F-16C CFT}"): _MOD_PYLONS,
    ("F-16D_52.lua", "{IDF Mods Project F-16C CFT}"): _MOD_PYLONS,
    ("Mi-28.lua", "{05544F1A-C39C-466b-BC37-5BD1D52E57BB}"): _MOD_PYLONS,
    ("Mi-28.lua", "{57232979-8B0F-4db7-8D9A-55197E06B0F5}"): _MOD_PYLONS,
    ("Su-30MKA.lua", "{SU30_KH31P}"): _MOD_PYLONS,
    ("Su-30MKA.lua", "{53BE25A4-C86C-4571-9BC0-47D668349595}"): _MOD_PYLONS,
    ("Su-30MKI.lua", "{SU30_R27ET}"): _MOD_PYLONS,
    ("Su-30MKI.lua", "{53BE25A4-C86C-4571-9BC0-47D668349595}"): _MOD_PYLONS,
    ("Su-57.lua", "{KH_59MK2}"): "mod weapon missing from pydcs_extensions",
    ("Su-57.lua", "{35B698AC-9FEF-4EC4-AD29-484A0085F62B}"): _MOD_PYLONS,
    ("Su-57.lua", "{F72F47E5-C83A-4B85-96ED-D3E46671EE9A}"): _MOD_PYLONS,
    ("Su-57.lua", "{FBC29BFE-3D24-4C64-B81D-941239D12249}"): _MOD_PYLONS,
    ("TIEB.lua", "{DAC53A2F-79CA-42FF-A77A-F5649B601308}"): _MOD_PYLONS,
    ("VSN_F4C.lua", "{6D21ECEA-F85B-4E8D-9D51-31DC9B8AA4EF}"): _MOD_PYLONS,
    ("vwv_ch46d_late.lua", "{DFT-150gal}"): _MOD_PYLONS,
    ("vwv_crusader_np.lua", "LAU3_HE5"): _MOD_PYLONS,
    ("vwv_crusader_np.lua", "{AIM-9D}"): _MOD_PYLONS,
    ("vwv_crusader_np.lua", "{F3EFE0AB-E91A-42D8-9CA2-B63C91ED570A}"): _MOD_PYLONS,
    ("vwv_crusader_np.lua", "{Mk-82_IMER_4_L}"): _MOD_PYLONS,
    ("vwv_crusader_np.lua", "{Mk-82_IMER_4_R}"): _MOD_PYLONS,
    # pydcs defines no stores at all on the SA342Mistral's pylons 1-4 (the
    # Mistral launchers are fixed on that variant), so nothing can match.
    ("SA342Mistral.lua", "{MBDA_MistralD}"): "pydcs lists no stores on pylons 1-4",
    ("SA342Mistral.lua", "{MBDA_MistralG}"): "pydcs lists no stores on pylons 1-4",
    ("SA342Mistral.lua", "{SA342_Mistral_R1}"): "pydcs lists no stores on pylons 1-4",
    ("SA342Mistral.lua", "{SA342_Mistral_L1}"): "pydcs lists no stores on pylons 1-4",
}


def _lua_globals() -> dict[str, Any]:
    return {str(v.internal_name): v.id for v in task.MainTask.map.values()}


def _read(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return lua.loads(text, _globals=_lua_globals())["unitPayloads"]


def _payloads(unit_payloads: dict[str, Any]) -> Iterator[Loadout]:
    for payload in unit_payloads["payloads"].values():
        pylons: dict[int, Optional[Weapon]] = {}
        for pylon in payload["pylons"].values():
            weapon = Weapon.with_clsid(pylon["CLSID"])
            assert weapon is not None, pylon["CLSID"]
            pylons[pylon["num"]] = weapon
        yield Loadout(payload["name"], pylons, date=None)


def _aircraft_by_dcs_id() -> dict[str, AircraftType]:
    aircraft: dict[str, AircraftType] = {}
    for a in AircraftType.iter_all():
        aircraft.setdefault(a.dcs_unit_type.id, a)
    return aircraft


def _incompatible(aircraft: AircraftType, loadout: Loadout) -> list[str]:
    return [
        f"{loadout.name}: pylon {number} {weapon.name} ({weapon.clsid})"
        for number, weapon in loadout.pylons.items()
        if weapon is not None
        and not Pylon.for_aircraft(aircraft, number).can_equip(weapon)
    ]


@pytest.mark.parametrize(
    "path", sorted(PAYLOADS_DIR.glob("*.lua")), ids=lambda p: str(p.name)
)
def test_customized_payloads_fit_their_pylons(path: Path) -> None:
    if path.name in UNCHECKED_FILES:
        pytest.skip(UNCHECKED_FILES[path.name])
    unit_payloads = _read(path)
    aircraft = _aircraft_by_dcs_id().get(unit_payloads["unitType"])
    assert aircraft is not None, f"unknown unitType {unit_payloads['unitType']}"

    errors = []
    for payload in unit_payloads["payloads"].values():
        for pylon in payload["pylons"].values():
            clsid, number = pylon["CLSID"], pylon["num"]
            if (path.name, clsid) in ALLOWED_MISMATCHES:
                continue
            weapon = Weapon.with_clsid(clsid)
            if weapon is None:
                errors.append(f"{payload['name']}: pylon {number} unknown {clsid!r}")
            elif not Pylon.for_aircraft(aircraft, number).can_equip(weapon):
                errors.append(f"{payload['name']}: pylon {number} {weapon.name}")
    assert not errors


@pytest.mark.parametrize(
    "lua_name", ["Su-17M4.lua", "Su-24M.lua", "MiG-25PD.lua", "MiG-29 Fulcrum.lua"]
)
def test_soviet_payloads_degrade_to_valid_period_loadouts(lua_name: str) -> None:
    unit_payloads = _read(PAYLOADS_DIR / lua_name)
    aircraft = _aircraft_by_dcs_id()[unit_payloads["unitType"]]
    with Path("resources/factions/russia_1975.json").open(encoding="utf-8") as data:
        faction = Faction.from_dict(json.load(data))

    errors = []
    for loadout in _payloads(unit_payloads):
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

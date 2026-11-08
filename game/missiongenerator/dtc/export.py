"""Put the cartridges of the player flights in the mission and next to it (#191).

`prepare` runs before the `.miz` is saved: it builds the cartridges and binds them to
the player units, which then carry a `DTC` block in the mission. `write` runs after:
it adds `DTC/<name>.dtc` to the `.miz` and copies each cartridge in a folder next to
it, so the Radios & TACAN tab can hand it to the player.

Neither ever fails the mission: a cartridge that cannot be built is logged and left
out, and when the cartridges cannot be added to the `.miz`, the mission is saved
again without them, as it was before the feature.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

from game import persistency
from .cartridge import DtcCartridge, DtcContext, build_cartridge

if TYPE_CHECKING:
    from dcs.flyingunit import FlyingUnit
    from dcs.mission import Mission

    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

INDEX_FILE = "index.json"


@dataclass(frozen=True)
class FlightCartridge:
    flight_id: UUID | None
    cartridge: DtcCartridge
    #: The player units that load it.
    units: tuple[FlyingUnit, ...]


def folder_for(miz: Path) -> Path:
    """The folder of the copies: `<mission>_DTC` next to the mission."""
    return miz.with_name(f"{miz.stem}_DTC")


def prepare(mission_data: MissionData, context: DtcContext) -> list[FlightCartridge]:
    """Build the cartridge of each player flight and bind it to its player units."""
    built: list[FlightCartridge] = []
    names: set[str] = set()
    for flight in mission_data.flights:
        if not flight.client_units:
            continue
        try:
            cartridge = build_cartridge(flight, mission_data, context)
        except Exception:
            logging.exception("Could not build the cartridge of %s", flight.callsign)
            continue
        if cartridge is None:
            continue
        cartridge = _unique(cartridge, names)
        names.add(cartridge.name)
        units = tuple(flight.client_units)
        for unit in units:
            _bind(unit, cartridge.name)
        built.append(FlightCartridge(flight.flight_id, cartridge, units))
    return built


def write(cartridges: list[FlightCartridge], miz: Path, mission: Mission) -> None:
    """Add the cartridges to `miz`, saved from `mission`, and copy them next to it."""
    folder = folder_for(miz)
    try:
        if folder.exists():
            shutil.rmtree(folder)
    except OSError:
        logging.exception("Could not clear the data cartridges of %s", folder)
    if not cartridges:
        return
    try:
        _embed(cartridges, miz)
    except Exception:
        logging.exception("Could not add the data cartridges to %s", miz)
        # The units name cartridges the miz lacks: save it again without them.
        for entry in cartridges:
            for unit in entry.units:
                _unbind(unit)
        mission.save(str(miz))
        return
    try:
        _copy(cartridges, folder)
    except Exception:
        logging.exception("Could not copy the data cartridges to %s", folder)


def _embed(cartridges: list[FlightCartridge], miz: Path) -> None:
    """Append the cartridges to a copy of `miz`, then replace it: never half written."""
    temporary = miz.with_name(miz.name + ".tmp")
    try:
        shutil.copyfile(miz, temporary)
        with ZipFile(temporary, "a", compression=ZIP_DEFLATED) as archive:
            for entry in cartridges:
                archive.writestr(
                    f"DTC/{entry.cartridge.file_name}", entry.cartridge.to_json()
                )
        os.replace(temporary, miz)
    finally:
        temporary.unlink(missing_ok=True)


def _copy(cartridges: list[FlightCartridge], folder: Path) -> None:
    folder.mkdir(parents=True)
    index: dict[str, str] = {}
    for entry in cartridges:
        path = folder / entry.cartridge.file_name
        path.write_text(entry.cartridge.to_json(), encoding="utf-8")
        if entry.flight_id is not None:
            index[str(entry.flight_id)] = entry.cartridge.file_name
    text = json.dumps(index, indent=2)
    persistency.write_atomically(
        folder / INDEX_FILE, lambda f: f.write(text.encode("utf-8"))
    )


def cartridge_file(miz: Path, flight_id: UUID) -> Path | None:
    """The copy of the cartridge of the flight in the last mission written to `miz`."""
    folder = folder_for(miz)
    try:
        index = json.loads((folder / INDEX_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    name = index.get(str(flight_id)) if isinstance(index, dict) else None
    if not isinstance(name, str):
        return None
    path = folder / name
    return path if path.is_file() else None


def _unique(cartridge: DtcCartridge, taken: set[str]) -> DtcCartridge:
    """Two flights may share a callsign: the second gets ` 2`, and so on."""
    name = cartridge.name
    number = 2
    while name in taken:
        name = f"{cartridge.name} {number}"
        number += 1
    if name == cartridge.name:
        return cartridge
    data = dict(cartridge.data, name=name)
    return DtcCartridge(name=name, unit_type=cartridge.unit_type, data=data)


def _bind(unit: FlyingUnit, name: str) -> None:
    """Make the unit load the cartridge at spawn.

    pydcs writes no `DTC` block, so the unit's own `dict()` gets it added.
    """
    unit_dict = unit.dict

    def with_cartridge() -> dict[str, Any]:
        d = unit_dict()
        d["DTC"] = {
            "Cartridges": {1: {"name": name, "default": True}},
            "AutoLoad": True,
        }
        return d

    setattr(unit, "dict", with_cartridge)


def _unbind(unit: FlyingUnit) -> None:
    vars(unit).pop("dict", None)

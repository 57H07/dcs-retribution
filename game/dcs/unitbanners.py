"""Banner images of unit types, shared by the web and Qt unit info sheets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from game.dcs.aircrafttype import AircraftType
from game.dcs.groundunittype import GroundUnitType
from game.dcs.shipunittype import ShipUnitType
from game.dcs.unittype import UnitType

AIRCRAFT_BANNERS_BASE = Path("resources/ui/units/aircrafts/banners")
VEHICLE_BANNERS_BASE = Path("resources/ui/units/vehicles/banners")
SHIP_IMAGES_BASE = Path("resources/ui/units/ships")
MISSING_BANNER_PATH = AIRCRAFT_BANNERS_BASE / "Missing.jpg"


def aircraft_banner_for(unit_type: AircraftType) -> Path:
    if unit_type.dcs_id in {
        "Mirage-F1CT",
        "Mirage-F1EE",
        "Mirage-F1M-EE",
        "Mirage-F1EQ",
    }:
        name = "Mirage-F1C-200"
    elif unit_type.dcs_id in {"Mirage-F1CE", "Mirage-F1M-CE"}:
        name = "Mirage-F1C"
    elif unit_type.dcs_id in {
        "Su-30MKA",
        "Su-30MKI",
        "Su-30MKM",
        "Su-30MKA-AG",
        "Su-30MKI-AG",
        "Su-30MKM-AG",
        "Su-30SM-AG",
    }:
        name = "Su-30SM"
    elif unit_type.dcs_id == "Su-35S-AG":
        name = "Su-35S"
    elif unit_type.dcs_id == "F-15ESE":
        name = "F-15E"
    elif "_FC" in unit_type.dcs_id:
        name = unit_type.dcs_id.replace("_FC", "")
    else:
        name = unit_type.dcs_id
    return AIRCRAFT_BANNERS_BASE / f"{name}.jpg"


def vehicle_banner_for(unit_type: GroundUnitType) -> Path:
    if unit_type.dcs_id == "(IDF Mods Project) BM-21 Grad 122mm":
        return VEHICLE_BANNERS_BASE / "Grad-URAL.jpg"
    elif unit_type.dcs_id == "(IDF Mods Project) Urgan BM-27 220mm":
        return VEHICLE_BANNERS_BASE / "Uragan_BM-27.jpg"
    elif unit_type.dcs_id == "(IDF Mods Project) 9A52 Smerch CM 300mm":
        return VEHICLE_BANNERS_BASE / "Smerch_HE.jpg"
    else:
        return VEHICLE_BANNERS_BASE / f"{unit_type.dcs_id}.jpg"


def banner_path_for(unit_type: UnitType[Any]) -> Path:
    if isinstance(unit_type, AircraftType):
        return aircraft_banner_for(unit_type)
    if isinstance(unit_type, GroundUnitType):
        return vehicle_banner_for(unit_type)
    if isinstance(unit_type, ShipUnitType):
        return SHIP_IMAGES_BASE / f"{unit_type.dcs_id}.png"
    raise NotImplementedError(f"Unhandled UnitType subclass: {unit_type.__class__}")


def existing_banner_for(unit_type: UnitType[Any]) -> Path:
    """The unit type's banner, or the generic one when it has none."""
    path = banner_path_for(unit_type)
    return path if path.exists() else MISSING_BANNER_PATH

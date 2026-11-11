"""Unit info sheet (WEB-08.3): static data of a unit type and its banner."""

from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel

from game.dcs.aircrafttype import AircraftType
from game.dcs.groundunittype import GroundUnitType
from game.dcs.shipunittype import ShipUnitType
from game.dcs.unitbanners import existing_banner_for
from game.dcs.unittype import UnitType
from game.gamelock import locked
from game.ground_forces.purpose import front_line_purpose

UnitKind = Literal["aircraft", "ground", "ship"]

router: APIRouter = APIRouter(prefix="/unit-info")

# Types without data get a rich text "No data" with a link to a web search, for Qt.
_HTML_LINK = re.compile(r"\s*<a\b.*?</a>", re.DOTALL)
_MEDIA_TYPES = {".jpg": "image/jpeg", ".png": "image/png"}


class UnitInfoJs(BaseModel):
    kind: UnitKind
    name: str
    display_name: str
    manufacturer: str
    country_of_origin: str
    role: str
    year_introduced: str
    #: What an aircraft can be tasked with; empty for other units.
    tasks: list[str]
    #: The unit's class, e.g. "Tank", "SHORAD" (`UnitClass`).
    unit_class: str
    #: What a ground unit does in the ground war (#214); empty for other units.
    purpose: str
    #: Plain text.
    description: str

    class Config:
        title = "UnitInfo"

    @staticmethod
    def for_unit_type(kind: UnitKind, unit_type: UnitType[Any]) -> UnitInfoJs:
        tasks = (
            [str(task) for task in unit_type.iter_task_capabilities()]
            if isinstance(unit_type, AircraftType)
            else []
        )
        return UnitInfoJs(
            kind=kind,
            name=unit_type.variant_id,
            display_name=unit_type.display_name,
            # Plain YAML values: a year or a role may not be a string.
            manufacturer=str(unit_type.manufacturer),
            country_of_origin=str(unit_type.country_of_origin),
            role=str(unit_type.role),
            year_introduced=str(unit_type.year_introduced),
            tasks=tasks,
            unit_class=unit_type.unit_class.value,
            purpose=(
                front_line_purpose(unit_type)
                if isinstance(unit_type, GroundUnitType)
                else ""
            ),
            description=_HTML_LINK.sub("", str(unit_type.description)),
        )


def _unit_type(kind: UnitKind, name: str) -> UnitType[Any]:
    types: dict[UnitKind, type[UnitType[Any]]] = {
        "aircraft": AircraftType,
        "ground": GroundUnitType,
        "ship": ShipUnitType,
    }
    try:
        return types[kind].named(name)
    except KeyError:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"No {kind} unit named {name}"
        )


# Names may hold slashes: they travel as query parameters, not in the path.
@router.get("", operation_id="get_unit_info", response_model=UnitInfoJs)
@locked
def get_unit_info(kind: UnitKind = Query(...), name: str = Query(...)) -> UnitInfoJs:
    return UnitInfoJs.for_unit_type(kind, _unit_type(kind, name))


@router.get(
    "/banner",
    operation_id="get_unit_banner",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "image/png": {}}}},
)
@locked
def get_unit_banner(kind: UnitKind = Query(...), name: str = Query(...)) -> Response:
    """The picture of a unit type, loaded by URL by the sheet (`<img>`)."""
    path = existing_banner_for(_unit_type(kind, name))
    return Response(
        content=path.read_bytes(),
        media_type=_MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream"),
    )

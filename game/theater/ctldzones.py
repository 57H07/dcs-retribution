"""Default CTLD pickup and drop zones for control points that have none.

Campaign designers declare CTLD zones as trigger zones named ``<base name> CTLD``
(see ``MizCampaignLoader.get_ctld_zones``). Few campaigns do, so when the CTLD plugin
option ``ctld.defaultzones`` is enabled, every airfield and FOB/FARP without designer
zones receives generated ones. Naval and off-map control points cannot host a zone;
:func:`ctld_zone_unavailable_reason` explains why to the player.

Generated zones are flagged on the control point (``ctld_zones_generated``) so that
disabling the option removes them again and designer zones are never overwritten.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional, Protocol, TYPE_CHECKING

from dcs import Point

from game.theater.controlpoint import Airfield, ControlPoint, Fob
from game.theater.interfaces.CTLD import CTLD

if TYPE_CHECKING:
    from game.settings import Settings

#: Plugin option identifier that enables the default zones.
DEFAULT_ZONES_OPTION = "ctld.defaultzones"

#: Airfield zones sit on both sides of the main runway, clear of the runway and of
#: most aprons, measured from the airfield reference point.
AIRFIELD_ZONE_OFFSET_METERS = 750
AIRFIELD_ZONE_RADIUS_METERS = 250

#: FOB/FARP zones sit next to the FARP, clear of its pads and statics.
FOB_ZONE_OFFSET_METERS = 300
FOB_ZONE_RADIUS_METERS = 150


class LandCheck(Protocol):
    def is_on_land(self, point: Point, ignore_exclusion: bool = False) -> bool: ...


def default_zones_enabled(settings: Settings) -> bool:
    try:
        return bool(settings.plugin_option("ctld")) and bool(
            settings.plugin_option(DEFAULT_ZONES_OPTION)
        )
    except KeyError:
        # Plugin options are not registered (plugin missing): keep current behavior.
        return False


def _candidates(cp: ControlPoint) -> list[tuple[Point, float]]:
    if isinstance(cp, Airfield):
        runways = cp.airport.runways if cp.airport is not None else []
        heading = runways[0].main.heading if runways else 0
        return [
            (
                cp.position.point_from_heading(
                    (heading + side) % 360, AIRFIELD_ZONE_OFFSET_METERS
                ),
                AIRFIELD_ZONE_RADIUS_METERS,
            )
            for side in (90, 270)
        ]
    if isinstance(cp, Fob):
        return [
            (
                cp.position.point_from_heading(heading, FOB_ZONE_OFFSET_METERS),
                FOB_ZONE_RADIUS_METERS,
            )
            for heading in (0, 180)
        ]
    return []


def ctld_zone_unavailable_reason(
    cp: ControlPoint, land: Optional[LandCheck] = None
) -> Optional[str]:
    """Returns why no CTLD zone exists or can be created at cp, or None if it can.

    Designer zones always win. Otherwise only airfields and FOBs/FARPs can host a
    zone, and at least one generated zone must be on land.
    """
    if isinstance(cp, CTLD) and cp.ctld_zones:
        return None
    if not isinstance(cp, (Airfield, Fob)):
        return (
            f"{cp.name} is a ship or an off-map spawn: CTLD pickup and drop zones "
            "can only exist at airfields and FOBs/FARPs, so Transport missions are "
            "unavailable there."
        )
    if land is not None and not any(
        land.is_on_land(position) for position, _ in _candidates(cp)
    ):
        return (
            f"No dry land found around {cp.name} for a default CTLD zone: add a "
            f'trigger zone named "{cp.name} CTLD" to the campaign to enable '
            "Transport missions there."
        )
    return None


def default_ctld_zones(cp: ControlPoint, land: LandCheck) -> list[tuple[Point, float]]:
    """Returns the generated CTLD zones for cp (empty if none can be placed)."""
    return [zone for zone in _candidates(cp) if land.is_on_land(zone[0])]


def apply_default_ctld_zones(
    control_points: Iterable[ControlPoint], land: LandCheck, enabled: bool
) -> list[str]:
    """Adds or removes generated CTLD zones. Returns the warnings raised.

    Idempotent: control points with designer zones are left untouched, generated zones
    are only created once, and are removed when ``enabled`` is False.
    """
    warnings: list[str] = []
    for cp in control_points:
        if not isinstance(cp, CTLD):
            continue
        if not enabled:
            if cp.ctld_zones_generated:
                cp.ctld_zones = []
                cp.ctld_zones_generated = False
            continue
        if cp.ctld_zones:
            continue
        zones = default_ctld_zones(cp, land)
        if zones:
            cp.ctld_zones = zones
            cp.ctld_zones_generated = True
            continue
        reason = ctld_zone_unavailable_reason(cp, land)
        if reason is not None:
            logging.warning(reason)
            warnings.append(reason)
    return warnings

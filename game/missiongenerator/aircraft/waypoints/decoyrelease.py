import logging

from dcs.point import MovingPoint
from dcs.task import AttackGroup, Expend, WeaponType as DcsWeaponType

from game.data.weapons import WeaponType
from game.theater import TheaterGroundObject
from .pydcswaypointbuilder import PydcsWaypointBuilder


class DecoyReleaseBuilder(PydcsWaypointBuilder):
    """Releases the flight's decoys (e.g. TALD) at the SEAD decoy release point.

    The point is placed at the configured release distance from the target so
    the decoys can glide into the SAM's engagement zone. The anti-radiation and
    other weapons stay on the INGRESS waypoint (see SeadIngressBuilder).
    """

    def add_tasks(self, waypoint: MovingPoint) -> None:
        # The loadout may have changed since the flight plan was created.
        if not self.flight.any_member_has_weapon_of_type(WeaponType.DECOY):
            return

        target = self.package.target
        if not isinstance(target, TheaterGroundObject):
            logging.error(
                "Unexpected target type for SEAD decoy release: %s",
                target.__class__.__name__,
            )
            return

        for group in target.groups:
            miz_group = self.mission.find_group(group.group_name)
            if miz_group is None:
                logging.error(
                    f"Could not find group for SEAD decoy release {group.group_name}"
                )
                continue

            waypoint.tasks.append(
                AttackGroup(
                    miz_group.id,
                    weapon_type=DcsWeaponType.Decoy,
                    group_attack=True,
                    expend=Expend.All,
                    altitude=round(waypoint.alt * 1.5),  # 50% increase forces a climb
                )
            )

"""Parking room a squadron would find at a transfer destination."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from game.theater import ParkingType

if TYPE_CHECKING:
    from game.theater import ControlPoint
    from .squadron import Squadron


@dataclass(frozen=True)
class TransferParking:
    #: Free slots at the base for the squadron's aircraft type.
    room: int
    #: Other squadrons expected at the base that do not all fit there.
    overflow: list[Squadron] = field(default_factory=list)


def transfer_parking(squadron: Squadron, cp: ControlPoint) -> TransferParking:
    """Parking room for ``squadron`` at ``cp``, ignoring the squadron itself.

    The base is filled with every other squadron expected there next turn: the
    squadrons currently based there (outgoing transfers included, since they may
    have to come back if their destination is captured) and the squadrons
    relocating in. ``squadron`` is left out so that its own planned transfer to
    ``cp`` does not eat into the room shown for it, which made a transfer that
    was just planned look impossible when the dialog was reopened (BUG-05).
    """
    others = [s for s in cp.squadrons if s != squadron]
    others += [
        s
        for s in cp.coalition.air_wing.iter_squadrons()
        if s.destination == cp and s != squadron
    ]

    airport = cp.dcs_airport
    if airport is None:
        parking_type = ParkingType().from_aircraft(
            squadron.aircraft, cp.coalition.game.settings.ground_start_ai_planes
        )
        room = cp.unclaimed_parking(parking_type)
        if squadron.destination == cp:
            # unclaimed_parking() counts the incoming squadron and its orders.
            room += squadron.owned_aircraft + squadron.pending_deliveries
        return TransferParking(room)

    ap = deepcopy(airport)
    overflow: list[Squadron] = []
    free_helicopter_slots = cp.total_aircraft_parking(
        ParkingType(fixed_wing=False, fixed_wing_stol=False, rotary_wing=True)
    )
    free_ground_spawns = cp.total_aircraft_parking(
        ParkingType(fixed_wing=False, fixed_wing_stol=True, rotary_wing=False)
    )
    for s in others:
        for count in range(s.owned_aircraft):
            is_heli = s.aircraft.helicopter
            is_vtol = not is_heli and s.aircraft.lha_capable
            count_ground_spawns = (
                s.aircraft.flyable or cp.coalition.game.settings.ground_start_ai_planes
            )
            if free_helicopter_slots > 0 and is_heli:
                free_helicopter_slots -= 1
            elif free_ground_spawns > 0 and (is_heli or is_vtol or count_ground_spawns):
                free_ground_spawns -= 1
            else:
                slot = ap.free_parking_slot(s.aircraft.dcs_unit_type)
                if slot:
                    slot.unit_id = id(s) + count
                else:
                    overflow.append(s)
                    break
    room = (
        len(ap.free_parking_slots(squadron.aircraft.dcs_unit_type))
        + free_helicopter_slots
        + free_ground_spawns
    )
    return TransferParking(room, overflow)

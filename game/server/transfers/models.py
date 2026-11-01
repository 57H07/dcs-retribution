"""Pending transfers screen (WEB-08.2): read model of `PendingTransfersDialog`."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

if TYPE_CHECKING:
    from game.transfers import TransferOrder


class TransferUnitJs(BaseModel):
    name: str
    count: int


class TransferJs(BaseModel):
    """A pending ground unit transfer of the player."""

    id: UUID
    origin: str
    destination: str
    #: Where the units are now (a stop on the way, or the origin).
    position: str
    size: int
    units: list[TransferUnitJs]
    #: This turn's leg ("No transports available" when none is planned).
    transport: str

    @staticmethod
    def from_transfer(transfer: TransferOrder) -> TransferJs:
        units = sorted(
            (
                TransferUnitJs(name=unit_type.display_name, count=count)
                for unit_type, count in transfer.units.items()
                if count
            ),
            key=lambda u: u.name,
        )
        return TransferJs(
            id=transfer.id,
            origin=transfer.origin.name,
            destination=transfer.destination.name,
            position=transfer.position.name,
            size=transfer.size,
            units=units,
            transport=transfer.description,
        )

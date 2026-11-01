"""Pending ground unit transfers (WEB-08.2), shared by the web UI and Qt."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from game.theater.player import Player
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.transfers import TransferOrder


def find_transfer(game: Game, transfer_id: UUID) -> TransferOrder | None:
    """The pending transfer of either coalition with this id, or None."""
    for coalition in game.coalitions:
        for transfer in coalition.transfers:
            if transfer.id == transfer_id:
                return transfer
    return None


def cancel_transfer(game: Game, transfer: TransferOrder) -> None:
    """Cancel a player transfer: its units return to the origin's inventory.

    `PendingTransfers.cancel_transfer` publishes the supply route change.
    """
    if not transfer.player.is_blue:
        raise CommandError("Only your own transfers can be cancelled.")
    transfers = game.coalition_for(Player.BLUE).transfers
    if not any(pending is transfer for pending in transfers):
        raise CommandError("This transfer is no longer pending.", status_code=404)
    transfers.cancel_transfer(transfer)

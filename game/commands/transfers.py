"""Ground unit transfers (WEB-08.2, WEB-02.3), shared by the web UI and Qt.

The rules of `NewUnitTransferDialog`, `DepartingConvoysMenu` and
`PendingTransfersDialog`. The units leave the inventory of the origin when the transfer
is placed. Without a squadron the engine arranges the transport (convoy, cargo ship or
AI airlift); a squadron makes it a player Transport mission (TRN-01.2).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional, cast
from uuid import UUID

from game.ato.flighttype import FlightType
from game.theater.ctldzones import ctld_zone_unavailable_reason, default_zones_enabled
from game.theater.player import Player
from game.theater.transitnetwork import NoPathError
from game.transfers import (
    CargoShip,
    Convoy,
    MultiGroupTransport,
    TransferOrder,
    airlift_squadrons,
    player_airlift_problem,
)
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.dcs.groundunittype import GroundUnitType
    from game.squadrons import Squadron
    from game.theater import ControlPoint


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


def can_transfer_units(game: Game, origin: ControlPoint) -> bool:
    """A player base with somewhere to send a convoy, ship or airlift."""
    return origin.captured.is_blue and game.transit_network_for(
        origin.captured
    ).has_destinations(origin)


def can_plan_transport_mission(origin: ControlPoint) -> bool:
    """A player base where a Transport mission can pick up units."""
    return origin.captured.is_blue and origin.can_deploy_ground_units


def transfer_destinations(game: Game, origin: ControlPoint) -> list[ControlPoint]:
    """Where units of this base can be sent, by name."""
    return sorted(
        (
            cp
            for cp in game.theater.controlpoints
            if cp != origin
            and cp.is_friendly(to_player=Player.BLUE)
            and cp.can_deploy_ground_units
        ),
        key=lambda cp: cp.name,
    )


def transferable_units(game: Game, origin: ControlPoint) -> dict[GroundUnitType, int]:
    """The units of the player's faction in the inventory of this base, by name."""
    faction = game.coalition_for(Player.BLUE).faction
    return {
        unit_type: origin.base.total_units_of_type(unit_type)
        for unit_type in sorted(set(faction.ground_units), key=lambda u: u.display_name)
        if origin.base.total_units_of_type(unit_type)
    }


def transport_squadrons(
    game: Game, origin: ControlPoint, destination: ControlPoint
) -> list[Squadron]:
    """The squadrons a Transport mission between these bases can pick."""
    draft = TransferOrder(origin, destination, {})
    return airlift_squadrons(game.blue.air_wing, draft, destination)


def no_transport_squadron_warning(
    game: Game, origin: ControlPoint, destination: ControlPoint
) -> str:
    """Why no squadron can fly between these bases."""
    lines = [
        f"No Transport-capable squadron can fly between {origin.name} and "
        f"{destination.name} this turn (aircraft, pilots, base type or helicopter "
        "range)."
    ]
    land = game.theater if default_zones_enabled(game.settings) else None
    for cp in (origin, destination):
        if (reason := ctld_zone_unavailable_reason(cp, land)) is not None:
            lines.append(reason)
    return "\n".join(lines)


def check_transfer(
    game: Game, transfer: TransferOrder, squadron: Optional[Squadron] = None
) -> None:
    """Whether this transfer can be placed; changes nothing.

    Raises:
        CommandError: not a player base, a destination this base cannot send to, no
            units or more than the base has, no route, or a squadron that cannot fly it.
    """
    origin, destination = transfer.origin, transfer.destination
    if not origin.captured.is_blue:
        raise CommandError(f"{origin.name} is not your base: you cannot transfer.")
    if destination not in transfer_destinations(game, origin):
        raise CommandError(f"{destination.name} cannot receive units of {origin.name}.")
    if not any(transfer.units.values()):
        raise CommandError("Select at least one unit to transfer.")
    for unit_type, count in transfer.units.items():
        if count < 0:
            raise CommandError("A transfer cannot have a negative number of units.")
        available = origin.base.total_units_of_type(unit_type)
        if count > available:
            raise CommandError(
                f"{origin.name} has {available} {unit_type.display_name}, {count} "
                "selected."
            )
    if squadron is not None:
        problem = player_airlift_problem(squadron, transfer, destination)
        if problem is not None:
            raise CommandError(problem)
        return
    # The engine asks for the route even for an AI airlift.
    if not _has_route(game, origin, destination):
        raise CommandError(
            f"No route from {origin.name} to {destination.name}: pick a Transport "
            "squadron to airlift the units."
        )


def _has_route(game: Game, origin: ControlPoint, destination: ControlPoint) -> bool:
    network = game.transit_network_for(origin.captured)
    try:
        network.shortest_path_between(origin, destination)
    except (NoPathError, ValueError):
        return False
    return True


def place_transfer(
    game: Game,
    transfer: TransferOrder,
    squadron: Optional[Squadron],
    now: datetime,
) -> None:
    """Takes the units out of the origin and arranges their transport.

    `PendingTransfers` publishes the supply route change and the new flights.

    Raises:
        CommandError: see `check_transfer`.
    """
    check_transfer(game, transfer, squadron)
    transfer.units = {u: count for u, count in transfer.units.items() if count}
    transfers = game.coalition_for(Player.BLUE).transfers
    if squadron is not None:
        transfers.new_player_airlift(transfer, squadron, now)
    else:
        transfers.new_transfer(transfer, now)


def departing_transports(game: Game, cp: ControlPoint) -> list[MultiGroupTransport]:
    """The convoys, then the cargo ships, leaving this base this turn."""
    transfers = game.coalition_for(cp.captured).transfers
    transports: list[MultiGroupTransport] = list(transfers.convoys.departing_from(cp))
    transports.extend(transfers.cargo_ships.departing_from(cp))
    return transports


def transport_kind(transport: MultiGroupTransport) -> str:
    return "cargo-ship" if isinstance(transport, CargoShip) else "convoy"


def attackable_transport(
    game: Game, origin: ControlPoint, destination: ControlPoint, kind: str
) -> MultiGroupTransport:
    """An enemy convoy or cargo ship leaving a base, as a mission target.

    Raises:
        CommandError: it is gone (404), or it is the player's.
    """
    for transport in departing_transports(game, origin):
        if transport.destination == destination and transport_kind(transport) == kind:
            if transport.is_friendly(Player.BLUE):
                raise CommandError(f"{transport.name} is yours: you cannot attack it.")
            return transport
    raise CommandError("This convoy is no longer departing.", status_code=404)


def can_attack_airfield(cp: ControlPoint) -> bool:
    """A base whose runway can be the target of a package."""
    return FlightType.OCA_RUNWAY in cp.mission_types(for_player=Player.BLUE)

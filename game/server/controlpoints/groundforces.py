"""Ground forces, departing convoys and base actions of the base screen (WEB-02.3).

The rules are in `game.commands`: `groundorders`, `frontline`, `transfers`, `cheats` and
`baseradios`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from game.commands.baseradios import (
    BaseRadios,
    base_radios,
    has_radios,
    radio_warnings,
)
from game.commands.cheats import cheat_capture_label, cheat_runway_label
from game.commands.frontline import enemies_at_front, front_line_stance
from game.commands.groundorders import (
    ground_unit_types,
    max_ground_units_to_add,
    recruitment_refusal,
)
from game.commands.transfers import (
    can_attack_airfield,
    can_plan_transport_mission,
    can_transfer_units,
    departing_transports,
    no_transport_squadron_warning,
    transfer_destinations,
    transferable_units,
    transport_kind,
    transport_squadrons,
)
from game.ground_forces.combat_stance import CombatStance
from game.radio.ICLSContainer import ICLSContainer
from game.radio.Link4Container import Link4Container
from game.radio.RadioFrequencyContainer import RadioFrequencyContainer
from game.radio.TacanContainer import TacanContainer
from game.transfers import max_airlift_capacity
from ..reports.models import UnitCountJs

if TYPE_CHECKING:
    from game import Game
    from game.dcs.groundunittype import GroundUnitType
    from game.theater import ControlPoint
    from game.transfers import MultiGroupTransport

TransportKind = Literal["convoy", "cargo-ship"]


class GroundUnitRowJs(BaseModel):
    unit_id: str
    name: str
    unit_cost: float
    owned: int
    #: Paid orders delivered next turn.
    pending: int
    #: Most units this row alone can order now (budget, factory).
    max_add: int

    class Config:
        title = "GroundUnitRow"

    @staticmethod
    def for_unit(
        game: Game, cp: ControlPoint, unit_type: GroundUnitType
    ) -> GroundUnitRowJs:
        return GroundUnitRowJs(
            unit_id=unit_type.variant_id,
            name=unit_type.display_name,
            unit_cost=unit_type.price,
            owned=cp.base.total_units_of_type(unit_type),
            pending=cp.ground_unit_orders.pending_orders(unit_type),
            max_add=max_ground_units_to_add(game, cp, unit_type),
        )


class FrontLineStanceJs(BaseModel):
    enemy_id: UUID
    enemy: str
    #: Name of a `CombatStance`, among `stance_options`.
    stance: str

    class Config:
        title = "FrontLineStance"


class GroundForcesJs(BaseModel):
    #: Empty for an enemy base.
    units: list[GroundUnitRowJs]
    #: Why no unit can be ordered at all here, whatever the budget.
    recruitment_refusal: Optional[str]
    has_factory: bool
    present: int
    #: Ordered, and on their way here from a transfer.
    ordered: int
    transferring: int
    #: Units deployed to the front line, with the rest in reserve; None without one.
    deployable_limit: Optional[int]
    reserve: Optional[int]
    front_lines: list[FrontLineStanceJs]
    stance_options: list[str]
    #: The advance and retreat buttons of `enable_frontline_cheats`.
    front_line_cheats: bool

    class Config:
        title = "GroundForces"

    @staticmethod
    def for_control_point(game: Game, cp: ControlPoint) -> GroundForcesJs:
        blue = cp.captured.is_blue
        allocated = cp.allocated_ground_units(game.coalition_for(cp.captured).transfers)
        active = cp.has_active_frontline
        limit = cp.frontline_unit_count_limit
        return GroundForcesJs(
            units=(
                [GroundUnitRowJs.for_unit(game, cp, u) for u in ground_unit_types(cp)]
                if blue
                else []
            ),
            recruitment_refusal=recruitment_refusal(game, cp) if blue else None,
            has_factory=cp.has_factory,
            present=allocated.total_present,
            ordered=allocated.total_ordered,
            transferring=allocated.total_transferring,
            deployable_limit=limit if active else None,
            reserve=max(allocated.total_present - limit, 0) if active else None,
            front_lines=[
                FrontLineStanceJs(
                    enemy_id=enemy.id,
                    enemy=enemy.name,
                    stance=front_line_stance(cp, enemy).name,
                )
                for enemy in enemies_at_front(cp)
            ],
            stance_options=[stance.name for stance in CombatStance],
            front_line_cheats=game.settings.enable_frontline_cheats,
        )


class GroundOrderLineJs(BaseModel):
    unit_id: str
    #: Units to buy; negative to cancel pending orders.
    quantity: int

    class Config:
        title = "GroundOrderLine"


class GroundOrdersJs(BaseModel):
    orders: list[GroundOrderLineJs]

    class Config:
        title = "GroundOrders"


class StanceJs(BaseModel):
    stance: str

    class Config:
        title = "Stance"


class FrontLineCheatJs(BaseModel):
    advance: bool

    class Config:
        title = "FrontLineCheat"


class DepartingConvoyJs(BaseModel):
    name: str
    kind: TransportKind
    destination_id: UUID
    destination: str
    size: int
    units: list[UnitCountJs]

    class Config:
        title = "DepartingConvoy"

    @staticmethod
    def from_transport(transport: MultiGroupTransport) -> DepartingConvoyJs:
        return DepartingConvoyJs(
            name=transport.name,
            kind=(
                "cargo-ship" if transport_kind(transport) == "cargo-ship" else "convoy"
            ),
            destination_id=transport.destination.id,
            destination=transport.destination.name,
            size=transport.size,
            units=sorted(
                (
                    UnitCountJs(name=unit_type.display_name, count=count)
                    for unit_type, count in transport.units.items()
                    if count
                ),
                key=lambda unit: unit.name,
            ),
        )

    @staticmethod
    def departing_from(game: Game, cp: ControlPoint) -> list[DepartingConvoyJs]:
        return [
            DepartingConvoyJs.from_transport(t) for t in departing_transports(game, cp)
        ]


class TransferDestinationJs(BaseModel):
    id: UUID
    name: str

    class Config:
        title = "TransferDestination"


class TransferableUnitJs(BaseModel):
    unit_id: str
    name: str
    available: int

    class Config:
        title = "TransferableUnit"


class TransportSquadronJs(BaseModel):
    id: UUID
    label: str
    #: Most units one flight of this squadron can carry this turn.
    capacity: int

    class Config:
        title = "TransportSquadron"


class TransferOptionsJs(BaseModel):
    """What the new transfer dialog offers, for the destination it shows."""

    destinations: list[TransferDestinationJs]
    #: The destination the squadrons are for: the asked one, else the first.
    destination_id: Optional[UUID]
    units: list[TransferableUnitJs]
    squadrons: list[TransportSquadronJs]
    #: Why no squadron is offered.
    no_squadron_warning: Optional[str]

    class Config:
        title = "TransferOptions"

    @staticmethod
    def for_control_point(
        game: Game, origin: ControlPoint, destination_id: Optional[UUID]
    ) -> TransferOptionsJs:
        destinations = transfer_destinations(game, origin)
        destination = next(
            (cp for cp in destinations if cp.id == destination_id),
            destinations[0] if destinations else None,
        )
        squadrons = (
            transport_squadrons(game, origin, destination)
            if destination is not None
            else []
        )
        return TransferOptionsJs(
            destinations=[
                TransferDestinationJs(id=cp.id, name=cp.name) for cp in destinations
            ],
            destination_id=destination.id if destination is not None else None,
            units=[
                TransferableUnitJs(
                    unit_id=unit_type.variant_id,
                    name=unit_type.display_name,
                    available=count,
                )
                for unit_type, count in transferable_units(game, origin).items()
            ],
            squadrons=[
                TransportSquadronJs(
                    id=squadron.id,
                    label=(
                        f"{squadron.name} - {squadron.aircraft.display_name} at "
                        f"{squadron.location.name}"
                    ),
                    capacity=max_airlift_capacity(squadron),
                )
                for squadron in squadrons
            ],
            no_squadron_warning=(
                no_transport_squadron_warning(game, origin, destination)
                if destination is not None and not squadrons
                else None
            ),
        )


class BaseRadiosJs(BaseModel):
    """The settings this base has; a None value is automatic."""

    has_frequency: bool
    has_tacan: bool
    has_icls: bool
    has_link4: bool
    frequency_mhz: Optional[float]
    tacan_channel: Optional[int]
    tacan_band: Optional[str]
    tacan_callsign: Optional[str]
    icls_channel: Optional[int]
    icls_callsign: Optional[str]
    link4_mhz: Optional[float]
    warnings: list[str]

    class Config:
        title = "BaseRadios"

    @staticmethod
    def for_control_point(game: Game, cp: ControlPoint) -> BaseRadiosJs:
        settings = base_radios(cp)
        return BaseRadiosJs(
            has_frequency=isinstance(cp, RadioFrequencyContainer),
            has_tacan=isinstance(cp, TacanContainer),
            has_icls=isinstance(cp, ICLSContainer),
            has_link4=isinstance(cp, Link4Container),
            frequency_mhz=settings.frequency_mhz,
            tacan_channel=settings.tacan_channel,
            tacan_band=settings.tacan_band,
            tacan_callsign=settings.tacan_callsign,
            icls_channel=settings.icls_channel,
            icls_callsign=settings.icls_callsign,
            link4_mhz=settings.link4_mhz,
            warnings=radio_warnings(game, cp),
        )


class BaseRadiosUpdateJs(BaseModel):
    frequency_mhz: Optional[float] = None
    tacan_channel: Optional[int] = None
    tacan_band: Optional[str] = None
    tacan_callsign: Optional[str] = None
    icls_channel: Optional[int] = None
    icls_callsign: Optional[str] = None
    link4_mhz: Optional[float] = None

    class Config:
        title = "BaseRadiosUpdate"

    def to_settings(self) -> BaseRadios:
        return BaseRadios(
            frequency_mhz=self.frequency_mhz,
            tacan_channel=self.tacan_channel,
            tacan_band=self.tacan_band,
            tacan_callsign=self.tacan_callsign,
            icls_channel=self.icls_channel,
            icls_callsign=self.icls_callsign,
            link4_mhz=self.link4_mhz,
        )


class BaseActionsJs(BaseModel):
    """The buttons and settings of the Qt base menu around its tabs."""

    can_transfer: bool
    can_plan_transport: bool
    can_attack_airfield: bool
    #: Label of the cheat when it is on ("Capture", "Destroy runway"...).
    cheat_capture: Optional[str]
    cheat_runway: Optional[str]
    #: None when the base has no radio setting.
    radios: Optional[BaseRadiosJs]

    class Config:
        title = "BaseActions"

    @staticmethod
    def for_control_point(game: Game, cp: ControlPoint) -> BaseActionsJs:
        return BaseActionsJs(
            can_transfer=can_transfer_units(game, cp),
            can_plan_transport=can_plan_transport_mission(cp),
            can_attack_airfield=can_attack_airfield(cp),
            cheat_capture=cheat_capture_label(game, cp),
            cheat_runway=cheat_runway_label(game, cp),
            radios=(
                BaseRadiosJs.for_control_point(game, cp) if has_radios(cp) else None
            ),
        )

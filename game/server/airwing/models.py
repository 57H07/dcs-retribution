"""Air wing screen (WEB-03): read model of the Qt `AirWingDialog` and `SquadronDialog`.

The engine decides everything shown here, including what a command would refuse: the
client only lays it out. The rules are in `game.commands.squadrons`.
"""

from __future__ import annotations

from typing import Iterator, Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.ato.flighttype import FlightType
from game.commands import (
    LiveryChoice,
    TransferDestination,
    leave_refusal,
    new_pilot_refusal,
    player_flag_refusal,
    room_at_base,
    squadron_repair_id,
)
from game.sidc import (
    StandardIdentity,
    Status,
    SymbolIdentificationCode,
    SymbolSet,
)
from game.squadrons.pilot import PilotStatus
from game.theater.player import Player
from ..controlpoints.aircraftorders import SquadronOrderRowJs

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight
    from game.coalition import Coalition
    from game.squadrons import Pilot, Squadron
    from game.theater import ControlPoint


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _return_turn(game: Game, pilot: Pilot) -> Optional[int]:
    if pilot.status is not PilotStatus.Recovering:
        return None
    return game.turn + pilot.turns_until_available


def _status(game: Game, pilot: Pilot) -> tuple[str, str]:
    """The kind of status (for its colour) and its text."""
    status = pilot.status
    if status is PilotStatus.Active:
        return "ready", "Ready"
    if status is PilotStatus.OnLeave:
        return "leave", "On leave"
    if status is PilotStatus.Downed:
        return "down", "Down · awaiting CSAR"
    if status is PilotStatus.PrisonerOfWar:
        return "prisoner", "Prisoner of war"
    if status is PilotStatus.Recovering:
        return "injured", f"Medical · back T{_return_turn(game, pilot):02d}"
    return "dead", "Killed in action"


def _downed_note(coalition: Coalition, pilot: Pilot) -> str:
    downed = next((d for d in coalition.downed_pilots if d.pilot is pilot), None)
    if downed is None:
        return ""
    time_left = f"{_plural(downed.turns_remaining, 'turn')} left"
    rescue_planned = any(p.target is downed for p in coalition.ato.packages)
    return f"{time_left}, rescue planned" if rescue_planned else time_left


def _note(game: Game, coalition: Coalition, pilot: Pilot) -> str:
    if pilot.status is PilotStatus.Downed:
        return _downed_note(coalition, pilot)
    if pilot.status is PilotStatus.PrisonerOfWar:
        held_at = next(
            (cp for cp in game.theater.controlpoints if cp.id == pilot.held_at), None
        )
        return f"Held at {held_at.name}" if held_at is not None else ""
    rank = pilot.record.rank
    return rank.name if rank is not None else ""


class PilotJs(BaseModel):
    id: UUID
    name: str
    player: bool
    alive: bool
    #: ready, leave, down, prisoner, injured or dead.
    status: str
    status_text: str
    #: Turn an injured pilot is back on duty.
    return_turn: Optional[int]
    note: str
    #: DCS skill the pilot flies at.
    skill: str
    sorties: int
    kills: int
    #: Why the player box is locked; null when it can change.
    player_refusal: Optional[str]
    #: Why the leave button is locked; null when it can change.
    leave_refusal: Optional[str]
    on_leave: bool

    class Config:
        title = "AirWingPilot"

    @staticmethod
    def for_pilot(game: Game, squadron: Squadron, pilot: Pilot) -> PilotJs:
        kind, text = _status(game, pilot)
        return PilotJs(
            id=pilot.id,
            name=pilot.name,
            player=pilot.player,
            alive=pilot.alive,
            status=kind,
            status_text=text,
            return_turn=_return_turn(game, pilot),
            note=_note(game, squadron.coalition, pilot),
            skill=squadron.pilot_skill(pilot).value,
            sorties=pilot.record.sorties,
            kills=pilot.record.total_kills,
            player_refusal=player_flag_refusal(squadron, pilot),
            leave_refusal=leave_refusal(squadron, pilot),
            on_leave=pilot.on_leave,
        )


class AllowedTaskJs(BaseModel):
    task: str
    #: The autoplanner may use the squadron for it.
    auto_assign: bool

    class Config:
        title = "AllowedTask"


class SquadronRepairJs(BaseModel):
    """The expedited repair: `POST /control-points/{cp}/repairs/{repair_id}`."""

    repair_id: str
    cost: float
    affordable: bool

    class Config:
        title = "SquadronRepair"


def _next_turn(squadron: Squadron) -> Iterator[str]:
    if squadron.destination is not None:
        yield f"Transfers to {squadron.destination.name}"
    pending = squadron.pending_deliveries
    if pending > 0:
        yield f"{pending} aircraft arriving"
    elif pending < 0:
        yield f"{-pending} aircraft sold"
    repaired = sum(count for count, turns in squadron.maintenance_batches if turns <= 1)
    if repaired > 0:
        yield f"{repaired} aircraft back from repairs"
    medical = [p for p in squadron.recovering_pilots if p.turns_until_available <= 1]
    if medical:
        yield f"{_plural(len(medical), 'pilot')} back from medical"
    if squadron.pilot_limits_enabled and squadron.replenish_count > 0:
        yield f"{_plural(squadron.replenish_count, 'new pilot')} joining"


def _repair(squadron: Squadron) -> Optional[SquadronRepairJs]:
    if not (
        squadron.player.is_blue
        and squadron.settings.expedited_aircraft_repair
        and squadron.aircraft_in_maintenance
    ):
        return None
    cost = squadron.expedited_repair_cost
    return SquadronRepairJs(
        repair_id=squadron_repair_id(squadron),
        cost=cost,
        affordable=cost <= squadron.coalition.budget,
    )


def _sidc(squadron: Squadron) -> str:
    return str(
        SymbolIdentificationCode(
            standard_identity=(
                StandardIdentity.FRIEND
                if squadron.player.is_blue
                else StandardIdentity.HOSTILE_FAKER
            ),
            symbol_set=SymbolSet.AIR,
            status=Status.PRESENT,
            entity=squadron.primary_task.entity_type,
        )
    )


class SquadronJs(BaseModel):
    id: UUID
    #: With the nickname.
    name: str
    nickname: Optional[str]
    aircraft: str
    sidc: str
    base_id: UUID
    base: str
    #: Base of the transfer in progress.
    destination: Optional[str]

    owned: int
    #: Most aircraft the squadron may hold; null without the limits setting.
    max_aircraft: Optional[int]
    initial: int
    purchased: int
    destroyed: int
    available: int
    untasked_crewed: int
    in_maintenance: int
    maintenance_text: str
    #: Expedited repair on offer; null without the setting or anything to repair.
    repair: Optional[SquadronRepairJs]

    pilots_ready: int
    pilots_alive: int
    #: Sorties and kills of the whole roster, the fallen included.
    sorties: int
    kills: int
    #: What changes for this squadron at the end of the turn.
    next_turn: list[str]

    primary_task: str
    #: Every task the aircraft can fly, in the game's order.
    tasks: list[AllowedTaskJs]

    #: Aircraft orders for this squadron; null for an enemy squadron.
    order: Optional[SquadronOrderRowJs]
    parking_room: int

    #: Why no player pilot can join; null when one can.
    new_pilot_refusal: Optional[str]
    #: Living pilots first.
    pilots: list[PilotJs]

    class Config:
        title = "AirWingSquadron"

    @staticmethod
    def for_squadron(game: Game, squadron: Squadron) -> SquadronJs:
        limited = squadron.settings.enable_squadron_aircraft_limits
        roster = sorted(squadron.current_roster, key=lambda p: not p.alive)
        return SquadronJs(
            id=squadron.id,
            name=str(squadron),
            nickname=squadron.nickname,
            aircraft=squadron.aircraft.display_name,
            sidc=_sidc(squadron),
            base_id=squadron.location.id,
            base=squadron.location.name,
            destination=(
                squadron.destination.name if squadron.destination is not None else None
            ),
            owned=squadron.owned_aircraft,
            max_aircraft=squadron.max_size if limited else None,
            initial=squadron.initial_aircraft,
            purchased=squadron.purchased_aircraft,
            destroyed=squadron.destroyed_aircraft,
            available=squadron.available_aircraft,
            untasked_crewed=squadron.untasked_crewed_aircraft,
            in_maintenance=squadron.aircraft_in_maintenance,
            maintenance_text=squadron.maintenance_text,
            repair=_repair(squadron),
            pilots_ready=len(squadron.active_pilots),
            pilots_alive=len(squadron.living_pilots),
            sorties=sum(p.record.sorties for p in roster),
            kills=sum(p.record.total_kills for p in roster),
            next_turn=list(_next_turn(squadron)),
            primary_task=squadron.primary_task.value,
            tasks=[
                AllowedTaskJs(
                    task=task.value,
                    auto_assign=task in squadron.auto_assignable_mission_types,
                )
                for task in FlightType
                if squadron.capable_of(task)
            ],
            order=(
                SquadronOrderRowJs.for_squadron(squadron.location, squadron)
                if squadron.player.is_blue and squadron.location.captured.is_blue
                else None
            ),
            parking_room=room_at_base(squadron),
            new_pilot_refusal=new_pilot_refusal(squadron),
            pilots=[PilotJs.for_pilot(game, squadron, p) for p in roster],
        )


class AirWingBaseJs(BaseModel):
    id: UUID
    name: str
    squadrons: list[SquadronJs]

    class Config:
        title = "AirWingBase"


class InventoryRowJs(BaseModel):
    """One aircraft of the Aircraft view."""

    key: str
    base: str
    aircraft: str
    #: Task of its flight, "Idle" or "In maintenance (2 turns)".
    task: str
    target: str
    pilot: str
    #: "Player", "AI", or "N/A" without a pilot.
    crew: str
    #: Part of a flight of the ATO.
    allocated: bool

    class Config:
        title = "InventoryRow"


def _allocated_rows(flight: Flight) -> Iterator[InventoryRowJs]:
    for index in range(flight.count):
        pilot = flight.roster.pilot_at(index)
        crew = "" if pilot is None else ("Player" if pilot.player else "AI")
        yield InventoryRowJs(
            key=f"{flight.id}-{index}",
            base=flight.departure.name,
            aircraft=flight.unit_type.display_name,
            task=flight.flight_type.value,
            target=flight.package.target.name,
            pilot="Unassigned" if pilot is None else pilot.name,
            crew=crew,
            allocated=True,
        )


def _unallocated_rows(squadron: Squadron) -> Iterator[InventoryRowJs]:
    def row(key: str, task: str) -> InventoryRowJs:
        return InventoryRowJs(
            key=f"{squadron.id}-{key}",
            base=squadron.location.name,
            aircraft=squadron.aircraft.display_name,
            task=task,
            target="N/A",
            pilot="N/A",
            crew="N/A",
            allocated=False,
        )

    for index in range(squadron.untasked_aircraft):
        yield row(f"idle-{index}", "Idle")
    for batch, (count, turns) in enumerate(squadron.maintenance_summary):
        for index in range(count):
            yield row(
                f"repair-{batch}-{index}",
                f"In maintenance ({_plural(turns, 'turn')})",
            )


def _by_aircraft_and_name(squadron: Squadron) -> tuple[str, str]:
    return squadron.aircraft.display_name, squadron.name


class AirWingJs(BaseModel):
    #: The player's coalition, or the enemy's.
    blue: bool
    squadron_count: int
    aircraft_count: int
    pilot_count: int
    #: Squadrons grouped by base, by base name.
    bases: list[AirWingBaseJs]
    #: One row per aircraft: unallocated first, then the ATO.
    inventory: list[InventoryRowJs]

    class Config:
        title = "AirWing"

    @staticmethod
    def for_coalition(game: Game, player: Player) -> AirWingJs:
        coalition = game.coalition_for(player)
        squadrons = list(coalition.air_wing.iter_squadrons())
        by_base: dict[ControlPoint, list[Squadron]] = {}
        for squadron in squadrons:
            by_base.setdefault(squadron.location, []).append(squadron)
        return AirWingJs(
            blue=player.is_blue,
            squadron_count=len(squadrons),
            aircraft_count=sum(s.owned_aircraft for s in squadrons),
            pilot_count=sum(len(s.living_pilots) for s in squadrons),
            bases=[
                AirWingBaseJs(
                    id=cp.id,
                    name=cp.name,
                    squadrons=[
                        SquadronJs.for_squadron(game, s)
                        for s in sorted(by_base[cp], key=_by_aircraft_and_name)
                    ],
                )
                for cp in sorted(by_base, key=lambda base: base.name)
            ],
            inventory=[row for s in squadrons for row in _unallocated_rows(s)]
            + [
                row
                for package in coalition.ato.packages
                for flight in package.flights
                for row in _allocated_rows(flight)
            ],
        )


class PrimaryTaskJs(BaseModel):
    task: str

    class Config:
        title = "PrimaryTask"


class AutoAssignJs(BaseModel):
    task: str
    enabled: bool

    class Config:
        title = "AutoAssign"


class LiveryChoiceJs(BaseModel):
    label: str
    livery_id: Optional[str]
    use_livery_set: bool
    selected: bool

    class Config:
        title = "LiveryChoice"

    @staticmethod
    def from_choice(choice: LiveryChoice) -> LiveryChoiceJs:
        return LiveryChoiceJs(
            label=choice.label,
            livery_id=choice.livery_id,
            use_livery_set=choice.use_livery_set,
            selected=choice.selected,
        )


class SetLiveryJs(BaseModel):
    livery_id: Optional[str] = None
    use_livery_set: bool = False

    class Config:
        title = "SetLivery"


class SquadronTransferDestinationJs(BaseModel):
    id: UUID
    name: str
    room: int
    #: Why the squadron cannot go there now; null when it can.
    refusal: Optional[str]
    #: Squadrons expected there that may have to start in the air.
    overflow: list[str]
    selected: bool

    class Config:
        title = "SquadronTransferDestination"

    @staticmethod
    def from_destination(
        squadron: Squadron, destination: TransferDestination
    ) -> SquadronTransferDestinationJs:
        return SquadronTransferDestinationJs(
            id=destination.control_point.id,
            name=destination.control_point.name,
            room=destination.room,
            refusal=destination.refusal,
            overflow=[s.name for s in destination.overflow],
            selected=squadron.destination == destination.control_point,
        )


class SquadronTransferOptionsJs(BaseModel):
    #: Free parking slots for the squadron's aircraft at its current base.
    room_here: int
    destinations: list[SquadronTransferDestinationJs]

    class Config:
        title = "SquadronTransferOptions"


class SetDestinationJs(BaseModel):
    #: Null keeps the squadron where it is.
    destination_id: Optional[UUID] = None

    class Config:
        title = "SetDestination"


class PilotUpdateJs(BaseModel):
    """What changes for the pilot; a missing field stays as it is."""

    player: Optional[bool] = None
    on_leave: Optional[bool] = None
    name: Optional[str] = None

    class Config:
        title = "PilotUpdate"


class NewPilotJs(BaseModel):
    name: str

    class Config:
        title = "NewPilot"

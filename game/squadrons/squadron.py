from __future__ import annotations

import logging
import random
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Union
from typing import Optional, Sequence, TYPE_CHECKING
from uuid import uuid4, UUID

from dcs.country import Country
from dcs.unit import Skill
from faker import Faker

from game.ato import Flight, FlightType, Package
from game.settings import AutoAtoBehavior, Settings
from game.theater import ParkingType
from game.theater.player import Player
from .pilot import Pilot, PilotStatus
from .maintenance import MaintenanceBatch, expedited_repair_cost
from .pilotnames import faker_for_country
from ..db.database import Database
from ..radio.radios import RadioFrequency
from ..utils import meters, nautical_miles

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.dcs.aircrafttype import AircraftType
    from game.theater import ControlPoint, MissionTarget
    from .operatingbases import OperatingBases
    from .squadrondef import SquadronDef


@dataclass
class Squadron:
    id: UUID = field(init=False, default_factory=uuid4)

    name: str
    nickname: Optional[str]
    country: Country
    role: str
    aircraft: AircraftType
    max_size: int
    livery: Optional[str]
    livery_set: list[str]  # will override livery if not empty
    primary_task: FlightType
    auto_assignable_mission_types: set[FlightType]
    radio_presets: dict[Union[str, int], list[RadioFrequency]]
    operating_bases: OperatingBases
    female_pilot_percentage: int

    #: The pool of pilots that have not yet been assigned to the squadron. This only
    #: happens when a preset squadron defines more preset pilots than the squadron limit
    #: allows. This pool will be consumed before random pilots are generated.
    pilot_pool: list[Pilot]

    current_roster: list[Pilot] = field(default_factory=list, init=False, hash=False)
    available_pilots: list[Pilot] = field(
        default_factory=list, init=False, hash=False, compare=False
    )

    coalition: Coalition = field(hash=False, compare=False)
    flight_db: Database[Flight] = field(hash=False, compare=False)
    settings: Settings = field(hash=False, compare=False)

    location: ControlPoint
    destination: Optional[ControlPoint] = field(
        init=False, hash=False, compare=False, default=None
    )

    owned_aircraft: int = field(init=False, hash=False, compare=False, default=0)
    untasked_aircraft: int = field(init=False, hash=False, compare=False, default=0)
    pending_deliveries: int = field(init=False, hash=False, compare=False, default=0)

    #: Aircraft the squadron started the campaign with (set at turn 0).
    initial_aircraft: int = field(init=False, hash=False, compare=False, default=0)
    #: Cumulative aircraft lost in combat over the whole campaign.
    destroyed_aircraft: int = field(init=False, hash=False, compare=False, default=0)
    #: Cumulative aircraft purchased and delivered over the whole campaign.
    purchased_aircraft: int = field(init=False, hash=False, compare=False, default=0)

    #: Damaged aircraft under repair (PER-01.2), as ``(count, turns remaining)``.
    #: They stay in ``owned_aircraft`` but cannot be assigned to a flight.
    maintenance_batches: list[MaintenanceBatch] = field(
        init=False, hash=False, compare=False, default_factory=list
    )
    #: Batches added by the mission results of the current turn. Their countdown
    #: starts at the end of this turn, so an aircraft sent for 1 turn misses
    #: exactly the next turn.
    new_maintenance_batches: list[MaintenanceBatch] = field(
        init=False, hash=False, compare=False, default_factory=list
    )

    use_livery_set: bool = False  # if livery-set should be used when present

    #: True once this squadron has been considered for CSAR auto-assignment. Lets
    #: the migrator opt existing squadrons in exactly once, so a player who turns
    #: CSAR back off doesn't have it re-enabled on the next load.
    csar_auto_assign_seeded: bool = field(
        init=False, hash=False, compare=False, default=False
    )

    def __setstate__(self, state: dict[str, Any]) -> None:
        if "id" not in state:
            state["id"] = uuid4()
        if "use_livery_set" not in state:
            state["use_livery_set"] = len(state.get("livery_set", [])) > 0
        if "initial_aircraft" not in state:
            # Best-effort for campaigns started before this counter existed:
            # approximate the starting force with the current owned count.
            state["initial_aircraft"] = state.get("owned_aircraft", 0)
        if "destroyed_aircraft" not in state:
            state["destroyed_aircraft"] = 0
        if "purchased_aircraft" not in state:
            state["purchased_aircraft"] = 0
        if "csar_auto_assign_seeded" not in state:
            # Pre-CSAR save: let the migrator opt this squadron in once.
            state["csar_auto_assign_seeded"] = False
        if "maintenance_batches" not in state:
            state["maintenance_batches"] = []
        if "new_maintenance_batches" not in state:
            state["new_maintenance_batches"] = []
        self.__dict__.update(state)

    def __str__(self) -> str:
        if self.nickname is None:
            return self.name
        return f'{self.name} "{self.nickname}"'

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Squadron):
            return False
        return self.id == other.id

    def __post_init__(self) -> None:
        self._livery_pool: list[str] = []

    @property
    def player(self) -> Player:
        return self.coalition.player

    @property
    def base_skill(self) -> Skill:
        if self.player.is_blue:
            return Skill(self.settings.player_skill)
        return Skill(self.settings.enemy_skill)

    def pilot_skill(self, pilot: Pilot) -> Skill:
        """The effective DCS skill the pilot flies at.

        Pilots level up one skill tier every few missions flown, starting from
        the coalition's base skill and capped at the top tier. Levelling only
        applies when the ``ai_pilot_levelling`` setting is enabled.
        """
        levels = [
            Skill.Average,
            Skill.Good,
            Skill.High,
            Skill.Excellent,
        ]
        current_level = levels.index(self.base_skill)
        missions_for_skill_increase = 4
        increase = pilot.record.missions_flown // missions_for_skill_increase
        capped_increase = min(current_level + increase, len(levels) - 1)

        if self.settings.ai_pilot_levelling:
            new_level = capped_increase
        else:
            new_level = current_level

        return levels[new_level]

    def assign_to_base(self, base: ControlPoint) -> None:
        self.location = base
        logging.debug(f"Assigned {self} to {base}")

    @property
    def pilot_limits_enabled(self) -> bool:
        return self.settings.enable_squadron_pilot_limits

    def random_round_robin_livery_from_set(self) -> str:
        livery = random.choice(self.livery_set)
        self._livery_pool.append(livery)
        self.livery_set.remove(livery)
        if not self.livery_set:
            self.livery_set = self._livery_pool
            self._livery_pool = []
        return livery

    def set_auto_assignable_mission_types(
        self, mission_types: Iterable[FlightType]
    ) -> None:
        self.auto_assignable_mission_types = {
            t for t in mission_types if self.capable_of(t)
        }

    def enable_csar_if_capable(self) -> None:
        """Seeds CSAR into the auto-assignable set for CSAR-capable squadrons.

        Campaign squadron configs (and existing saves) predate CSAR and never list
        it as a secondary task, so without this no squadron would ever auto-plan a
        rescue. This is deliberately *not* folded into
        ``set_auto_assignable_mission_types``, which the Air Wing configuration
        dialog uses to apply the player's explicit choices -- forcing CSAR there
        would make it impossible to turn off. Called once at squadron creation and
        once per squadron by the save migrator instead.
        """
        if self.capable_of(FlightType.CSAR):
            self.auto_assignable_mission_types.add(FlightType.CSAR)

    def claim_new_pilot_if_allowed(self) -> Optional[Pilot]:
        if self.pilot_limits_enabled:
            return None
        self._recruit_pilots(1)
        return self.available_pilots.pop()

    def claim_available_pilot(self) -> Optional[Pilot]:
        if not self.available_pilots:
            return self.claim_new_pilot_if_allowed()

        # For opfor, so player/AI option is irrelevant.
        if self.player != Player.BLUE:
            return self.available_pilots.pop()

        preference = self.settings.auto_ato_behavior

        # No preference, so the first pilot is fine.
        if preference is AutoAtoBehavior.Default:
            return self.available_pilots.pop()

        prefer_players = preference is AutoAtoBehavior.Prefer
        for pilot in self.available_pilots:
            if pilot.player == prefer_players:
                self.available_pilots.remove(pilot)
                return pilot

        # No pilot was found that matched the user's preference.
        #
        # If they chose to *never* assign players and only players remain in the pool,
        # we cannot fill the slot with the available pilots.
        #
        # If they only *prefer* players and we're out of players, just return an AI
        # pilot.
        if not prefer_players:
            return self.claim_new_pilot_if_allowed()
        return self.available_pilots.pop()

    def claim_pilot(self, pilot: Pilot) -> None:
        if pilot not in self.available_pilots:
            raise ValueError(
                f"Cannot assign {pilot} to {self} because they are not available"
            )
        self.available_pilots.remove(pilot)

    def return_pilot(self, pilot: Pilot) -> None:
        self.return_pilots([pilot])

    def return_pilots(self, pilots: Sequence[Pilot]) -> None:
        # Return in reverse so that returning two pilots and then getting two more
        # results in the same ordering. This happens commonly when resetting rosters in
        # the UI, when we clear the roster because the UI is updating, then end up
        # repopulating the same size flight from the same squadron.
        #
        # A pilot that is already free is never added twice: a duplicate would be
        # handed to two flights at once (BUG-05).
        for pilot in reversed(pilots):
            if not any(p is pilot for p in self.available_pilots):
                self.available_pilots.append(pilot)

    def _recruit_pilots(self, count: int) -> None:
        new_pilots = self.pilot_pool[:count]
        self.pilot_pool = self.pilot_pool[count:]
        count -= len(new_pilots)
        # Resolve the squadron's faker once per batch, not once per pilot: the
        # country/locale is fixed for a squadron's lifetime, so hundreds of
        # identical ``faker_for_country`` lookups per campaign collapse to one.
        faker = self.faker
        taken = {p.name for p in self.current_roster} | {p.name for p in new_pilots}
        for _ in range(count):
            female = random.randint(1, 100) <= self.female_pilot_percentage
            name = self._unique_pilot_name(faker, female, taken)
            taken.add(name)
            new_pilots.append(Pilot(name))
        self.current_roster.extend(new_pilots)
        self.available_pilots.extend(new_pilots)

    #: Draws allowed to find a name not yet used in the squadron. Small locales can
    #: run out of combinations, so after this many a namesake is accepted.
    MAX_PILOT_NAME_DRAWS = 20

    @classmethod
    def _unique_pilot_name(cls, faker: Faker, female: bool, taken: set[str]) -> str:
        """A random pilot name, avoiding names already in the squadron (BUG-05)."""
        name = ""
        for _ in range(cls.MAX_PILOT_NAME_DRAWS):
            name = faker.name_female() if female else faker.name_male()
            if name not in taken:
                break
        return name

    def populate_for_turn_0(self, squadrons_start_full: bool) -> None:
        if any(p.status is not PilotStatus.Active for p in self.pilot_pool):
            raise ValueError("Squadrons can only be created with active pilots.")
        self._recruit_pilots(self.settings.squadron_pilot_limit)
        if squadrons_start_full:
            parking_type = ParkingType().from_squadron(self)
            self.owned_aircraft = max(
                0,
                min(self.max_size, self.location.unclaimed_parking(parking_type)),
            )
        self.initial_aircraft = self.owned_aircraft

    def end_turn(self) -> None:
        if self.destination is not None:
            self.relocate_to(self.destination)
        # Advance recovering pilots *before* replenishment so a returning pilot
        # reclaims their slot rather than having it filled by a fresh recruit.
        self._process_pilot_recovery()
        self.replenish_lost_pilots()
        self.process_maintenance()
        self.deliver_orders()

    def _process_pilot_recovery(self) -> None:
        for pilot in self.recovering_pilots:
            pilot.advance_recovery()

    @property
    def aircraft_in_maintenance(self) -> int:
        """Owned aircraft that cannot fly because they are under repair."""
        total = sum(
            count
            for count, _ in self.maintenance_batches + self.new_maintenance_batches
        )
        return min(total, max(self.owned_aircraft, 0))

    @property
    def available_aircraft(self) -> int:
        """Owned aircraft that are not under repair."""
        return max(self.owned_aircraft - self.aircraft_in_maintenance, 0)

    @property
    def maintenance_summary(self) -> list[MaintenanceBatch]:
        """Aircraft under repair grouped by turns remaining, soonest first, as
        ``(count, turns)``. Only owned aircraft are counted."""
        by_turns: dict[int, int] = {}
        for count, turns in self.maintenance_batches + self.new_maintenance_batches:
            if count > 0 and turns > 0:
                by_turns[turns] = by_turns.get(turns, 0) + count
        return [(count, turns) for turns, count in sorted(by_turns.items())]

    @property
    def maintenance_text(self) -> str:
        """Human readable maintenance state, e.g. "2 in maintenance (1 turn), 1 in
        maintenance (3 turns)". Empty when no aircraft is under repair."""
        return ", ".join(
            f"{count} in maintenance ({turns} {'turn' if turns == 1 else 'turns'})"
            for count, turns in self.maintenance_summary
        )

    def send_to_maintenance(self, count: int, turns: int) -> None:
        """Puts ``count`` owned aircraft under repair for the next ``turns`` turns."""
        if count <= 0 or turns <= 0:
            return
        self.new_maintenance_batches.append((count, turns))
        self._trim_maintenance()

    def process_maintenance(self) -> None:
        """Counts down repairs at the end of a turn and releases repaired aircraft."""
        self.maintenance_batches = [
            (count, turns - 1)
            for count, turns in self.maintenance_batches
            if turns > 1 and count > 0
        ] + self.new_maintenance_batches
        self.new_maintenance_batches = []
        self._trim_maintenance()

    def _trim_maintenance(self) -> None:
        """Drops batch entries for aircraft that are no longer owned (lost since),
        newest first."""
        excess = sum(
            c for c, _ in self.maintenance_batches + self.new_maintenance_batches
        ) - max(self.owned_aircraft, 0)
        for batches in (self.new_maintenance_batches, self.maintenance_batches):
            while excess > 0 and batches:
                count, turns = batches.pop()
                removed = min(count, excess)
                excess -= removed
                if count > removed:
                    batches.append((count - removed, turns))

    @property
    def expedited_repair_cost(self) -> int:
        """Cost of finishing every repair of this squadron at once."""
        aircraft_turns = sum(
            count * turns
            for count, turns in self.maintenance_batches + self.new_maintenance_batches
        )
        return expedited_repair_cost(self.aircraft.price, aircraft_turns)

    def expedite_maintenance(self) -> int:
        """Finishes every repair at once and returns the aircraft to the pool of
        untasked aircraft. Payment is the caller's responsibility (see
        ``expedited_repair_cost``). Returns the number of aircraft released."""
        released = self.aircraft_in_maintenance
        self.maintenance_batches = []
        self.new_maintenance_batches = []
        self.untasked_aircraft = min(
            self.untasked_aircraft + released, self.owned_aircraft
        )
        return released

    def buy_expedited_maintenance(self) -> int:
        """Pays ``expedited_repair_cost`` from the coalition's budget and finishes
        every repair at once. Returns the number of aircraft released, 0 when
        nothing is under repair or the budget is too small."""
        cost = self.expedited_repair_cost
        if not self.aircraft_in_maintenance or cost > self.coalition.budget:
            return 0
        self.coalition.budget -= cost
        return self.expedite_maintenance()

    def replenish_lost_pilots(self) -> None:
        if self.pilot_limits_enabled and self.replenish_count > 0:
            self._recruit_pilots(self.replenish_count)

    def return_all_pilots_and_aircraft(self) -> None:
        self.available_pilots = list(self.active_pilots)
        self.untasked_aircraft = self.available_aircraft

    @staticmethod
    def send_on_leave(pilot: Pilot) -> None:
        pilot.send_on_leave()

    def release_prisoner(self, pilot: Pilot, recovery_turns: int) -> bool:
        """Frees a prisoner of war whose base was retaken.

        A prisoner keeps their slot, so they normally go straight into recovery.
        If the squadron is over its limit anyway (the limit was lowered while they
        were held), they are sent on leave instead, which does not count against
        the limit, and can be recalled from leave once a slot frees up. Returns
        whether the pilot went into recovery.
        """
        pilot.release_from_captivity(recovery_turns)
        if self.pilot_limits_enabled and self._number_of_unfilled_pilot_slots < 0:
            pilot.begin_recovery(0)
            pilot.send_on_leave()
            return False
        return True

    def return_from_leave(self, pilot: Pilot) -> None:
        if not self.has_unfilled_pilot_slots:
            raise RuntimeError(
                f"Cannot return {pilot} from leave because {self} is full"
            )
        pilot.return_from_leave()

    def create_player_pilot(self, name: str) -> Pilot:
        """Adds a new player pilot to the roster, ready to be assigned."""
        if not self.has_unfilled_pilot_slots:
            raise RuntimeError(f"Cannot add a pilot to {self} because it is full")
        pilot = Pilot(name, player=True)
        self.current_roster.append(pilot)
        self.available_pilots.append(pilot)
        return pilot

    @property
    def faker(self) -> Faker:
        # Name the squadron's pilots in their own nation's convention (the
        # squadron flies under its own DCS country, #627), falling back to a
        # faker built from the faction's locale list for unmapped /
        # multinational countries. See game/squadrons/pilotnames.py.
        return faker_for_country(self.country, self.coalition.faction.locales)

    def _pilots_with_status(self, status: PilotStatus) -> list[Pilot]:
        return [p for p in self.current_roster if p.status == status]

    def _pilots_without_status(self, status: PilotStatus) -> list[Pilot]:
        return [p for p in self.current_roster if p.status != status]

    @property
    def pilot_limit(self) -> int:
        return self.settings.squadron_pilot_limit

    @property
    def expected_pilots_next_turn(self) -> int:
        return len(self.active_pilots) + self.replenish_count

    @property
    def replenish_count(self) -> int:
        return min(
            self.settings.squadron_replenishment_rate,
            self._number_of_unfilled_pilot_slots,
        )

    @property
    def active_pilots(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.Active)

    @property
    def pilots_on_leave(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.OnLeave)

    @property
    def number_of_pilots_including_inactive(self) -> int:
        return len(self.current_roster)

    @property
    def living_pilots(self) -> list[Pilot]:
        return [p for p in self.current_roster if p.alive]

    @property
    def dead_pilots(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.Dead)

    @property
    def prisoners_of_war(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.PrisonerOfWar)

    @property
    def downed_pilots(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.Downed)

    @property
    def recovering_pilots(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.Recovering)

    @property
    def _number_of_unfilled_pilot_slots(self) -> int:
        # Downed, recovering and captive pilots still hold their roster slot: a
        # downed pilot may be rescued, a recovering one will return and a prisoner
        # is freed when their base is retaken, so we must not recruit a fresh pilot
        # into a slot that may be reclaimed (CSAR-01 requirement 3, #63).
        reserved = (
            len(self.downed_pilots)
            + len(self.recovering_pilots)
            + len(self.prisoners_of_war)
        )
        return self.pilot_limit - len(self.active_pilots) - reserved

    @property
    def number_of_available_pilots(self) -> int:
        return len(self.available_pilots)

    def can_provide_pilots(self, count: int) -> bool:
        return not self.pilot_limits_enabled or self.number_of_available_pilots >= count

    @property
    def has_available_pilots(self) -> bool:
        return not self.pilot_limits_enabled or bool(self.available_pilots)

    @property
    def has_unfilled_pilot_slots(self) -> bool:
        return not self.pilot_limits_enabled or self._number_of_unfilled_pilot_slots > 0

    def capable_of(self, task: FlightType) -> bool:
        """Returns True if the squadron is capable of performing the given task.

        A squadron may be capable of performing a task even if it will not be
        automatically assigned to it.
        """
        return self.aircraft.capable_of(task)

    def can_auto_assign(self, task: FlightType) -> bool:
        # Intersect with airframe capability at read time: a saved/UI-added type the
        # airframe cannot fly is never auto-assignable, even if present in the set.
        return task in self.auto_assignable_mission_types and self.capable_of(task)

    def can_auto_assign_mission(
        self,
        location: MissionTarget,
        task: FlightType,
        size: int,
        heli: bool,
        this_turn: bool,
        ignore_range: bool = False,
    ) -> bool:
        if (
            self.location.cptype.name in ["FOB", "FARP"]
            and not self.aircraft.helicopter
        ):
            # AI harriers can't handle FOBs/FARPs
            # AI has a hard time taking off and will not land back at FOB/FARP
            # thus, disable auto-planning
            return False
        if not self.can_auto_assign(task):
            return False
        if this_turn and not self.can_fulfill_flight(size):
            return False

        if task in [FlightType.ESCORT, FlightType.SEAD_ESCORT]:
            if heli and not self.aircraft.helicopter and not self.aircraft.lha_capable:
                return False
            if not heli and self.aircraft.helicopter:
                return False

        if heli and task == FlightType.REFUELING:
            return False

        if ignore_range:
            return True

        distance_to_target = meters(location.distance_to(self.location))
        max_plane_dist = nautical_miles(
            self.coalition.game.settings.max_mission_range_planes
        )
        max_heli_dist = nautical_miles(
            self.coalition.game.settings.max_mission_range_helicopters
        )
        if self.aircraft.helicopter:
            return distance_to_target <= max(
                self.aircraft.max_mission_range, max_heli_dist
            )
        return distance_to_target <= max(
            self.aircraft.max_mission_range, max_plane_dist
        )

    def operates_from(self, control_point: ControlPoint) -> bool:
        if not control_point.can_operate(self.aircraft):
            return False
        if control_point.is_carrier:
            return self.operating_bases.carrier
        elif control_point.is_lha:
            return self.operating_bases.lha
        else:
            return self.operating_bases.shore

    def pilot_at_index(self, index: int) -> Pilot:
        return self.current_roster[index]

    def claim_inventory(self, count: int) -> None:
        if self.untasked_aircraft < count:
            raise ValueError(
                f"Cannot remove {count} from {self.name}. Only have "
                f"{self.untasked_aircraft}."
            )
        self.untasked_aircraft -= count

    def can_fulfill_flight(self, count: int) -> bool:
        return self.can_provide_pilots(count) and self.untasked_aircraft >= count

    def refund_orders(self, count: Optional[int] = None) -> None:
        if count is None:
            count = self.pending_deliveries
        self.coalition.adjust_budget(self.aircraft.price * count)
        self.pending_deliveries -= count

    def deliver_orders(self) -> None:
        self.cancel_overflow_orders()
        self.purchased_aircraft += self.pending_deliveries
        self.owned_aircraft += self.pending_deliveries
        self.pending_deliveries = 0

    def relocate_to(self, destination: ControlPoint) -> None:
        if not destination.is_friendly(self.coalition.player):
            logging.warning(
                f"Cannot relocate {self} to {destination.name} - destination is no longer friendly. "
                f"Cancelling relocation order."
            )
            self.destination = None
            return
        self.location = destination
        if self.location == self.destination:
            self.destination = None

    def cancel_overflow_orders(self) -> None:
        from game.theater import ParkingType

        if self.pending_deliveries <= 0:
            return
        parking_type = ParkingType().from_aircraft(
            self.aircraft, self.coalition.game.settings.ground_start_ai_planes
        )
        overflow = -self.location.unclaimed_parking(parking_type)
        if overflow > 0:
            sell_count = min(overflow, self.pending_deliveries)
            logging.debug(
                f"{self.location} is overfull by {overflow} aircraft. Cancelling "
                f"orders for {sell_count} aircraft to make room."
            )
            self.refund_orders(sell_count)

    @property
    def max_fulfillable_aircraft(self) -> int:
        return max(self.number_of_available_pilots, self.untasked_aircraft)

    @property
    def untasked_crewed_aircraft(self) -> int:
        """Untasked aircraft that also have a free pilot to fly them — the real number
        launchable this turn. ``untasked_aircraft`` alone can exceed the pilots on hand;
        this caps it. Equals ``untasked_aircraft`` when pilot limits are disabled."""
        if not self.pilot_limits_enabled:
            return self.untasked_aircraft
        return min(self.untasked_aircraft, self.number_of_available_pilots)

    @property
    def expected_size_next_turn(self) -> int:
        return self.owned_aircraft + self.pending_deliveries

    def has_aircraft_capacity_for(self, n: int) -> bool:
        if not self.settings.enable_squadron_aircraft_limits:
            return True
        remaining = self.max_size - self.owned_aircraft - self.pending_deliveries
        return remaining >= n

    @property
    def arrival(self) -> ControlPoint:
        return self.location if self.destination is None else self.destination

    def plan_relocation(self, destination: ControlPoint, now: datetime) -> None:
        from game.theater import ParkingType

        if destination == self.location:
            logging.warning(
                f"Attempted to plan relocation of {self} to current location "
                f"{destination}. Ignoring."
            )
            return
        if destination == self.destination:
            logging.warning(
                f"Attempted to plan relocation of {self} to current destination "
                f"{destination}. Ignoring."
            )
            return

        parking_type = ParkingType().from_squadron(self)
        if self.expected_size_next_turn > destination.unclaimed_parking(parking_type):
            raise RuntimeError(f"Not enough parking for {self} at {destination}.")
        if not destination.can_operate(self.aircraft):
            raise RuntimeError(f"{self} cannot operate at {destination}.")
        self.destination = destination
        self.replan_ferry_flights(now)

    def cancel_relocation(self) -> None:
        from game.theater import ParkingType

        if self.destination is None:
            logging.warning(
                f"Attempted to cancel relocation of squadron with no transfer order. "
                "Ignoring."
            )
            return

        parking_type = ParkingType().from_squadron(self)
        if self.expected_size_next_turn > self.location.unclaimed_parking(parking_type):
            raise RuntimeError(f"Not enough parking for {self} at {self.location}.")
        self.destination = None
        self.cancel_ferry_flights()

    def replan_ferry_flights(self, now: datetime) -> None:
        self.cancel_ferry_flights()
        self.plan_ferry_flights(now)

    def cancel_ferry_flights(self) -> None:
        # Copy both lists: removing from a list while iterating it skips the next
        # element, which left stale ferry flights behind after an empty package
        # (BUG-05).
        for package in list(self.coalition.ato.packages):
            for flight in list(package.flights):
                if flight.squadron == self and flight.flight_type is FlightType.FERRY:
                    package.remove_flight(flight)
            if not package.flights:
                self.coalition.ato.remove_package(package)

    def plan_ferry_flights(self, now: datetime) -> None:
        if self.destination is None:
            raise RuntimeError(
                f"Cannot plan ferry flights for {self} because there is no destination."
            )
        remaining = self.untasked_aircraft
        if not remaining:
            return

        package = Package(self.destination, self.flight_db)
        while remaining:
            size = min(remaining, self.aircraft.max_group_size)
            self.plan_ferry_flight(package, size)
            remaining -= size
        package.set_tot_asap(now)
        self.coalition.ato.add_package(package)

    def plan_ferry_flight(self, package: Package, size: int) -> None:
        start_type = self.location.required_aircraft_start_type
        if start_type is None:
            start_type = self.settings.default_start_type

        flight = Flight(
            package,
            self,
            size,
            FlightType.FERRY,
            start_type,
            divert=None,
        )
        package.add_flight(flight)
        flight.recreate_flight_plan()

    @classmethod
    def create_from(
        cls,
        squadron_def: SquadronDef,
        primary_task: FlightType,
        max_size: int,
        base: ControlPoint,
        coalition: Coalition,
        game: Game,
    ) -> Squadron:
        squadron_def.claimed = True
        return Squadron(
            squadron_def.name,
            squadron_def.nickname,
            squadron_def.country,
            squadron_def.role,
            squadron_def.aircraft,
            max_size,
            squadron_def.livery,
            squadron_def.livery_set,
            primary_task,
            squadron_def.auto_assignable_mission_types,
            squadron_def.radio_presets,
            squadron_def.operating_bases,
            squadron_def.female_pilot_percentage,
            squadron_def.pilot_pool,
            coalition,
            game.db.flights,
            game.settings,
            base,
        )

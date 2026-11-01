"""Air wing configuration (WEB-06): the rules of the Qt `AirWingConfigurationDialog`.

It works on a `Game` of a new campaign before turn 0 starts, or on the campaign in
play when the "Enable Air Wing adjustments" cheat is on. There is no save step: each
command applies at once. A command that changes which aircraft stand where replans the
coalition's turn in a campaign already under way, as the Qt dialog does on Accept.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

import yaml
from dcs import Point

from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType
from game.squadrons.pilot import Pilot
from game.theater.controlpoint import Airfield, ParkingType
from .errors import CommandError

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.squadrons import Squadron
    from game.squadrons.squadrondef import SquadronDef
    from game.theater import ControlPoint


def _replan_if_under_way(game: Game, coalition: Coalition) -> None:
    from game.server import EventStream
    from game.sim import GameUpdateEvents

    if game.turn == 0:
        return
    coalition.initialize_turn(False)
    EventStream.put_nowait(GameUpdateEvents().begin_new_turn())


# --- What can be chosen --------------------------------------------------------


def possible_bases(coalition: Coalition, aircraft: AircraftType) -> list[ControlPoint]:
    """Where a squadron of this aircraft may be based, by name."""
    return sorted(
        (
            base
            for base in coalition.game.theater.control_points_for(coalition.player)
            if base.can_operate(aircraft) or isinstance(base, Airfield)
        ),
        key=lambda base: base.name,
    )


def possible_aircraft(coalition: Coalition) -> list[AircraftType]:
    """What a new squadron may fly: an aircraft of the faction with a usable base."""
    bases = list(coalition.game.theater.control_points_for(coalition.player))
    return sorted(
        (
            aircraft
            for aircraft in coalition.faction.all_aircrafts
            if isinstance(aircraft, AircraftType)
            and any(base.can_operate(aircraft) for base in bases)
        ),
        key=lambda aircraft: aircraft.display_name,
    )


def presets_for(coalition: Coalition, aircraft: AircraftType) -> list[SquadronDef]:
    """The squadron definitions of this aircraft that no squadron uses yet."""
    return sorted(
        (
            squadron_def
            for squadron_def in coalition.air_wing.squadron_defs.get(aircraft, [])
            if not squadron_def.claimed
        ),
        key=lambda squadron_def: squadron_def.name,
    )


def primary_tasks(aircraft: AircraftType) -> list[FlightType]:
    return sorted(aircraft.iter_task_capabilities(), key=lambda task: task.value)


@dataclass(frozen=True)
class ParkingInfo:
    #: Aircraft that may stand at the base: the squadrons' sizes added up.
    required: int
    total: int
    #: Slots of the airfield this aircraft fits in; None without an airfield.
    fitting: Optional[int]


def parking_at_base(game: Game, squadron: Squadron) -> ParkingInfo:
    base = squadron.location
    required = sum(
        other.max_size
        for other in squadron.coalition.air_wing.iter_squadrons()
        if other.location == base
    )
    fitting = None
    if (airport := base.dcs_airport) is not None:
        fitting = len(airport.free_parking_slots(squadron.aircraft.dcs_unit_type))
    return ParkingInfo(
        required,
        base.total_aircraft_parking(
            ParkingType().from_aircraft(
                squadron.aircraft, game.settings.ground_start_ai_planes
            )
        ),
        fitting,
    )


def player_names_refusal(squadron: Squadron) -> Optional[str]:
    """Why this squadron cannot have player pilots; None when it can."""
    if not squadron.aircraft.flyable:
        return "Player slots not available for non-flyable aircraft"
    if not squadron.player.is_blue:
        return "Player slots not available for opfor"
    return None


def player_names(squadron: Squadron) -> list[str]:
    return [pilot.name for pilot in squadron.pilot_pool if pilot.player]


# --- Commands ------------------------------------------------------------------


def rename_squadron(squadron: Squadron, name: str) -> None:
    cleaned = name.strip()
    if not cleaned:
        raise CommandError("A squadron needs a name.")
    squadron.name = cleaned


def set_nickname(squadron: Squadron, nickname: str) -> None:
    squadron.nickname = nickname.strip()


def reroll_nickname(squadron: Squadron) -> None:
    generator = squadron.coalition.air_wing.squadron_def_generator
    squadron.nickname = generator.random_nickname()


def set_max_size(squadron: Squadron, size: int) -> None:
    if size < 1:
        raise CommandError("A squadron holds at least one aircraft.")
    squadron.max_size = size


def set_player_names(squadron: Squadron, names: list[str]) -> None:
    """Replaces the pilots flown by players with these names, first in the pool."""
    cleaned = [name.strip() for name in names if name.strip()]
    refusal = player_names_refusal(squadron)
    if refusal is not None and cleaned:
        raise CommandError(refusal)
    others = [pilot for pilot in squadron.pilot_pool if not pilot.player]
    squadron.pilot_pool = [Pilot(name, player=True) for name in cleaned] + others


def move_to_base(game: Game, squadron: Squadron, base: ControlPoint) -> None:
    """Changes the home base of the squadron, at once and for free.

    Raises:
        CommandError: the base is not one of `possible_bases`.
    """
    if base not in possible_bases(squadron.coalition, squadron.aircraft):
        raise CommandError(f"{squadron.aircraft} cannot be based at {base.name}.")
    squadron.assign_to_base(base)
    _replan_if_under_way(game, squadron.coalition)


def _preset_named(
    coalition: Coalition, aircraft: AircraftType, preset: str
) -> SquadronDef:
    for squadron_def in presets_for(coalition, aircraft):
        if squadron_def.name == preset:
            return squadron_def
    raise CommandError(f"The squadron {preset} is not available.")


def add_squadron(
    game: Game,
    coalition: Coalition,
    aircraft: AircraftType,
    base: ControlPoint,
    task: FlightType,
    preset: Optional[str],
) -> Squadron:
    """Adds a squadron with the default size.

    Args:
        preset: name of one of `presets_for`; None generates a squadron.

    Raises:
        CommandError: a choice the coalition does not offer.
    """
    from game.campaignloader.campaignairwingconfig import DEFAULT_SQUADRON_SIZE
    from game.squadrons import Squadron

    if aircraft not in possible_aircraft(coalition):
        raise CommandError(f"{aircraft} cannot join this air wing.")
    if base not in possible_bases(coalition, aircraft):
        raise CommandError(f"{aircraft} cannot be based at {base.name}.")
    if task not in primary_tasks(aircraft):
        raise CommandError(f"{aircraft} cannot fly {task.value}.")
    squadron_def = (
        _preset_named(coalition, aircraft, preset)
        if preset is not None
        else coalition.air_wing.squadron_def_generator.generate_for_aircraft(aircraft)
    )
    squadron = Squadron.create_from(
        squadron_def, task, DEFAULT_SQUADRON_SIZE, base, coalition, game
    )
    coalition.air_wing.add_squadron(squadron)
    if game.turn != 0:
        # The turn 0 setup this squadron missed: its pilots, and no aircraft.
        squadron.populate_for_turn_0(squadrons_start_full=False)
    _replan_if_under_way(game, coalition)
    return squadron


def remove_squadron(game: Game, squadron: Squadron) -> None:
    coalition = squadron.coalition
    squadrons = coalition.air_wing.squadrons
    remaining = [s for s in squadrons[squadron.aircraft] if s is not squadron]
    if remaining:
        squadrons[squadron.aircraft] = remaining
    else:
        del squadrons[squadron.aircraft]
    coalition.air_wing.unclaim_squadron_def(squadron)
    _replan_if_under_way(game, coalition)


def replace_with_preset(game: Game, squadron: Squadron, preset: str) -> Squadron:
    """Swaps the squadron for a preset: same task, size and base; players stay.

    Raises:
        CommandError: the preset is not one of `presets_for`.
    """
    from game.squadrons import Squadron

    coalition = squadron.coalition
    selected = _preset_named(coalition, squadron.aircraft, preset)
    coalition.air_wing.unclaim_squadron_def(squadron)
    replacement = Squadron.create_from(
        selected,
        squadron.primary_task,
        squadron.max_size,
        squadron.location,
        coalition,
        game,
    )
    replacement.pilot_pool = [
        pilot for pilot in squadron.pilot_pool if pilot.player
    ] + replacement.pilot_pool
    squadrons = coalition.air_wing.squadrons[squadron.aircraft]
    squadrons[squadrons.index(squadron)] = replacement
    if game.turn != 0:
        replacement.populate_for_turn_0(squadrons_start_full=False)
    _replan_if_under_way(game, coalition)
    return replacement


# --- The faction ---------------------------------------------------------------


def add_faction_unit(coalition: Coalition, group_key: str, unit_name: str) -> None:
    """Adds a unit to the faction; a preset group joins its armed forces too."""
    from game.armedforces.armedforces import ArmedForces
    from .newgame import add_unit_to_faction

    add_unit_to_faction(coalition.faction, group_key, unit_name)
    if group_key == "preset_groups":
        coalition.armed_forces = ArmedForces(coalition.faction)


# --- Files ---------------------------------------------------------------------


def air_wing_as_config(coalition: Coalition) -> dict[Any, list[dict[str, Any]]]:
    """The coalition's squadrons in the `squadrons:` format of a campaign YAML."""
    config: dict[Any, list[dict[str, Any]]] = {}
    defs = coalition.air_wing.squadron_defs
    for aircraft, squadrons in coalition.air_wing.squadrons.items():
        for squadron in squadrons:
            at = squadron.location.at
            key = squadron.location.full_name if isinstance(at, Point) else at.id
            presets = [squadron_def.name for squadron_def in defs.get(aircraft, [])]
            name = (
                squadron.name
                if squadron.name in presets
                else squadron.aircraft.variant_id
            )
            config.setdefault(key, []).append(
                {
                    "primary": squadron.primary_task.value,
                    "secondary": [
                        task.value
                        for task in squadron.auto_assignable_mission_types
                        if task.value != squadron.primary_task.value
                    ],
                    "aircraft": [name],
                    "aircraft_type": squadron.aircraft.display_name,
                    "size": squadron.max_size,
                }
            )
    return config


def save_air_wing(coalition: Coalition, path: Path) -> None:
    try:
        with path.open("w", encoding="utf-8") as file:
            file.write(yaml.dump(air_wing_as_config(coalition)))
    except OSError as error:
        raise CommandError(f"Could not write {path}: {error}", status_code=500)


def load_air_wing(game: Game, coalition: Coalition, path: Path) -> None:
    """Replaces the coalition's squadrons with those of an air wing file.

    Raises:
        CommandError: the file cannot be read.
    """
    from game.campaignloader.campaignairwingconfig import CampaignAirWingConfig

    try:
        with path.open(encoding="utf-8") as file:
            data = yaml.safe_load(file)
        config = CampaignAirWingConfig.from_campaign_data(data, game.theater)
    except (OSError, yaml.YAMLError, KeyError, TypeError, AttributeError) as error:
        raise CommandError(f"Could not read the air wing file {path}: {error}")
    for squadrons in coalition.air_wing.squadrons.values():
        for squadron in squadrons:
            coalition.air_wing.unclaim_squadron_def(squadron)
    coalition.air_wing.squadrons = defaultdict(list)
    coalition.configure_default_air_wing(config)
    if game.turn != 0:
        for squadron in coalition.air_wing.iter_squadrons():
            squadron.populate_for_turn_0(squadrons_start_full=False)
    _replan_if_under_way(game, coalition)

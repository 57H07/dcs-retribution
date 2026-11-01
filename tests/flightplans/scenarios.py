"""Planning scenarios replayed on the reference game (W16).

Each scenario creates one blue package through the engine commands of the web
editor (WEB-04.1), which the Qt dialogs share:

* ``plan_manual``: ``create_package``, then ``add_flight`` for each flight.
* ``plan_auto``: ``create_package``, then ``auto_create``.

The references were produced by the Qt call sequence before those commands
existed (see ``README.md``). They must stay as they are.

Targets are chosen by structure (closest enemy SAM, the only front line, ...)
rather than by generated name, and ties are broken by name, so the selection
is stable for a given seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, TypeVar

from dcs.mapping import Point

from game import Game
from game.ato import FlightType, Package
from game.commander.missionproposals import ProposedFlight
from game.commands.packageflights import add_flight, auto_create
from game.commands.packages import create_package
from game.squadrons import Squadron
from game.squadrons.csarplacement import find_downed_pilot_position
from game.squadrons.downedpilot import DownedPilot
from game.theater import ControlPoint, MissionTarget
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    SamGroundObject,
    TheaterGroundObject,
    VehicleGroupGroundObject,
)
from tests.flightplans.referencegame import seed_all

#: Seeds :mod:`random` again before planning, so planning does not depend on how
#: many numbers generation drew.
PLANNING_SEED = 1304

T = TypeVar("T")
TgoT = TypeVar("TgoT", bound=TheaterGroundObject)


@dataclass(frozen=True)
class FlightRequest:
    task: FlightType
    aircraft: str
    count: int


def _squadron(game: Game, aircraft: str) -> Squadron:
    for squadron in game.blue.air_wing.iter_squadrons():
        if squadron.aircraft.display_name == aircraft:
            return squadron
    raise KeyError(f"No blue squadron flies {aircraft}")


def plan_manual(
    game: Game, target: MissionTarget, requests: Iterable[FlightRequest]
) -> Package:
    now = game.conditions.start_time
    package = create_package(game, target, now)
    for request in requests:
        add_flight(
            game,
            package,
            request.task,
            _squadron(game, request.aircraft),
            request.count,
            now,
        )
    return package


def plan_auto(
    game: Game, target: MissionTarget, flights: Iterable[ProposedFlight]
) -> Package:
    now = game.conditions.start_time
    return auto_create(game, create_package(game, target, now), list(flights), now)


def _closest(
    candidates: Iterable[T], origin: Point, position: Callable[[T], Point]
) -> T:
    return min(
        candidates,
        key=lambda c: (position(c).distance_to_point(origin), str(c)),
    )


def _enemy_tgos(game: Game, kind: type[TgoT]) -> list[TgoT]:
    return [
        tgo
        for tgo in game.theater.ground_objects
        if isinstance(tgo, kind)
        and not tgo.is_friendly(game.blue.player)
        and not tgo.is_dead
    ]


def _home(game: Game) -> ControlPoint:
    return game.theater.control_point_named("Ramat David")


def _sams_by_distance(game: Game) -> list[SamGroundObject]:
    origin = _home(game).position
    return sorted(
        _enemy_tgos(game, SamGroundObject),
        key=lambda t: (t.position.distance_to_point(origin), t.name),
    )


def _downed_pilot(game: Game) -> DownedPilot:
    """A blue pilot down between the front line and Golan South."""
    squadron = _squadron(game, "F-16CM Fighting Falcon (Block 50)")
    pilot = squadron.claim_available_pilot()
    assert pilot is not None
    front = next(iter(game.theater.conflicts()))
    base = game.theater.control_point_named("Golan South")
    near = base.position.lerp(front.position, 0.5)
    position = find_downed_pilot_position(game.theater, near)
    assert position is not None
    downed = DownedPilot(
        pilot=pilot,
        squadron=squadron,
        _position=position,
        player=squadron.player,
        turn_downed=game.turn,
        turns_remaining=3,
        was_player=False,
        aircraft_name=squadron.aircraft.display_name,
        in_water=game.theater.is_in_sea(position),
    )
    pilot.go_down()
    game.blue.downed_pilots.append(downed)
    game.db.downed_pilots.add(downed.id, downed)
    return downed


F15C = "F-15C Eagle"
F4E = "F-4E Phantom II"
F15E = "F-15E Strike Eagle (AI)"
F16 = "F-16CM Fighting Falcon (Block 50)"
AH1W = "AH-1W SuperCobra"
UH1H = "UH-1H Iroquois"


def plan_reference_packages(game: Game) -> dict[str, Package]:
    """Plans every scenario, in a fixed order, and returns them by name.

    All scenarios are planned together because each one claims aircraft and
    pilots that the next one can no longer use.
    """
    seed_all(PLANNING_SEED)
    sams = _sams_by_distance(game)
    front = next(iter(game.theater.conflicts()))
    packages: dict[str, Package] = {}

    packages["barcap"] = plan_manual(
        game, _home(game), [FlightRequest(FlightType.BARCAP, F15C, 2)]
    )
    packages["cas"] = plan_manual(game, front, [FlightRequest(FlightType.CAS, AH1W, 2)])
    packages["sead"] = plan_manual(
        game, sams[0], [FlightRequest(FlightType.SEAD, F16, 2)]
    )
    packages["dead"] = plan_manual(
        game,
        sams[1],
        [
            FlightRequest(FlightType.DEAD, F4E, 2),
            FlightRequest(FlightType.SEAD_ESCORT, F16, 2),
        ],
    )
    packages["strike_escort"] = plan_manual(
        game,
        _closest(
            _enemy_tgos(game, BuildingGroundObject),
            _home(game).position,
            lambda t: t.position,
        ),
        [
            FlightRequest(FlightType.STRIKE, F15E, 2),
            FlightRequest(FlightType.ESCORT, F15C, 2),
        ],
    )
    packages["csar"] = plan_manual(
        game, _downed_pilot(game), [FlightRequest(FlightType.CSAR, UH1H, 1)]
    )
    packages["auto_bai"] = plan_auto(
        game,
        _closest(
            _enemy_tgos(game, VehicleGroupGroundObject),
            front.position,
            lambda t: t.position,
        ),
        [ProposedFlight(FlightType.BAI, 2)],
    )
    return packages


def scenario_names() -> list[str]:
    return ["barcap", "cas", "sead", "dead", "strike_escort", "csar", "auto_bai"]

from game.gamelock import locked
from fastapi import APIRouter, Depends

from game import Game
from game.commands import (
    CommandError,
    fix_past_tots,
    generate_mission,
    set_sim_speed,
    skip_turn,
)
from game.commands.mission import describe_package
from game.server import EventStream, GameContext
from .models import CampaignStateJs, GameJs, TurnJs
from .timeline import TimelineJs
from .topbar import (
    FixedTotsJs,
    MissionChecksJs,
    MissionJs,
    SimJs,
    SimSpeedChangeJs,
    SimSpeedJs,
    TopBarJs,
)
from ..commanderrors import command_error_responses
from ..dependencies import QtCallbacks, QtContext, UiOptions
from ..missionresult import MissionResultContext

router: APIRouter = APIRouter(prefix="/game")


def _require_game(game: Game | None) -> Game:
    if game is None:
        raise CommandError("No campaign is loaded.")
    return game


@router.get("/", operation_id="get_game_state", response_model=GameJs)
@locked
def game_state(game: Game | None = Depends(GameContext.get)) -> GameJs | None:
    if game is None:
        return None
    return GameJs.from_game(game)


@router.get("/top-bar", operation_id="get_top_bar", response_model=TopBarJs | None)
@locked
def top_bar(game: Game | None = Depends(GameContext.get)) -> TopBarJs | None:
    """What the top bar and the turn buttons show; null without a campaign."""
    if game is None:
        return None
    sim = GameContext.get_sim()
    return TopBarJs.from_game(
        game,
        sim.simulation_speed,
        sim.current_time_in_sim_if_game_loaded,
        UiOptions.show_sim_speed_controls,
    )


@router.get("/timeline", operation_id="get_timeline", response_model=TimelineJs | None)
@locked
def timeline(game: Game | None = Depends(GameContext.get)) -> TimelineJs | None:
    """Friendly packages on the mission time axis (startup, TOT, landing); null
    without a campaign."""
    if game is None:
        return None
    return TimelineJs.for_game(game)


@router.post(
    "/turn/pass",
    operation_id="pass_turn",
    response_model=TurnJs,
    responses=command_error_responses("No campaign is loaded, or it is over."),
)
@locked
def pass_turn(
    game: Game | None = Depends(GameContext.get),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> TurnJs:
    """Skip the current turn without flying it ("Pass Turn" / "Begin Campaign").

    The new turn is published on the event stream (`new_turn`), so every open screen
    reloads its state.
    """
    game = _require_game(game)
    state = skip_turn(game)
    if qt is not None and qt.turn_passed is not None:
        qt.turn_passed(state)
    return TurnJs(turn=game.turn, campaign_state=CampaignStateJs.from_turn_state(state))


@router.get(
    "/mission/checks",
    operation_id="get_mission_checks",
    response_model=MissionChecksJs,
    responses=command_error_responses("No campaign is loaded."),
)
@locked
def mission_checks(game: Game | None = Depends(GameContext.get)) -> MissionChecksJs:
    """What to confirm before taking off: no player pilot, missing pilots, flights
    starting before the mission start."""
    game = _require_game(game)
    return MissionChecksJs.for_game(game, GameContext.get_sim().current_time_in_sim)


@router.post(
    "/mission/fix-tots",
    operation_id="fix_tots",
    response_model=FixedTotsJs,
    responses=command_error_responses("No campaign is loaded."),
)
@locked
def fix_tots(game: Game | None = Depends(GameContext.get)) -> FixedTotsJs:
    """ "Fix TOTs automatically": moves each package with a flight starting before
    the mission start to its earliest feasible TOT."""
    game = _require_game(game)
    packages = fix_past_tots(game, GameContext.get_sim().current_time_in_sim)
    with EventStream.event_context() as events:
        for package in packages:
            events.update_flights_in_package(package)
    return FixedTotsJs(packages=[describe_package(p) for p in packages])


@router.post(
    "/mission",
    operation_id="generate_mission",
    response_model=MissionJs,
    responses=command_error_responses(
        "No campaign is loaded, it has not begun, or flights are missing pilots."
    ),
)
@locked
def take_off(game: Game | None = Depends(GameContext.get)) -> MissionJs:
    """ "Take off": fast forwards to first contact if the settings ask for it, writes
    the mission for DCS, then watches state.json for its result (WEB-05.1: see
    `GET /game/mission/result`).

    The client runs the confirmations of `GET /game/mission/checks` first.
    """
    game = _require_game(game)
    sim = GameContext.get_sim()
    path = generate_mission(game, sim)
    MissionResultContext.get().start(sim, path)
    return MissionJs(path=str(path))


@router.put(
    "/sim/speed",
    operation_id="set_sim_speed",
    response_model=SimJs,
    responses=command_error_responses(
        "No campaign is loaded, it has not begun, or the simulation is complete."
    ),
)
@locked
def sim_speed(
    change: SimSpeedChangeJs, game: Game | None = Depends(GameContext.get)
) -> SimJs:
    """Pauses the turn simulation or runs it at a speed (sim speed controls)."""
    game = _require_game(game)
    sim = GameContext.get_sim()
    set_sim_speed(game, sim, change.speed.to_setting())
    time = sim.current_time_in_sim_if_game_loaded
    return SimJs(
        speed=SimSpeedJs.from_setting(sim.simulation_speed),
        time=None if time is None else time.strftime("%H:%M:%S"),
    )

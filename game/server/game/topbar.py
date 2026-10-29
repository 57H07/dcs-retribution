"""Top bar and turn actions of the command view (WEB-01.1).

Read models of what `QTopPanel` showed (`QFactionsInfos`, `QConditionsWidget`,
`QBudgetBox`, `QIntelBox`, `MaxPlayerCount`, `SimSpeedControls`) and of the checks
it ran before a take off. The texts are built here so that the client applies no
game rule (spec §0 rule 1).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from dcs.weather import Weather as PydcsWeather
from pydantic import BaseModel

from game.commands import (
    flights_missing_pilots,
    max_player_count,
    packages_starting_in_the_past,
)
from game.commands.mission import describe_flight, describe_package
from game.income import Income
from game.sim.simspeedsetting import SimSpeedSetting
from game.theater.player import Player
from game.utils import meters, mps

if TYPE_CHECKING:
    from game import Game
    from game.weather.conditions import Conditions


class SimSpeedJs(str, Enum):
    """Mirror of `SimSpeedSetting` (whose values are tuples, unfit for OpenAPI)."""

    PAUSED = "paused"
    X1 = "1x"
    X2 = "2x"
    X5 = "5x"
    X10 = "10x"
    X100 = "100x"
    X1000 = "1000x"

    @staticmethod
    def from_setting(setting: SimSpeedSetting) -> SimSpeedJs:
        return SimSpeedJs[setting.name]

    def to_setting(self) -> SimSpeedSetting:
        return SimSpeedSetting[self.name]


class SimJs(BaseModel):
    """Speed and current time of the turn simulation."""

    speed: SimSpeedJs
    #: Current time in the simulation, "HH:MM:SS"; None when no simulation exists.
    time: str | None

    class Config:
        title = "Sim"


class SimSpeedChangeJs(BaseModel):
    speed: SimSpeedJs

    class Config:
        title = "SimSpeedChange"


class WindJs(BaseModel):
    altitude: str
    direction: int
    speed_kt: int

    class Config:
        title = "Wind"


class WeatherJs(BaseModel):
    #: "Clear", "Partly Cloudy"... or the name of the cloud preset.
    clouds: str
    precipitation: str
    fog: str
    #: Cloud base, None without clouds (the tooltip of QConditionsWidget).
    cloud_base_m: int | None
    cloud_base_ft: int | None
    winds: list[WindJs]

    class Config:
        title = "Weather"

    @staticmethod
    def from_conditions(conditions: Conditions) -> WeatherJs:
        weather = conditions.weather
        clouds = weather.clouds
        precipitation = "No rain"
        if clouds is not None and clouds.preset is not None:
            # "09 ##Two Layer Broken/Scattered \nMETAR:..." -> the name only.
            cloud_text = clouds.preset.description.splitlines()[0].split("##")[-1]
            if "Rain" in clouds.preset.name:
                precipitation = "Rain"
        else:
            density = 0 if clouds is None else clouds.density
            if not density:
                cloud_text = "Clear"
            elif density < 3:
                cloud_text = "Partly Cloudy"
            elif density < 5:
                cloud_text = "Mostly Cloudy"
            else:
                cloud_text = "Totally Cloudy"
            if clouds is not None:
                if clouds.precipitation == PydcsWeather.Preceptions.Rain:
                    precipitation = "Rain"
                elif clouds.precipitation == PydcsWeather.Preceptions.Thunderstorm:
                    precipitation = "Thunderstorm"
        if weather.fog is None:
            fog = "No fog"
        else:
            fog = f"Fog vis: {round(weather.fog.visibility.nautical_miles, 1)}nm"

        base_m = None if clouds is None else int(clouds.base)
        base_ft = None if base_m is None else int(meters(base_m).feet)
        winds = [
            WindJs(
                altitude=label,
                direction=int(wind.direction or 0),
                speed_kt=int(mps(wind.speed or 0).knots),
            )
            for label, wind in (
                ("GL", weather.wind.at_0m),
                ("FL08", weather.wind.at_2000m),
                ("FL26", weather.wind.at_8000m),
            )
        ]
        return WeatherJs(
            clouds=cloud_text.strip(),
            precipitation=precipitation,
            fog=fog,
            cloud_base_m=base_m,
            cloud_base_ft=base_ft,
            winds=winds,
        )


class ForceBalanceJs(BaseModel):
    """Friendly and enemy strength of one arm, as the Intel box rated it."""

    friendly: int
    enemy: int
    assessment: str

    class Config:
        title = "ForceBalance"


def forces_assessment(own: int, enemy: int) -> str:
    if not enemy:
        return "enemy eliminated"
    ratio = own / enemy
    if ratio < 0.6:
        return "outnumbered"
    if ratio < 0.8:
        return "slightly outnumbered"
    if ratio < 1.2:
        return "evenly matched"
    if ratio < 1.4:
        return "slight advantage"
    return "strong advantage"


def economy_assessment(own: float, enemy: float) -> str:
    if not enemy:
        return "enemy economy ruined"
    ratio = own / enemy
    if ratio < 0.6:
        return "strong disadvantage"
    if ratio < 0.8:
        return "slight disadvantage"
    if ratio < 1.2:
        return "evenly matched"
    if ratio < 1.4:
        return "slight advantage"
    return "strong advantage"


class TopBarJs(BaseModel):
    """Everything the top bar and the turn buttons of the command view show."""

    campaign_name: str | None
    theater: str
    player_faction: str
    enemy_faction: str
    turn: int
    #: Mission start, already formatted ("17 May 2022", "06:40").
    mission_start_date: str
    mission_start_time: str
    time_of_day: str
    weather: WeatherJs
    budget: float
    income: float
    air: ForceBalanceJs
    ground: ForceBalanceJs
    economy: str
    max_player_count: int
    sim: SimJs
    show_sim_speed_controls: bool

    class Config:
        title = "TopBar"

    @staticmethod
    def from_game(
        game: Game,
        sim_speed: SimSpeedSetting,
        sim_time: datetime | None,
        show_sim_speed_controls: bool,
    ) -> TopBarJs:
        start = game.conditions.start_time
        stats = game.game_stats.data_per_turn[-1]
        air = ForceBalanceJs(
            friendly=stats.allied_units.aircraft_count,
            enemy=stats.enemy_units.aircraft_count,
            assessment=forces_assessment(
                stats.allied_units.aircraft_count, stats.enemy_units.aircraft_count
            ),
        )
        ground = ForceBalanceJs(
            friendly=stats.allied_units.vehicles_count,
            enemy=stats.enemy_units.vehicles_count,
            assessment=forces_assessment(
                stats.allied_units.vehicles_count, stats.enemy_units.vehicles_count
            ),
        )
        if game.turn == 0:
            air.assessment = ground.assessment = "gathering intel"
        income = Income(game, player=Player.BLUE).total
        return TopBarJs(
            campaign_name=game.campaign_name,
            theater=game.theater.terrain.name,
            player_faction=game.blue.faction.name,
            enemy_faction=game.red.faction.name,
            turn=game.turn,
            mission_start_date=start.strftime("%d %b %Y"),
            mission_start_time=start.strftime("%H:%M"),
            time_of_day=game.conditions.time_of_day.value,
            weather=WeatherJs.from_conditions(game.conditions),
            budget=round(game.blue.budget, 2),
            income=round(income, 2),
            air=air,
            ground=ground,
            economy=economy_assessment(income, Income(game, player=Player.RED).total),
            max_player_count=max_player_count(game),
            sim=SimJs(
                speed=SimSpeedJs.from_setting(sim_speed),
                time=None if sim_time is None else sim_time.strftime("%H:%M:%S"),
            ),
            show_sim_speed_controls=show_sim_speed_controls,
        )


class MissionChecksJs(BaseModel):
    """What the player must confirm or fix before taking off."""

    has_player_pilots: bool
    #: Flights missing pilots, as "<task> <target>: <flight>": they block take off.
    flights_missing_pilots: list[str]
    #: Packages with a flight starting before the mission start, "<task> <target>".
    packages_starting_in_the_past: list[str]
    max_player_count: int

    class Config:
        title = "MissionChecks"

    @staticmethod
    def for_game(game: Game, now: datetime) -> MissionChecksJs:
        return MissionChecksJs(
            has_player_pilots=game.ato_has_clients(),
            flights_missing_pilots=[
                describe_flight(p, f) for p, f in flights_missing_pilots(game)
            ],
            packages_starting_in_the_past=[
                describe_package(p) for p in packages_starting_in_the_past(game, now)
            ],
            max_player_count=max_player_count(game),
        )


class FixedTotsJs(BaseModel):
    #: The packages whose TOT moved, "<task> <target>".
    packages: list[str]

    class Config:
        title = "FixedTots"


class MissionJs(BaseModel):
    """The mission written for DCS."""

    path: str

    class Config:
        title = "Mission"

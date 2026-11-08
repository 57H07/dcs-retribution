"""The weather of a mission in words: the top bar and the war diary (#193) read it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dcs.weather import Weather as PydcsWeather

if TYPE_CHECKING:
    from .conditions import Conditions


@dataclass(frozen=True)
class SkyDescription:
    #: "Clear", "Partly Cloudy"... or the name of the cloud preset.
    clouds: str
    #: "No rain", "Rain" or "Thunderstorm".
    precipitation: str
    #: "No fog" or "Fog vis: 1.2nm".
    fog: str

    def __str__(self) -> str:
        return f"{self.clouds}, {self.precipitation.lower()}, {self.fog.lower()}"


def describe_sky(conditions: Conditions) -> SkyDescription:
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
    return SkyDescription(cloud_text.strip(), precipitation, fog)

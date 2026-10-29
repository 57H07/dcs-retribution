// Fixtures of the command view tests (WEB-01.1).
import { MissionChecks, TopBar } from "../api/liberationApi";

export function topBar(overrides: Partial<TopBar> = {}): TopBar {
  return {
    campaign_name: "Slava Ukraini",
    theater: "Caucasus",
    player_faction: "Ukraine 2020",
    enemy_faction: "Russia 2020",
    turn: 4,
    mission_start_date: "17 May 2022",
    mission_start_time: "06:40",
    time_of_day: "dawn",
    weather: {
      clouds: "Scattered 2",
      precipitation: "No rain",
      fog: "No fog",
      cloud_base_m: 2400,
      cloud_base_ft: 7874,
      winds: [
        { altitude: "GL", direction: 270, speed_kt: 12 },
        { altitude: "FL08", direction: 280, speed_kt: 20 },
        { altitude: "FL26", direction: 290, speed_kt: 40 },
      ],
    },
    budget: 1240.4,
    income: 180,
    air: { friendly: 96, enemy: 132, assessment: "slightly outnumbered" },
    ground: { friendly: 64, enemy: 52, assessment: "slight advantage" },
    economy: "strong advantage",
    max_player_count: 2,
    sim: { speed: "paused", time: "06:40:00" },
    show_sim_speed_controls: false,
    ...overrides,
  };
}

export function missionChecks(
  overrides: Partial<MissionChecks> = {},
): MissionChecks {
  return {
    has_player_pilots: true,
    flights_missing_pilots: [],
    packages_starting_in_the_past: [],
    max_player_count: 2,
    ...overrides,
  };
}

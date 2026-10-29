// Display helpers of the command view (WEB-01.1). Formatting only: every value
// and every rating comes from the server.
import { TopBar, Weather } from "../api/liberationApi";

/** "$1 240M": millions, rounded, grouped by thousands. */
export function formatMoney(millions: number): string {
  const rounded = Math.round(millions);
  const grouped = Math.abs(rounded)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${rounded < 0 ? "-" : ""}$${grouped}M`;
}

/** "+180M/turn" (or "-20M/turn"). */
export function formatIncome(millions: number): string {
  const rounded = Math.round(millions);
  return `${rounded < 0 ? "-" : "+"}${Math.abs(rounded)}M/turn`;
}

export function formatTurn(turn: number): string {
  return turn.toString().padStart(2, "0");
}

/** "Clear · 270°/9 kt": the clouds and the ground wind. */
export function weatherSummary(weather: Weather): string {
  const ground = weather.winds[0];
  if (ground === undefined) {
    return weather.clouds;
  }
  const direction = ground.direction.toString().padStart(3, "0");
  return `${weather.clouds} · ${direction}°/${ground.speed_kt} kt`;
}

/** Lines of the weather tooltip, the cloud base first (QConditionsWidget). */
export function weatherDetails(weather: Weather): string[] {
  const lines = [
    weather.cloud_base_m != null
      ? `Cloud base: ${weather.cloud_base_m}m / ${weather.cloud_base_ft}ft`
      : "No cloud base",
    weather.precipitation,
    weather.fog,
  ];
  for (const wind of weather.winds) {
    const direction = wind.direction.toString().padStart(3, "0");
    lines.push(`Wind at ${wind.altitude}: ${direction}° ${wind.speed_kt} kt`);
  }
  return lines;
}

export function campaignTitle(bar: TopBar): string {
  return bar.campaign_name != null && bar.campaign_name !== ""
    ? bar.campaign_name
    : "Campaign";
}

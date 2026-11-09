// How far a campaign objective (#194) is, as one line: the Objectives screen and
// the top bar tooltip both show it.
import type { CampaignObjective } from "../api/liberationApi";

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

/** "2 / 5 destroyed · by turn 10 · 3 turns left" */
export function objectiveProgress(objective: CampaignObjective): string {
  const parts = [];
  if (objective.total != null) {
    parts.push(`${objective.done ?? 0} / ${objective.total} destroyed`);
  }
  if (objective.deadline != null) {
    const until = ["hold", "survive"].includes(objective.kind) ? "until" : "by";
    parts.push(`${until} turn ${objective.deadline}`);
  }
  if (objective.turns_left != null) {
    parts.push(`${plural(objective.turns_left, "turn")} left`);
  }
  return parts.join(" · ");
}

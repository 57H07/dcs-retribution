// Step 5: what will be generated.
import type { NewGameCampaign, NewGameOptions } from "../api/liberationApi";
import styles from "./NewGame.module.css";
import { FactionDraft, WizardState, startDate } from "./wizardState";

function changeCount(draft: FactionDraft): number {
  return [
    ...Object.values(draft.removed),
    ...Object.values(draft.added),
  ].reduce((total, units) => total + units.length, 0);
}

function factionText(draft: FactionDraft): string {
  const changes = changeCount(draft);
  return changes === 0
    ? draft.name
    : `${draft.name} (${changes} unit change${changes === 1 ? "" : "s"})`;
}

export function SummaryStep({
  campaign,
  options,
  state,
}: {
  campaign: NewGameCampaign;
  options: NewGameOptions;
  state: WizardState;
}) {
  const date = startDate(state, options);
  const rows: [string, string][] = [
    ["Campaign", campaign.name],
    ["Theater", campaign.theater],
    ["Player faction", factionText(state.blue)],
    ["Enemy faction", factionText(state.red)],
    ["Start date", date ?? "Choose a date in Campaign options"],
    ["Map", state.inverted ? "Inverted" : "As designed"],
    ["Budgets", `${state.playerBudget} : ${state.enemyBudget}`],
    [
      "Squadrons",
      state.squadronsStartFull ? "Start at full capacity" : "Start as planned",
    ],
    ["Settings changed", String(Object.keys(state.settings).length)],
    ["Mods", String(state.mods.length)],
  ];
  if (state.seed !== "") {
    rows.push(["Seed", state.seed]);
  }
  return (
    <div className={styles.form}>
      <h2 className={styles.heading}>Summary</h2>
      <dl className={styles.summary}>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className={styles.hint}>
        The air wing is configured once the campaign is generated, before its
        first turn. The campaign in play stays until then.
      </p>
    </div>
  );
}

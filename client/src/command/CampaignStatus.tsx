// Campaign state in the top bar (WEB-01.1): what QFactionsInfos,
// QConditionsWidget, QBudgetBox and QIntelBox showed in the Qt top panel.
import { TopBar, useGetTopBarQuery } from "../api/liberationApi";
import { Tooltip } from "../ui";
import styles from "./CampaignStatus.module.css";
import {
  campaignTitle,
  formatIncome,
  formatMoney,
  formatTurn,
  weatherDetails,
  weatherSummary,
} from "./format";

export interface CampaignStatusProps {
  /** Opens the finances (budget) and the intel (force balance) screens. */
  onOpenFinances: () => void;
  onOpenIntel: () => void;
}

export function useTopBar() {
  return useGetTopBarQuery();
}

function Stat({ label, children }: { label: string; children: string }) {
  return (
    <div className={styles.stat}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{children}</span>
    </div>
  );
}

function Loaded({
  bar,
  onOpenFinances,
  onOpenIntel,
}: CampaignStatusProps & { bar: TopBar }) {
  const weather = weatherDetails(bar.weather);
  return (
    <>
      <div className={styles.campaign}>
        <span className={styles.name}>{campaignTitle(bar)}</span>
        <span className={styles.sub}>
          {bar.theater} · {bar.player_faction} vs {bar.enemy_faction}
        </span>
      </div>
      <div className={styles.divider} aria-hidden="true" />
      <div className={styles.stats}>
        <Stat label="Turn">{formatTurn(bar.turn)}</Stat>
        <Stat label="Mission start">
          {`${bar.mission_start_date.toUpperCase()} · ${bar.mission_start_time}`}
        </Stat>
        <Tooltip
          content={
            <span className={styles.lines}>
              {weather.map((line) => (
                <span key={line}>{line}</span>
              ))}
            </span>
          }
          side="bottom"
        >
          <div
            className={styles.stat}
            tabIndex={0}
            aria-label={`Weather: ${weatherSummary(bar.weather)}. ${weather.join(". ")}`}
          >
            <span className={styles.label}>Weather</span>
            <span className={styles.text}>{weatherSummary(bar.weather)}</span>
          </div>
        </Tooltip>
      </div>
      <div className={styles.spacer} />
      <div className={styles.boxes}>
        <button
          type="button"
          className={styles.box}
          onClick={onOpenFinances}
          aria-label={`Budget ${formatMoney(bar.budget)}, ${formatIncome(bar.income)}: open finances`}
        >
          <svg
            className={styles.icon}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v10M9 9.5h4.5a2 2 0 010 4H10a2 2 0 000 4h5" />
          </svg>
          <span className={styles.money}>{formatMoney(bar.budget)}</span>
          <span className={styles.income}>{formatIncome(bar.income)}</span>
        </button>
        <Tooltip
          content={
            <span className={styles.lines}>
              <span>Air superiority: {bar.air.assessment}</span>
              <span>Front line: {bar.ground.assessment}</span>
              <span>Economic strength: {bar.economy}</span>
            </span>
          }
          side="bottom"
        >
          <button
            type="button"
            className={styles.box}
            onClick={onOpenIntel}
            aria-label={
              `Air ${bar.air.friendly} friendly / ${bar.air.enemy} enemy, ` +
              `armor ${bar.ground.friendly} / ${bar.ground.enemy}: open intel`
            }
          >
            <span className={styles.label}>Air</span>
            <span className={styles.friendly}>{bar.air.friendly}</span>
            <span className={styles.slash}>/</span>
            <span className={styles.enemy}>{bar.air.enemy}</span>
            <span className={styles.label}>Armor</span>
            <span className={styles.friendly}>{bar.ground.friendly}</span>
            <span className={styles.slash}>/</span>
            <span className={styles.enemy}>{bar.ground.enemy}</span>
          </button>
        </Tooltip>
      </div>
    </>
  );
}

/** Campaign, turn, time, weather, budget and force balance; live updated. */
export function CampaignStatus(props: CampaignStatusProps) {
  const { data, isLoading, isError } = useTopBar();
  if (isLoading) {
    return <span className={styles.placeholder}>Loading campaign…</span>;
  }
  if (isError) {
    return (
      <span className={styles.placeholder} role="alert">
        Campaign state unavailable
      </span>
    );
  }
  if (data == null) {
    return <span className={styles.placeholder}>No campaign loaded</span>;
  }
  return <Loaded bar={data} {...props} />;
}

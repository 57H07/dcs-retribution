// Pieces shared by the report tabs: query states, coalition switch, stat card.
import { commandErrorMessage } from "../api/commands";
import { Switch } from "../ui";
import styles from "./Reports.module.css";
import { ReactNode } from "react";

/** "812.5M": the one-decimal figures of the Qt finances window. */
export function formatMillions(value: number): string {
  return `${value.toFixed(1)}M`;
}

interface QueryState<T> {
  data?: T | null;
  error?: unknown;
  isLoading: boolean;
}

/** Loading, error and no-campaign states around a report. */
export function ReportBody<T>({
  query,
  name,
  children,
}: {
  query: QueryState<T>;
  name: string;
  children: (data: T) => ReactNode;
}) {
  if (query.isLoading) {
    return <p className={styles.state}>Loading {name}…</p>;
  }
  if (query.error) {
    return (
      <p className={styles.state} role="alert">
        {commandErrorMessage(query.error) ?? `The ${name} is not available.`}
      </p>
    );
  }
  if (query.data == null) {
    return <p className={styles.state}>No campaign loaded.</p>;
  }
  return <>{children(query.data)}</>;
}

/** The "Enemy info" check box of the Qt intel window. */
export function EnemySwitch({
  enemy,
  onChange,
}: {
  enemy: boolean;
  onChange: (enemy: boolean) => void;
}) {
  return (
    <div className={styles.toolbar}>
      <Switch label="Enemy info" checked={enemy} onCheckedChange={onChange} />
    </div>
  );
}

export function StatCard({
  title,
  value,
  detail,
  tone = "neutral",
}: {
  title: string;
  value: ReactNode;
  detail?: string;
  tone?: "neutral" | "friendly" | "enemy";
}) {
  return (
    <div className={styles.card}>
      <span className={styles.cardTitle}>{title}</span>
      <span className={styles.cardValue} data-tone={tone}>
        {value}
      </span>
      {detail && <span className={styles.cardDetail}>{detail}</span>}
    </div>
  );
}

// Frame of the secondary screens (WEB-08.2): the settings screen header (back
// to the command view, title, actions) above a scrolling body.
import { commandErrorMessage } from "../api/commands";
import { PATHS } from "../shell/paths";
import frame from "../settings/SettingsScreen.module.css";
import styles from "./Secondary.module.css";
import { ReactNode } from "react";
import { Link } from "react-router-dom";

export interface ScreenFrameProps {
  title: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function ScreenFrame({ title, actions, children }: ScreenFrameProps) {
  return (
    <div className={frame.screen}>
      <header className={frame.header}>
        <Link to={PATHS.command} className={frame.back}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M15 6l-6 6 6 6" />
          </svg>
          Command view
        </Link>
        <span className={frame.divider} />
        <h1 className={frame.title}>{title}</h1>
        {actions && <div className={styles.actions}>{actions}</div>}
      </header>
      <div className={styles.body}>{children}</div>
    </div>
  );
}

interface QueryState<T> {
  data?: T | null;
  error?: unknown;
  isLoading: boolean;
}

/** Loading, error and no-campaign states around a screen's data. */
export function QueryBody<T>({
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
        {commandErrorMessage(
          query.error as Parameters<typeof commandErrorMessage>[0],
        ) ?? `The ${name} are not available.`}
      </p>
    );
  }
  if (query.data == null) {
    return <p className={styles.state}>No campaign loaded.</p>;
  }
  return <>{children(query.data)}</>;
}

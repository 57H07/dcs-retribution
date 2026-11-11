// Frame of the secondary screens (WEB-08.2): the settings screen header (back
// to the command view, or to the screen that opened it, title, actions) above a
// scrolling body.
import { commandErrorMessage } from "../api/commands";
import { PATHS } from "../shell/paths";
import frame from "../settings/SettingsScreen.module.css";
import styles from "./Secondary.module.css";
import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

/** Where the back link of a secondary screen leads. */
export interface BackTo {
  to: string;
  label: string;
}

/**
 * The navigation state of a link that opens a secondary screen from another
 * screen than the command view: its back link then returns there. The after-
 * action report opens a pilot career this way, so that coming back leaves its
 * results to accept (#220).
 */
export function backTo(to: string, label: string): { backTo: BackTo } {
  return { backTo: { to, label } };
}

const COMMAND_VIEW: BackTo = { to: PATHS.command, label: "Command view" };

function useBackTo(): BackTo {
  const state = useLocation().state as { backTo?: BackTo } | null;
  return state?.backTo ?? COMMAND_VIEW;
}

export interface ScreenFrameProps {
  title: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function ScreenFrame({ title, actions, children }: ScreenFrameProps) {
  const back = useBackTo();
  return (
    <div className={frame.screen}>
      <header className={frame.header}>
        <Link to={back.to} className={frame.back}>
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
          {back.label}
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

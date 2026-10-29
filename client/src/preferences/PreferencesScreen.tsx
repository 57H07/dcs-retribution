// Preferences screen (WEB-07.2): DCS folders and install options, read from and
// saved to the preferences file by GET/PUT /preferences/. No campaign needed.
import { commandErrorMessage } from "../api/commands";
import {
  InstallPreferencesState,
  useGetInstallPreferencesQuery,
} from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import { PATHS } from "../shell/paths";
import { PreferencesForm } from "./PreferencesForm";
import { ReactNode } from "react";
import { Link } from "react-router-dom";

/** Loading and error states around the form. */
export function PreferencesBody({
  children,
}: {
  children: (state: InstallPreferencesState) => ReactNode;
}) {
  const { data, error, isLoading } = useGetInstallPreferencesQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  if (isLoading) {
    return <p className={settings.state}>Loading preferences…</p>;
  }
  if (error || !data) {
    return (
      <p className={settings.state} role="alert">
        {commandErrorMessage(error) ?? "Preferences are not available."}
      </p>
    );
  }
  return <>{children(data)}</>;
}

export function PreferencesScreen() {
  return (
    <div className={settings.screen}>
      <header className={settings.header}>
        <Link to={PATHS.command} className={settings.back}>
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
        <span className={settings.divider} />
        <h1 className={settings.title}>Preferences</h1>
      </header>
      <div className={settings.main}>
        <PreferencesBody>
          {(state) => <PreferencesForm state={state} submitLabel="Apply" />}
        </PreferencesBody>
      </div>
    </div>
  );
}

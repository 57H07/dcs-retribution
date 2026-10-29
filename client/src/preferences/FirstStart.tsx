// First start (WEB-07.2), formerly QLiberationFirstStartWindow: shown over the
// whole shell while the server says the preferences are missing or invalid, until
// the player accepts valid ones (which also replaces MissionScripting.lua).
import { useGetInstallPreferencesQuery } from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import styles from "./Preferences.module.css";
import { PreferencesForm } from "./PreferencesForm";

const MISSION_SCRIPTING =
  "<DCS installation folder>/Scripts/MissionScripting.lua";

function Warning() {
  return (
    <section className={styles.warning} aria-label="Please read this">
      <h2 className={settings.sectionTitle}>
        Please take 30 seconds to read this
      </h2>
      <p>
        DCS Retribution will modify this file in your DCS installation folder:{" "}
        <code>{MISSION_SCRIPTING}</code>
      </p>
      <p>
        This disables some security limits of the DCS World Lua scripting
        environment, so that DCS World and DCS Retribution can communicate. It
        could also let malicious DCS mission files access your filesystem: do
        not join untrusted servers or open untrusted mission files while DCS
        Retribution is running.
      </p>
      <p>
        DCS Retribution restores the original file when it closes. If it ever
        crashes before, copy the backup{" "}
        <code>./resources/scripts/MissionScripting.original.lua</code> back to{" "}
        <code>{MISSION_SCRIPTING}</code>.
      </p>
      <p>
        If you leave the DCS installation folder empty, DCS Retribution cannot
        replace the file and will not work properly: replace it yourself with{" "}
        <code>resources/scripts/MissionScripting.lua</code> (see the Dedicated
        Server Guide in the Retribution wiki).
      </p>
      <p>The file is replaced when you accept below.</p>
    </section>
  );
}

/** The first start screen, or nothing when the preferences are fine. */
export function FirstStart() {
  const { data } = useGetInstallPreferencesQuery();
  if (!data?.first_start) {
    return null;
  }
  return (
    <div
      className={`${settings.screen} ${styles.firstStart}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="first-start-title"
    >
      <header className={settings.header}>
        <h1 id="first-start-title" className={settings.title}>
          Welcome to DCS Retribution
        </h1>
      </header>
      <div className={settings.main}>
        <PreferencesForm
          state={data}
          submitLabel="I have read everything and I accept"
        >
          <Warning />
        </PreferencesForm>
      </div>
    </div>
  );
}

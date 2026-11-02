// The modules the player owns (File → Preferences): saved at each tick, for every
// campaign. The engine cannot know them, so the player declares them.
import { commandErrorMessage } from "../api/commands";
import {
  useGetPlayerModulesQuery,
  useSetPlayerModulesMutation,
} from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import { compareNames } from "./AircraftOptions";
import { useToast } from "../ui";
import styles from "./Preferences.module.css";
import { useEffect, useId, useState } from "react";

export function ModulesSection() {
  const { data: modules } = useGetPlayerModulesQuery();
  const [save] = useSetPlayerModulesMutation();
  const toast = useToast();
  const headingId = useId();
  const [filter, setFilter] = useState("");
  // What was just ticked, until the server's answer comes back.
  const [ticked, setTicked] = useState<Set<string> | null>(null);
  useEffect(() => setTicked(null), [modules]);
  const owned =
    ticked ?? new Set(modules?.filter((m) => m.owned).map((m) => m.id));

  const toggle = async (id: string, checked: boolean) => {
    const next = new Set(owned);
    if (checked) {
      next.add(id);
    } else {
      next.delete(id);
    }
    setTicked(next);
    const result = await save({ ownedModulesJs: { owned: [...next] } });
    if ("error" in result) {
      setTicked(null);
      toast({
        title: "Modules not saved",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    }
  };

  const needle = filter.trim().toLowerCase();
  const shown = (modules ?? [])
    .filter((m) => m.name.toLowerCase().includes(needle))
    .sort((a, b) => compareNames(a.name, b.name));
  return (
    <section className={settings.section} aria-labelledby={headingId}>
      <h2 id={headingId} className={settings.sectionTitle}>
        Modules you own
      </h2>
      {modules?.length === 0 ? (
        <p className={styles.note}>
          Choose your DCS Saved Games folder and apply it to list the modules.
        </p>
      ) : (
        <div className={styles.modules}>
          <p className={styles.note}>
            These aircraft come first, marked ★, in the Add new squadron and Add
            flight lists. Saved at once, for every campaign.
          </p>
          <input
            className={styles.path}
            aria-label="Filter modules"
            placeholder={`Filter ${modules?.length ?? 0} aircraft…`}
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          />
          <div className={styles.moduleGrid}>
            {shown.map((module) => (
              <label key={module.id} className={styles.module}>
                <input
                  type="checkbox"
                  checked={owned.has(module.id)}
                  onChange={(event) => toggle(module.id, event.target.checked)}
                />
                {module.name}
              </label>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

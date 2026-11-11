// Steps 3 and 4: date, map and campaign settings, with the controls of the settings
// screen; then what only the generator reads: navies, budgets, mods, seed.
import type {
  CampaignDefaults,
  NewGameOptions,
  Setting,
} from "../api/liberationApi";
import { SettingControl } from "../settings/SettingControl";
import {
  groupMatches,
  isModified,
  modifiedCount,
  searchSettings,
} from "../settings/search";
import { NumberField, Switch } from "../ui";
import styles from "./NewGame.module.css";
import { GENERATOR_FLAGS, SettingValue, WizardState } from "./wizardState";
import { useState } from "react";

export interface StepProps {
  options: NewGameOptions;
  state: WizardState;
  onChange: (state: WizardState) => void;
}

function Row({
  label,
  help,
  modified,
  children,
}: {
  label: string;
  help?: string | null;
  /** Shows the Modified marker of the Settings screen. */
  modified?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={styles.row}>
      <div className={styles.rowText}>
        <span>{label}</span>
        {help != null && <span className={styles.hint}>{help}</span>}
      </div>
      {modified && (
        <span className={styles.modified} title="Differs from the default">
          Modified
        </span>
      )}
      {children}
    </div>
  );
}

function ToggleRow({
  label,
  help,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  help?: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <Row label={label} help={help}>
      <Switch
        aria-label={label}
        checked={checked}
        disabled={disabled}
        onCheckedChange={onChange}
      />
    </Row>
  );
}

function SettingRow({
  setting,
  value,
  onChange,
}: {
  setting: Setting;
  value: SettingValue;
  onChange: (value: SettingValue) => void;
}) {
  return (
    <Row
      label={setting.label}
      help={setting.detail ?? setting.tooltip}
      modified={isModified(setting, { [setting.key]: value })}
    >
      <SettingControl setting={setting} value={value} onChange={onChange} />
    </Row>
  );
}

export function OptionsStep({
  options,
  defaults,
  state,
  onChange,
}: StepProps & { defaults: CampaignDefaults }) {
  const [pageId, setPageId] = useState<string>();
  const [query, setQuery] = useState("");
  const pages = defaults.settings_pages;
  const page = pages.find((p) => p.id === pageId) ?? pages[0];
  const searching = query.trim() !== "";
  const settingRow = (setting: Setting) => (
    <SettingRow
      key={setting.key}
      setting={setting}
      value={state.settings[setting.key] ?? setting.value}
      onChange={(value) =>
        onChange({
          ...state,
          settings: { ...state.settings, [setting.key]: value },
        })
      }
    />
  );
  let shown: { title: string; settings: Setting[] }[];
  if (searching) {
    shown = groupMatches(searchSettings(pages, query.trim()));
  } else {
    shown = (page?.sections ?? []).map((section) => ({
      title: section.name,
      settings: section.settings,
    }));
  }
  const invert = (inverted: boolean) =>
    // Qt too: the sides trade places, so the factions follow them.
    onChange({ ...state, inverted, blue: state.red, red: state.blue });
  return (
    <div className={`${styles.form} ${styles.fillForm}`}>
      <section className={styles.group} aria-label="Date and map">
        <h2 className={styles.heading}>Date and map</h2>
        <Row label="Start date">
          <div className={styles.dateFields}>
            <label className={styles.check}>
              <input
                type="checkbox"
                checked={state.timePeriod !== null}
                onChange={(event) =>
                  onChange({
                    ...state,
                    timePeriod: event.target.checked
                      ? options.default_time_period
                      : null,
                  })
                }
              />
              Use preset
            </label>
            {state.timePeriod !== null ? (
              <select
                className={styles.select}
                aria-label="Time period"
                value={state.timePeriod}
                onChange={(event) =>
                  onChange({ ...state, timePeriod: event.target.value })
                }
              >
                {options.time_periods.map((period) => (
                  <option key={period.name} value={period.name}>
                    {period.name}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className={styles.input}
                type="date"
                aria-label="Custom start date"
                value={state.customDate}
                onChange={(event) =>
                  onChange({ ...state, customDate: event.target.value })
                }
              />
            )}
          </div>
        </Row>
        <ToggleRow
          label="Invert map"
          help="The sides trade their bases, and the factions follow."
          checked={state.inverted}
          onChange={invert}
        />
        <ToggleRow
          label="Advanced IADS (WIP)"
          help={
            defaults.advanced_iads_available
              ? undefined
              : "Advanced IADS is not supported by this campaign."
          }
          checked={state.advancedIads}
          disabled={!defaults.advanced_iads_available}
          onChange={(advancedIads) => onChange({ ...state, advancedIads })}
        />
      </section>
      <section
        className={`${styles.group} ${styles.fillGroup}`}
        aria-label="Campaign settings"
      >
        <h2 className={styles.heading}>Campaign settings</h2>
        <input
          className={styles.settingsSearch}
          type="search"
          placeholder="Search all settings"
          aria-label="Search all settings"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <div className={styles.settingsColumns}>
          <nav className={styles.pages} aria-label="Settings pages">
            {pages.map((p) => {
              const changed = modifiedCount(p, state.settings);
              return (
                <button
                  key={p.id}
                  type="button"
                  className={styles.pageButton}
                  aria-current={
                    !searching && p.id === page?.id ? "page" : undefined
                  }
                  onClick={() => {
                    setPageId(p.id);
                    setQuery("");
                  }}
                >
                  <span>{p.name}</span>
                  {changed > 0 && (
                    <span
                      className={styles.pageCount}
                      aria-label={`${changed} modified`}
                    >
                      {changed}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
          {/* #213: its own scroll, so the pages and the search stay in view; a
              new page or search remounts it, back at the top. */}
          <div
            key={searching ? `search:${query.trim()}` : page?.id}
            className={styles.settings}
            role="region"
            aria-label="Settings list"
            tabIndex={0}
          >
            {searching && shown.length === 0 && (
              <p className={styles.hint}>
                No setting matches “{query.trim()}”.
              </p>
            )}
            {shown.map((group) => (
              <section key={group.title} aria-label={group.title}>
                <h3 className={styles.label}>{group.title}</h3>
                {group.settings.map(settingRow)}
              </section>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

export function GeneratorStep({ options, state, onChange }: StepProps) {
  return (
    <div className={styles.form}>
      <section className={styles.group} aria-label="Generator settings">
        <h2 className={styles.heading}>Generator settings</h2>
        {GENERATOR_FLAGS.map(([key, label]) => (
          <ToggleRow
            key={key}
            label={label}
            checked={state.flags[key]}
            onChange={(checked) =>
              onChange({
                ...state,
                flags: { ...state.flags, [key]: checked },
              })
            }
          />
        ))}
        <ToggleRow
          label="Squadrons start at full capacity"
          help="All squadrons start at full strength, given enough room at their base."
          checked={state.squadronsStartFull}
          onChange={(squadronsStartFull) =>
            onChange({ ...state, squadronsStartFull })
          }
        />
        <Row label="Player starting budget">
          <NumberField
            label="Player starting budget"
            hideLabel
            value={state.playerBudget}
            min={0}
            step={10}
            onValueChange={(playerBudget) =>
              onChange({ ...state, playerBudget })
            }
          />
        </Row>
        <Row label="Enemy starting budget">
          <NumberField
            label="Enemy starting budget"
            hideLabel
            value={state.enemyBudget}
            min={0}
            step={10}
            onValueChange={(enemyBudget) => onChange({ ...state, enemyBudget })}
          />
        </Row>
        <Row
          label="Seed"
          help="Same parameters and seed, same campaign. Empty: a new campaign each time."
        >
          <input
            className={styles.input}
            inputMode="numeric"
            aria-label="Seed"
            value={state.seed}
            onChange={(event) =>
              onChange({
                ...state,
                seed: event.target.value.replace(/[^0-9]/g, ""),
              })
            }
          />
        </Row>
      </section>
      <section className={styles.group} aria-label="Mods">
        <h2 className={styles.heading}>Mod settings</h2>
        <p className={styles.hint}>
          Select the mods you have installed. If your chosen factions support
          them, you'll be able to use these mods in your campaign.
        </p>
        <div className={styles.mods}>
          {options.mods.map((mod) => (
            <label key={mod.key} className={styles.check}>
              <input
                type="checkbox"
                checked={state.mods.includes(mod.key)}
                onChange={(event) =>
                  onChange({
                    ...state,
                    mods: event.target.checked
                      ? [...state.mods, mod.key]
                      : state.mods.filter((key) => key !== mod.key),
                  })
                }
              />
              {mod.label}
            </label>
          ))}
        </div>
      </section>
    </div>
  );
}

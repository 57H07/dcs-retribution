// The units of a faction by group (Qt: QFactionUnits), for the wizard, where units
// can also leave, and for the air wing configuration, where they can only join.
import type { FactionSheet } from "../api/liberationApi";
import { Button, Switch } from "../ui";
import styles from "./AirWingConfig.module.css";
import { useState } from "react";

export interface FactionUnitsProps {
  sheet: FactionSheet;
  hasJtac: boolean;
  doctrine: string;
  /** Units the player added and the server does not list yet (wizard). */
  added?: Record<string, string[]>;
  /** Units the player took out, per group (wizard). */
  removed?: Record<string, string[]>;
  /** Absent: the units of the faction cannot be taken out. */
  onToggleUnit?: (group: string, unit: string) => void;
  onAddUnit: (group: string, unit: string) => void;
  onJtacChange: (hasJtac: boolean) => void;
  onDoctrineChange: (doctrine: string) => void;
}

function AddUnit({
  label,
  units,
  onAdd,
}: {
  label: string;
  units: string[];
  onAdd: (unit: string) => void;
}) {
  const [picked, setPicked] = useState<string>();
  const unit =
    picked !== undefined && units.includes(picked) ? picked : units[0];
  return (
    <div className={styles.addUnit}>
      <select
        className={styles.select}
        aria-label={`Unit to add to ${label}`}
        value={unit ?? ""}
        disabled={units.length === 0}
        onChange={(event) => setPicked(event.target.value)}
      >
        {units.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
      <Button
        disabled={unit === undefined}
        aria-label={`Add to ${label}`}
        onClick={() => unit !== undefined && onAdd(unit)}
      >
        Add
      </Button>
    </div>
  );
}

export function FactionUnits({
  sheet,
  hasJtac,
  doctrine,
  added = {},
  removed = {},
  onToggleUnit,
  onAddUnit,
  onJtacChange,
  onDoctrineChange,
}: FactionUnitsProps) {
  return (
    <div className={styles.faction}>
      <div className={styles.fields}>
        <label className={styles.field}>
          <span className={styles.label}>Doctrine</span>
          <select
            className={styles.select}
            value={doctrine}
            onChange={(event) => onDoctrineChange(event.target.value)}
          >
            {sheet.doctrines.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <div className={styles.field}>
          <span className={styles.label}>Has JTAC</span>
          <Switch
            aria-label="Has JTAC"
            checked={hasJtac}
            onCheckedChange={onJtacChange}
          />
        </div>
      </div>
      {sheet.groups.map((group) => {
        const extra = added[group.key] ?? [];
        const units = [...group.units, ...extra].sort();
        const gone = removed[group.key] ?? [];
        return (
          <section
            key={group.key}
            className={styles.unitGroup}
            aria-label={group.label}
          >
            <h3 className={styles.label}>{group.label}</h3>
            {units.length === 0 && <p className={styles.hint}>None.</p>}
            <ul className={styles.units}>
              {units.map((unit) => (
                <li key={unit}>
                  {onToggleUnit ? (
                    <label className={styles.check}>
                      <input
                        type="checkbox"
                        checked={!gone.includes(unit)}
                        onChange={() => onToggleUnit(group.key, unit)}
                      />
                      {unit}
                    </label>
                  ) : (
                    unit
                  )}
                </li>
              ))}
            </ul>
            <AddUnit
              label={group.label}
              units={group.addable.filter((unit) => !extra.includes(unit))}
              onAdd={(unit) => onAddUnit(group.key, unit)}
            />
          </section>
        );
      })}
    </div>
  );
}

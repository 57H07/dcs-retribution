// One control per setting kind (WEB-07.1). The kind, bounds, step and choices
// come from the server schema: a new setting needs no code here.
import type { Setting } from "../api/liberationApi";
import { NumberField, Slider, Switch } from "../ui";
import styles from "./SettingsScreen.module.css";
import { useEffect, useState } from "react";

export type SettingValue = Setting["value"];

export interface SettingControlProps {
  setting: Setting;
  /** Value shown while its command runs (optimistic), else the server value. */
  value: SettingValue;
  onChange: (value: SettingValue) => void;
}

// A slider only when it has a reasonable number of positions.
const MAX_SLIDER_POSITIONS = 1000;

function formatNumber(value: number, step: number): string {
  const decimals = (String(step).split(".")[1] ?? "").length;
  return value.toFixed(decimals);
}

function FloatSlider({ setting, value, onChange }: SettingControlProps) {
  const step = setting.step ?? 0.01;
  const [dragged, setDragged] = useState<number | null>(null);
  // A new server value ends the drag preview.
  useEffect(() => setDragged(null), [value]);
  return (
    <Slider
      className={styles.slider}
      label={setting.label}
      value={dragged ?? Number(value)}
      min={setting.min}
      max={setting.max}
      step={step}
      format={(v) => formatNumber(v, step)}
      onValueChange={setDragged}
      onValueCommit={(next) => onChange(next)}
    />
  );
}

export function SettingControl(props: SettingControlProps) {
  const { setting, value, onChange } = props;
  switch (setting.kind) {
    case "bool":
      return (
        <Switch
          aria-label={setting.label}
          checked={value === true}
          onCheckedChange={(checked) => onChange(checked)}
        />
      );
    case "choice":
      return (
        <select
          className={styles.select}
          aria-label={setting.label}
          value={String(value)}
          onChange={(event) => onChange(event.target.value)}
        >
          {(setting.choices ?? []).map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>
      );
    case "float": {
      const step = setting.step ?? 0.01;
      const positions =
        setting.min != null && setting.max != null
          ? (setting.max - setting.min) / step
          : Infinity;
      if (positions <= MAX_SLIDER_POSITIONS) {
        return <FloatSlider {...props} />;
      }
      return (
        <NumberField
          label={setting.label}
          hideLabel
          value={Number(value)}
          min={setting.min ?? undefined}
          max={setting.max ?? undefined}
          step={step}
          onValueChange={onChange}
        />
      );
    }
    case "int":
    case "minutes":
      return (
        <NumberField
          label={setting.label}
          hideLabel
          value={Number(value)}
          min={setting.min ?? undefined}
          max={setting.max ?? undefined}
          step={setting.step ?? 1}
          unit={setting.kind === "minutes" ? "min" : undefined}
          onValueChange={onChange}
        />
      );
  }
}

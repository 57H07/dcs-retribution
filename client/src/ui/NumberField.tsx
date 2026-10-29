import { IconButton } from "./Button";
import styles from "./NumberField.module.css";
import { cx } from "./cx";
import { KeyboardEvent, useId, useState } from "react";

// Radix has no number field primitive: this follows the WAI-ARIA spinbutton
// pattern (arrows, Page Up/Down, Home/End) on a text input, so typing is free
// and the value is clamped and committed on Enter or blur.

export interface NumberFieldProps {
  label: string;
  /** Keeps the label for assistive technology only. */
  hideLabel?: boolean;
  value: number;
  onValueChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  /** Shown after the input, e.g. "kt" or "$M". */
  unit?: string;
  disabled?: boolean;
  /** Hides the − / + buttons (compact tables). */
  hideSteppers?: boolean;
  className?: string;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function NumberField({
  label,
  hideLabel,
  value,
  onValueChange,
  min = -Infinity,
  max = Infinity,
  step = 1,
  unit,
  disabled,
  hideSteppers,
  className,
}: NumberFieldProps) {
  const id = useId();
  // Text being typed; null shows the committed value.
  const [draft, setDraft] = useState<string | null>(null);
  const parsed = draft === null ? value : Number(draft.replace(",", "."));
  const invalid =
    draft !== null && (draft.trim() === "" || Number.isNaN(parsed));

  const decimals = (String(step).split(".")[1] ?? "").length;

  const set = (next: number) => {
    setDraft(null);
    // Rounded to the step precision: 0.1 + 0.2 gives 0.3.
    const clamped = clamp(Number(next.toFixed(decimals)), min, max);
    if (clamped !== value) {
      onValueChange(clamped);
    }
  };

  const commit = () => {
    if (draft === null) {
      return;
    }
    if (invalid) {
      setDraft(null);
      return;
    }
    set(parsed);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    const base = invalid ? value : parsed;
    const moves: Record<string, number | undefined> = {
      ArrowUp: base + step,
      ArrowDown: base - step,
      PageUp: base + step * 10,
      PageDown: base - step * 10,
      Home: Number.isFinite(min) ? min : undefined,
      End: Number.isFinite(max) ? max : undefined,
    };
    if (event.key === "Enter") {
      commit();
      return;
    }
    const next = moves[event.key];
    if (next !== undefined) {
      event.preventDefault();
      set(next);
    }
  };

  return (
    <div className={cx(styles.field, className)}>
      <label
        htmlFor={id}
        className={hideLabel ? "ui-visually-hidden" : styles.label}
      >
        {label}
      </label>
      <div className={styles.row}>
        {!hideSteppers && (
          <IconButton
            aria-label={`Decrease ${label}`}
            className={styles.step}
            variant="secondary"
            disabled={disabled || value <= min}
            onClick={() => set(value - step)}
            tabIndex={-1}
          >
            −
          </IconButton>
        )}
        <input
          id={id}
          className={styles.input}
          role="spinbutton"
          inputMode="decimal"
          autoComplete="off"
          aria-valuenow={value}
          aria-valuemin={Number.isFinite(min) ? min : undefined}
          aria-valuemax={Number.isFinite(max) ? max : undefined}
          aria-invalid={invalid || undefined}
          disabled={disabled}
          value={draft ?? String(value)}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={commit}
          onKeyDown={onKeyDown}
        />
        {!hideSteppers && (
          <IconButton
            aria-label={`Increase ${label}`}
            className={styles.step}
            variant="secondary"
            disabled={disabled || value >= max}
            onClick={() => set(value + step)}
            tabIndex={-1}
          >
            +
          </IconButton>
        )}
        {unit && <span className={styles.unit}>{unit}</span>}
      </div>
    </div>
  );
}

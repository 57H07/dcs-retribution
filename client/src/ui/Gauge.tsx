import styles from "./Gauge.module.css";
import { cx } from "./cx";
import { vars } from "./tokens";
import * as Progress from "@radix-ui/react-progress";
import { useId } from "react";

export type GaugeTone = "friendly" | "hostile" | "success" | "accent";

export interface GaugeProps {
  label: string;
  /** Keeps the label for assistive technology only. */
  hideLabel?: boolean;
  value: number;
  max?: number;
  tone?: GaugeTone;
  /** Text after the bar; defaults to "value/max". Pass null to hide it. */
  valueText?: string | null;
  className?: string;
}

const TONE_COLORS: Record<GaugeTone, string> = {
  friendly: vars.color.friendly,
  hostile: vars.color.hostile,
  success: vars.color.success,
  accent: vars.color.accent,
};

export function Gauge({
  label,
  hideLabel,
  value,
  max = 100,
  tone = "friendly",
  valueText,
  className,
}: GaugeProps) {
  const labelId = useId();
  const clamped = Math.min(max, Math.max(0, value));
  const text = valueText === undefined ? `${clamped}/${max}` : valueText;
  return (
    <div
      className={cx(styles.gauge, hideLabel && styles.noLabel, className)}
      data-tone={tone}
    >
      <span
        id={labelId}
        className={hideLabel ? "ui-visually-hidden" : styles.label}
      >
        {label}
      </span>
      <Progress.Root
        className={styles.track}
        value={clamped}
        max={max}
        aria-labelledby={labelId}
        getValueLabel={(current, total) => text ?? `${current}/${total}`}
      >
        <Progress.Indicator
          className={styles.indicator}
          style={{
            width: `${max > 0 ? (clamped / max) * 100 : 0}%`,
            background: TONE_COLORS[tone],
          }}
        />
      </Progress.Root>
      {text !== null && (
        <span className={styles.value} aria-hidden="true">
          {text}
        </span>
      )}
    </div>
  );
}

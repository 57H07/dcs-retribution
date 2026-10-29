import styles from "./Slider.module.css";
import { cx } from "./cx";
import * as RadixSlider from "@radix-ui/react-slider";
import { useId } from "react";

export interface SliderProps {
  label: string;
  value: number;
  onValueChange: (value: number) => void;
  /** Called once the user releases the thumb (expensive commands). */
  onValueCommit?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  /** Formats the value shown beside the label and read by screen readers. */
  format?: (value: number) => string;
  className?: string;
}

export function Slider({
  label,
  value,
  onValueChange,
  onValueCommit,
  min = 0,
  max = 100,
  step = 1,
  disabled,
  format = String,
  className,
}: SliderProps) {
  const labelId = useId();
  return (
    <div className={cx(styles.field, className)}>
      <div className={styles.header}>
        <span id={labelId} className={styles.label}>
          {label}
        </span>
        <span className={styles.value} aria-hidden="true">
          {format(value)}
        </span>
      </div>
      <RadixSlider.Root
        className={styles.root}
        value={[value]}
        onValueChange={([next]) => onValueChange(next)}
        onValueCommit={
          onValueCommit ? ([next]) => onValueCommit(next) : undefined
        }
        min={min}
        max={max}
        step={step}
        disabled={disabled}
      >
        <RadixSlider.Track className={styles.track}>
          <RadixSlider.Range className={styles.range} />
        </RadixSlider.Track>
        <RadixSlider.Thumb
          className={styles.thumb}
          aria-labelledby={labelId}
          aria-valuetext={format(value)}
        />
      </RadixSlider.Root>
    </div>
  );
}

import styles from "./Switch.module.css";
import { cx } from "./cx";
import * as RadixSwitch from "@radix-ui/react-switch";
import { ComponentPropsWithoutRef, forwardRef, useId } from "react";

export interface SwitchProps extends ComponentPropsWithoutRef<
  typeof RadixSwitch.Root
> {
  /** Visible label; without it, pass aria-label. */
  label?: string;
}

export const Switch = forwardRef<HTMLButtonElement, SwitchProps>(
  function Switch({ label, id, className, ...props }, ref) {
    const generatedId = useId();
    const switchId = id ?? generatedId;
    const control = (
      <RadixSwitch.Root
        ref={ref}
        id={switchId}
        className={cx(styles.root, className)}
        {...props}
      >
        <RadixSwitch.Thumb className={styles.thumb} />
      </RadixSwitch.Root>
    );
    if (!label) {
      return control;
    }
    return (
      <span className={styles.field}>
        {control}
        <label className={styles.label} htmlFor={switchId}>
          {label}
        </label>
      </span>
    );
  },
);

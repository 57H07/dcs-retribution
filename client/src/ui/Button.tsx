import styles from "./Button.module.css";
import { cx } from "./cx";
import { Slot } from "@radix-ui/react-slot";
import { ButtonHTMLAttributes, forwardRef } from "react";

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
export type ButtonSize = "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Renders the single child (e.g. a link) with the button styles. */
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    { variant = "secondary", size = "md", asChild, className, type, ...props },
    ref,
  ) {
    const Component = asChild ? Slot : "button";
    return (
      <Component
        ref={ref}
        type={asChild ? undefined : (type ?? "button")}
        data-variant={variant}
        className={cx(
          styles.button,
          styles[variant],
          size === "lg" && styles.lg,
          className,
        )}
        {...props}
      />
    );
  },
);

export interface IconButtonProps extends Omit<
  ButtonProps,
  "asChild" | "aria-label"
> {
  /** Required: an icon-only button has no visible text. */
  "aria-label": string;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton({ variant = "ghost", className, ...props }, ref) {
    return (
      <Button
        ref={ref}
        variant={variant}
        className={cx(styles.icon, className)}
        {...props}
      />
    );
  },
);

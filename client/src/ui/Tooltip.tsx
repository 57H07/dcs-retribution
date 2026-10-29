import styles from "./Tooltip.module.css";
import * as RadixTooltip from "@radix-ui/react-tooltip";
import { ReactElement, ReactNode } from "react";

export interface TooltipProps {
  content: ReactNode;
  /** One focusable element (a Button...), shown on hover and on focus. */
  children: ReactElement;
  side?: "top" | "right" | "bottom" | "left";
  delayDuration?: number;
  /** Controlled state, for tests and tours. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/**
 * Each tooltip carries its own Radix provider, so screens need no setup.
 * Put the information somewhere reachable too: a tooltip is a hint.
 */
export function Tooltip({
  content,
  children,
  side = "top",
  delayDuration = 400,
  open,
  onOpenChange,
}: TooltipProps) {
  return (
    <RadixTooltip.Provider delayDuration={delayDuration}>
      <RadixTooltip.Root open={open} onOpenChange={onOpenChange}>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            className={styles.content}
            side={side}
            sideOffset={6}
            collisionPadding={8}
          >
            {content}
            <RadixTooltip.Arrow className={styles.arrow} />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}

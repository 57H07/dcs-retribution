import { IconButton } from "./Button";
import styles from "./SidePanel.module.css";
import { cx } from "./cx";
import * as Collapsible from "@radix-ui/react-collapsible";
import { ReactNode, useId, useState } from "react";

export interface SidePanelProps {
  title: string;
  side?: "left" | "right";
  /** Controlled state; leave undefined to let the panel keep its own. */
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: ReactNode;
  className?: string;
}

/** A collapsible aside: collapsed, it leaves a rail with its toggle (W15). */
export function SidePanel({
  title,
  side = "left",
  open,
  defaultOpen = true,
  onOpenChange,
  children,
  className,
}: SidePanelProps) {
  const titleId = useId();
  const [ownOpen, setOwnOpen] = useState(defaultOpen);
  const isOpen = open ?? ownOpen;
  const setOpen = (next: boolean) => {
    if (open === undefined) {
      setOwnOpen(next);
    }
    onOpenChange?.(next);
  };
  // The chevron points to where the panel goes.
  const pointsLeft = (side === "left") === isOpen;

  return (
    <Collapsible.Root asChild open={isOpen} onOpenChange={setOpen}>
      <aside
        className={cx(styles.panel, styles[side], className)}
        aria-labelledby={titleId}
      >
        <div className={styles.header}>
          <h2 id={titleId} className={styles.title} hidden={!isOpen}>
            {title}
          </h2>
          <Collapsible.Trigger asChild>
            <IconButton
              aria-label={isOpen ? `Collapse ${title}` : `Expand ${title}`}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <path d={pointsLeft ? "M15 6l-6 6 6 6" : "M9 6l6 6-6 6"} />
              </svg>
            </IconButton>
          </Collapsible.Trigger>
        </div>
        <Collapsible.Content className={styles.content}>
          {children}
        </Collapsible.Content>
      </aside>
    </Collapsible.Root>
  );
}

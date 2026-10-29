import styles from "./ListCard.module.css";
import { cx } from "./cx";
import { ReactNode } from "react";

export interface ListCardProps {
  title: ReactNode;
  /** Before the title, e.g. a TaskTag or a MilSymbol. */
  leading?: ReactNode;
  /** Right of the title, in mono, e.g. "TOT 07:12". */
  meta?: ReactNode;
  subtitle?: ReactNode;
  /** Extra rows under the subtitle (gauges...). */
  children?: ReactNode;
  selected?: boolean;
  /** Makes the card a button; without it, the card is static. */
  onSelect?: () => void;
  disabled?: boolean;
  className?: string;
}

export function ListCard({
  title,
  leading,
  meta,
  subtitle,
  children,
  selected,
  onSelect,
  disabled,
  className,
}: ListCardProps) {
  const content = (
    <span className={styles.body}>
      <span className={styles.header}>
        {leading}
        <span className={styles.title}>{title}</span>
        {meta && <span className={styles.meta}>{meta}</span>}
      </span>
      {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
      {children}
    </span>
  );
  const common = {
    className: cx(styles.card, className),
    "data-selected": selected ? "" : undefined,
  };
  if (!onSelect) {
    return <div {...common}>{content}</div>;
  }
  return (
    <button
      type="button"
      {...common}
      aria-pressed={selected ?? false}
      disabled={disabled}
      onClick={onSelect}
    >
      {content}
    </button>
  );
}

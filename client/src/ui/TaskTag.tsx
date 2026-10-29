import styles from "./TaskTag.module.css";
import { cx } from "./cx";
import { taskFamily, vars } from "./tokens";

export interface TaskTagProps {
  /** A FlightType value as sent by the API, e.g. "BARCAP" or "Strike". */
  task: string;
  size?: "md" | "lg";
  className?: string;
}

export function TaskTag({ task, size = "md", className }: TaskTagProps) {
  const family = taskFamily(task);
  return (
    <span
      className={cx(styles.tag, size === "lg" && styles.lg, className)}
      data-task-family={family}
      style={{ color: vars.task[family].fg, background: vars.task[family].bg }}
    >
      {task}
    </span>
  );
}

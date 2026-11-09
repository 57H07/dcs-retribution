// Marks a package whose target is a campaign objective in progress (#194).
import styles from "./ObjectiveBadge.module.css";

export function ObjectiveBadge({ objectives }: { objectives: string[] }) {
  if (objectives.length === 0) {
    return null;
  }
  const names = objectives.join(", ");
  return (
    <span
      className={styles.badge}
      role="img"
      aria-label={`Objective: ${names}`}
      title={`Objective: ${names}`}
    >
      Objective
    </span>
  );
}

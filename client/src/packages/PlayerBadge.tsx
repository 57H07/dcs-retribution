// Marks a flight with player slots, so the player's packages stand out (#215).
import { PackageFlight } from "../api/liberationApi";
import { playersLabel } from "../command/packages/packageFormat";
import styles from "./PlayerBadge.module.css";

export function PlayerBadge({ flight }: { flight: PackageFlight }) {
  const label = playersLabel(flight);
  if (label === undefined) {
    return null;
  }
  return (
    <span className={styles.badge} role="img" aria-label={label} title={label}>
      {label}
    </span>
  );
}

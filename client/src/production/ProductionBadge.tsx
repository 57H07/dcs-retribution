// Top bar badge of Production & repairs (issue #182): how many items are in progress
// and the turns until the next one ends. Opens the screen.
import { useGetProductionQuery } from "../api/liberationApi";
import { PATHS } from "../shell/paths";
import styles from "./Production.module.css";
import { turnsText } from "./ProductionScreen";
import { useNavigate } from "react-router-dom";

export function ProductionBadge() {
  const { data } = useGetProductionQuery();
  const navigate = useNavigate();
  if (!data) {
    return null;
  }
  const count = data.in_progress.length;
  const next = data.next_end_turns;
  const text = next != null ? `${count} · ${turnsText(next)}` : `${count}`;
  return (
    <button
      type="button"
      className={styles.badge}
      data-active={count > 0 ? "true" : undefined}
      title="Production & repairs"
      aria-label={`Production and repairs: ${count} in progress${
        next != null ? `, next ends in ${turnsText(next)}` : ""
      }`}
      onClick={() => navigate(PATHS.production)}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <path d="M3 21h18M5 21V9l5 3V9l5 3V5h4v16" />
      </svg>
      {text}
    </button>
  );
}

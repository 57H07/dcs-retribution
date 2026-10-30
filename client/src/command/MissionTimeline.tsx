// Mission timeline (WEB-01.4), the bottom strip of the command view: friendly
// packages on the mission time axis, from first startup to last landing, with
// their TOT and the simulation clock. Clicking a package selects it for the map
// and the packages panel (selectionSlice).
import { useAppDispatch, useAppSelector } from "../app/hooks";
import { selectSelectedFlightId } from "../api/flightsSlice";
import {
  useGetTimelineQuery,
  useGetTopBarQuery,
} from "../api/liberationApi";
import {
  selectedPackageId,
  selectPackage,
  selectSelectedPackageKey,
} from "../api/selectionSlice";
import { taskFamily, vars } from "../ui";
import styles from "./MissionTimeline.module.css";
import {
  axisPercent,
  clockLabel,
  layoutBars,
  simOffset,
  timeAxis,
} from "./timeline";

const LANE_HEIGHT = 20;

export function MissionTimeline() {
  const dispatch = useAppDispatch();
  const { data: timeline } = useGetTimelineQuery();
  // The top bar query is polled every second while the sim runs (TurnActions).
  const { data: bar } = useGetTopBarQuery();
  const packageKey = useAppSelector(selectSelectedPackageKey);
  const selectedFlight = useAppSelector(selectSelectedFlightId);

  if (timeline == null || timeline.packages.length === 0) {
    return <p className={styles.empty}>No package scheduled yet.</p>;
  }

  const simTime = bar?.sim.time;
  const cursor =
    simTime != null ? simOffset(timeline.start_time, simTime) : null;
  const axis = timeAxis(timeline.start_time, timeline.packages, cursor);
  const bars = layoutBars(axis, timeline.packages);
  const lanes = Math.max(...bars.map((b) => b.lane)) + 1;
  const selected = selectedPackageId(
    packageKey,
    selectedFlight,
    timeline.packages,
  );

  return (
    <div className={styles.timeline}>
      <div className={styles.scale} aria-hidden="true">
        {axis.ticks.map((tick) => (
          <span
            key={tick}
            className={styles.tick}
            style={{ left: `${axisPercent(axis, tick)}%` }}
          >
            {clockLabel(timeline.start_time, tick)}
          </span>
        ))}
      </div>
      <div
        className={styles.track}
        style={{ height: `${lanes * LANE_HEIGHT + 8}px` }}
      >
        {axis.ticks.map((tick) => (
          <span
            key={tick}
            className={styles.grid}
            style={{ left: `${axisPercent(axis, tick)}%` }}
          />
        ))}
        {bars.map(({ pkg, left, width, tot, lane }) => {
          const colors = vars.task[taskFamily(pkg.task)];
          const totLabel = clockLabel(timeline.start_time, pkg.tot);
          const label = [pkg.task, pkg.target, `TOT ${totLabel}`]
            .filter((part) => part !== "")
            .join(" · ");
          return (
            <button
              key={pkg.id}
              type="button"
              className={styles.bar}
              data-task-family={taskFamily(pkg.task)}
              aria-pressed={selected === pkg.id}
              title={`${label} (${clockLabel(
                timeline.start_time,
                pkg.startup,
              )} - ${clockLabel(timeline.start_time, pkg.landing)})`}
              style={{
                left: `${left}%`,
                width: `${width}%`,
                top: `${4 + lane * LANE_HEIGHT}px`,
                color: colors.fg,
                background: colors.bg,
                borderLeftColor: colors.fg,
              }}
              onClick={() => selectPackage(dispatch, pkg.id, pkg.flight_ids[0])}
            >
              <span className={styles.label}>{label}</span>
              <span
                className={styles.tot}
                data-testid="tot-marker"
                style={{ left: `${tot}%`, background: colors.fg }}
              />
            </button>
          );
        })}
        {cursor !== null && (
          <span
            className={styles.cursor}
            role="img"
            aria-label={`Simulation time ${simTime}`}
            style={{ left: `${axisPercent(axis, cursor)}%` }}
          />
        )}
      </div>
    </div>
  );
}

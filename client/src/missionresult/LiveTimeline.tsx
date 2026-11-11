// Live package timeline of the waiting screen: the friendly packages of the
// mission being played in DCS, with the mission clock DCS reports in state.json
// (`mission_elapsed`). Between two reports the clock runs on at 1x for a few
// seconds (timeline.liveOffset), so the cursor moves smoothly.
import { useGetTimelineQuery } from "../api/liberationApi";
import { TimelineChart } from "../command/MissionTimeline";
import {
  clockLabel,
  liveOffset,
  packageProgress,
  playerLabel,
} from "../command/timeline";
import styles from "./WaitingScreen.module.css";
import { useEffect, useState } from "react";

const TICK_MS = 1000;

/** Seconds since the mission start, ticking between two reports of DCS. */
export function useLiveMissionClock(
  elapsed: number | null | undefined,
  ended: boolean,
): number | null {
  const [now, setNow] = useState(() => Date.now());
  const [reportedAt, setReportedAt] = useState(() => Date.now());

  useEffect(() => {
    const at = Date.now();
    setReportedAt(at);
    setNow(at);
  }, [elapsed]);

  const running = elapsed != null && !ended;
  useEffect(() => {
    if (!running) {
      return undefined;
    }
    const timer = window.setInterval(() => setNow(Date.now()), TICK_MS);
    return () => window.clearInterval(timer);
  }, [running]);

  if (elapsed == null) {
    return null;
  }
  return liveOffset(elapsed, now - reportedAt, ended);
}

function clock(startTime: string, offset: number): string {
  const seconds = Math.floor(offset % 60);
  return `${clockLabel(startTime, offset)}:${seconds
    .toString()
    .padStart(2, "0")}`;
}

export function LiveTimeline({
  elapsed,
  ended,
}: {
  elapsed: number | null | undefined;
  ended: boolean;
}) {
  const { data: timeline } = useGetTimelineQuery();
  const cursor = useLiveMissionClock(elapsed, ended);

  if (timeline == null || timeline.packages.length === 0) {
    return null;
  }

  const time = cursor === null ? null : clock(timeline.start_time, cursor);
  const mine = timeline.packages.filter((pkg) => playerLabel(pkg) !== null);

  return (
    <section className={styles.panel} aria-label="Package timeline">
      <div className={styles.timelineHeader}>
        <span className={styles.cardLabel}>Package timeline</span>
        <span className={styles.missionClock} data-testid="mission-clock">
          {time === null ? "Waiting for the DCS clock" : `Mission time ${time}`}
        </span>
      </div>
      {mine.length > 0 && (
        <ul className={styles.playerPackages} aria-label="Your packages">
          {mine.map((pkg) => {
            const what = [pkg.task, pkg.target]
              .filter((part) => part !== "")
              .join(" · ");
            const phase =
              cursor === null ? null : packageProgress(pkg, cursor).phase;
            return (
              <li key={pkg.id} className={styles.playerPackage}>
                <span className={styles.playerChip}>{playerLabel(pkg)}</span>
                <span>{what}</span>
                <span className={styles.missionClock}>
                  TOT {clockLabel(timeline.start_time, pkg.tot)}
                </span>
                {phase !== null && (
                  <span className={styles.playerPhase}>{phase}</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
      <div className={styles.timelineBody}>
        <TimelineChart
          timeline={timeline}
          cursor={cursor}
          cursorLabel={time === null ? undefined : `Mission time ${time}`}
          showProgress
        />
      </div>
    </section>
  );
}

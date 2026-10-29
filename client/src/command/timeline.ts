// Layout of the mission timeline (WEB-01.4). Geometry only: every time comes
// from the server (`GET /game/timeline`), as seconds since the mission start.
import { TimelinePackage } from "../api/liberationApi";

const DAY = 24 * 3600;
const STEPS_MIN = [5, 10, 15, 30, 60, 120, 240];
const MAX_TICKS = 8;

/** "HH:MM:SS" (or "HH:MM") -> seconds since midnight; null if malformed. */
export function clockSeconds(clock: string): number | null {
  const match = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(clock);
  if (match === null) {
    return null;
  }
  return +match[1] * 3600 + +match[2] * 60 + +(match[3] ?? 0);
}

/**
 * Seconds of the sim clock `simTime` since the mission start `startTime`, both
 * "HH:MM:SS"; past midnight the clock wraps, the offset keeps counting.
 */
export function simOffset(startTime: string, simTime: string): number | null {
  const start = clockSeconds(startTime);
  const now = clockSeconds(simTime);
  if (start === null || now === null) {
    return null;
  }
  return (((now - start) % DAY) + DAY) % DAY;
}

/** "HH:MM" of the clock `offset` seconds after `startTime`. */
export function clockLabel(startTime: string, offset: number): string {
  const start = clockSeconds(startTime) ?? 0;
  const total = (((start + offset) % DAY) + DAY) % DAY;
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
}

export interface Axis {
  /** Offsets (seconds since mission start) of the left and right edges. */
  from: number;
  to: number;
  /** Offsets of the grid lines, on round clock times. */
  ticks: number[];
}

/**
 * The time axis: from the earliest startup (or the cursor) to the latest
 * landing, widened to round clock times, with at most 8 grid lines.
 */
export function timeAxis(
  startTime: string,
  packages: TimelinePackage[],
  cursor: number | null = null,
): Axis {
  const times = packages.flatMap((p) => [p.startup, p.landing]);
  if (cursor !== null) {
    times.push(cursor);
  }
  if (times.length === 0) {
    times.push(0);
  }
  const min = Math.min(...times);
  const max = Math.max(...times, min + 60);
  const span = max - min;
  const step =
    (STEPS_MIN.find((s) => span / (s * 60) <= MAX_TICKS - 1) ??
      STEPS_MIN[STEPS_MIN.length - 1]) * 60;
  // Round in clock time so that grid lines fall on 06:30, 07:00...
  const start = clockSeconds(startTime) ?? 0;
  const from = Math.floor((start + min) / step) * step - start;
  const to = Math.ceil((start + max) / step) * step - start;
  const ticks: number[] = [];
  for (let t = from; t <= to; t += step) {
    ticks.push(t);
  }
  return { from, to, ticks };
}

/** Position of `offset` on the axis, in percent of its width (0-100). */
export function axisPercent(axis: Axis, offset: number): number {
  const width = axis.to - axis.from;
  if (width <= 0) {
    return 0;
  }
  return ((offset - axis.from) / width) * 100;
}

export interface Bar {
  pkg: TimelinePackage;
  /** Percent of the axis width. */
  left: number;
  width: number;
  /** TOT marker, in percent of the bar width. */
  tot: number;
  /** Row of the bar: overlapping packages go to separate rows. */
  lane: number;
}

/** One bar per package, from first startup to last landing, packed in rows. */
export function layoutBars(axis: Axis, packages: TimelinePackage[]): Bar[] {
  const sorted = [...packages].sort(
    (a, b) => a.startup - b.startup || a.landing - b.landing,
  );
  const laneEnds: number[] = [];
  return sorted.map((pkg) => {
    const end = Math.max(pkg.landing, pkg.startup);
    let lane = laneEnds.findIndex((laneEnd) => laneEnd <= pkg.startup);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(end);
    } else {
      laneEnds[lane] = end;
    }
    const left = axisPercent(axis, pkg.startup);
    const width = axisPercent(axis, end) - left;
    const duration = end - pkg.startup;
    const tot =
      duration > 0
        ? Math.min(100, Math.max(0, ((pkg.tot - pkg.startup) / duration) * 100))
        : 0;
    return { pkg, left, width, tot, lane };
  });
}

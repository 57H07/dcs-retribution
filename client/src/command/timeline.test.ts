import { TimelinePackage } from "../api/liberationApi";
import {
  axisPercent,
  clockLabel,
  layoutBars,
  simOffset,
  timeAxis,
} from "./timeline";

function pkg(
  id: string,
  startup: number,
  tot: number,
  landing: number,
): TimelinePackage {
  return {
    id,
    task: "Strike",
    target: id,
    startup,
    tot,
    landing,
    flight_ids: [id],
  };
}

const MIN = 60;

describe("time axis", () => {
  it("spans the packages on round clock times", () => {
    // Mission at 06:40; packages from 06:45 to 07:50.
    const axis = timeAxis("06:40:00", [pkg("a", 5 * MIN, 40 * MIN, 70 * MIN)]);
    expect(clockLabel("06:40:00", axis.from)).toBe("06:40");
    expect(clockLabel("06:40:00", axis.to)).toBe("07:50");
    expect(axis.ticks.map((t) => clockLabel("06:40:00", t))).toEqual([
      "06:40",
      "06:50",
      "07:00",
      "07:10",
      "07:20",
      "07:30",
      "07:40",
      "07:50",
    ]);
  });

  it("widens the step on long missions and includes the cursor", () => {
    const axis = timeAxis(
      "06:30:00",
      [pkg("a", 30 * MIN, 120 * MIN, 240 * MIN)],
      0,
    );
    expect(axis.ticks.length).toBeLessThanOrEqual(8);
    expect(clockLabel("06:30:00", axis.from)).toBe("06:00");
    expect(clockLabel("06:30:00", axis.to)).toBe("11:00");
  });
});

describe("bar layout", () => {
  const axis = { from: 0, to: 100 * MIN, ticks: [] };

  it("places a bar from startup to landing with its TOT marker", () => {
    const [bar] = layoutBars(axis, [pkg("a", 10 * MIN, 40 * MIN, 60 * MIN)]);
    expect(bar.left).toBeCloseTo(10);
    expect(bar.width).toBeCloseTo(50);
    expect(bar.tot).toBeCloseTo(60);
    expect(bar.lane).toBe(0);
  });

  it("puts overlapping packages on separate rows and reuses free rows", () => {
    const bars = layoutBars(axis, [
      pkg("late", 70 * MIN, 80 * MIN, 90 * MIN),
      pkg("first", 0, 20 * MIN, 50 * MIN),
      pkg("overlap", 10 * MIN, 30 * MIN, 60 * MIN),
    ]);
    expect(bars.map((b) => [b.pkg.id, b.lane])).toEqual([
      ["first", 0],
      ["overlap", 1],
      ["late", 0],
    ]);
  });

  it("clamps a TOT outside the bar", () => {
    const [bar] = layoutBars(axis, [pkg("a", 10 * MIN, 90 * MIN, 30 * MIN)]);
    expect(bar.tot).toBe(100);
  });
});

describe("simulation cursor", () => {
  it("is the sim clock offset from the mission start", () => {
    expect(simOffset("06:40:00", "06:40:00")).toBe(0);
    expect(simOffset("06:40:00", "07:10:30")).toBe(30 * MIN + 30);
  });

  it("keeps counting past midnight", () => {
    expect(simOffset("23:50:00", "00:10:00")).toBe(20 * MIN);
  });

  it("is null on a malformed clock", () => {
    expect(simOffset("06:40:00", "soon")).toBeNull();
  });

  it("maps onto the axis", () => {
    expect(axisPercent({ from: 0, to: 200, ticks: [] }, 50)).toBe(25);
  });
});

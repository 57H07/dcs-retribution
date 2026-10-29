import { selectFlight } from "../api/flightsSlice";
import { Timeline } from "../api/liberationApi";
import { selectedPackageId } from "../api/selectionSlice";
import { recordFetch, restoreFetch } from "../shell/testing";
import { renderWithProviders } from "../testutils";
import { MissionTimeline } from "./MissionTimeline";
import { topBar } from "./testdata";
import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

afterEach(restoreFetch);

const TIMELINE: Timeline = {
  start_time: "06:30:00",
  packages: [
    {
      id: "strike-lead",
      task: "Strike",
      target: "Ammo depot",
      startup: 600,
      tot: 2400,
      landing: 4200,
      flight_ids: ["strike-lead", "strike-escort"],
    },
    {
      id: "cap-lead",
      task: "BARCAP",
      target: "Krymsk",
      startup: 0,
      tot: 1200,
      landing: 5400,
      flight_ids: ["cap-lead"],
    },
  ],
};

function render(timeline: Timeline | null, simTime = "06:40:00") {
  recordFetch(204, undefined, {
    "/game/timeline": timeline,
    "/game/top-bar": topBar({ sim: { speed: "paused", time: simTime } }),
  });
  return renderWithProviders(<MissionTimeline />);
}

describe("mission timeline", () => {
  it("says so when no package is scheduled", async () => {
    render({ start_time: "06:30:00", packages: [] });
    expect(
      await screen.findByText("No package scheduled yet."),
    ).toBeInTheDocument();
  });

  it("draws one bar per package with its task colour and TOT", async () => {
    render(TIMELINE);
    const strike = await screen.findByRole("button", {
      name: "Strike · Ammo depot · TOT 07:10",
    });
    expect(strike).toHaveAttribute("data-task-family", "strike");
    expect(strike.style.color).toBe("var(--ui-task-strike-fg)");
    expect(
      screen.getByRole("button", { name: "BARCAP · Krymsk · TOT 06:50" }),
    ).toHaveAttribute("data-task-family", "air");
    expect(screen.getAllByTestId("tot-marker")).toHaveLength(2);
    expect(screen.getByText("07:00")).toBeInTheDocument();
  });

  it("places the cursor at the simulation time", async () => {
    render(TIMELINE, "06:45:00");
    const cursor = await screen.findByRole("img", {
      name: "Simulation time 06:45:00",
    });
    // Axis 06:30-08:00: 06:45 is at one sixth.
    expect(parseFloat(cursor.style.left)).toBeCloseTo(100 / 6);
  });

  it("selects the package and its lead flight on click", async () => {
    const { store } = render(TIMELINE);
    const strike = await screen.findByRole("button", {
      name: /^Strike/,
    });
    await userEvent.click(strike);
    expect(store.getState().selection.packageId).toBe("strike-lead");
    expect(store.getState().flights.selected).toBe("strike-lead");
    expect(strike).toHaveAttribute("aria-pressed", "true");
  });

  it("follows a flight selected on the map", async () => {
    const { store } = render(TIMELINE);
    const strike = await screen.findByRole("button", { name: /^Strike/ });
    act(() => {
      store.dispatch(selectFlight("strike-escort"));
    });
    expect(strike).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("button", { name: /^BARCAP/ }),
    ).toHaveAttribute("aria-pressed", "false");
  });
});

describe("selected package", () => {
  const packages = TIMELINE.packages;

  it("prefers the explicit package key", () => {
    expect(selectedPackageId("cap-lead", "strike-escort", packages)).toBe(
      "cap-lead",
    );
  });

  it("falls back to the package of the selected flight", () => {
    expect(selectedPackageId(null, "strike-escort", packages)).toBe(
      "strike-lead",
    );
    expect(selectedPackageId("gone", null, packages)).toBeNull();
  });
});

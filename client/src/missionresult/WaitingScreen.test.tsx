import { liberationApi, Tags } from "../api/liberationApi";
import type { MissionResult } from "../api/liberationApi";
import { recordFetch, renderShell, restoreFetch } from "../shell/testing";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const RESULT = "/game/mission/result";
const MIZ = "C:\\Saved Games\\DCS\\Missions\\retribution_nextturn.miz";

function result(overrides: Partial<MissionResult> = {}): MissionResult {
  return {
    status: "waiting",
    miz_path: MIZ,
    state_path: "C:\\Retribution\\state.json",
    mission_ended: false,
    losses: [],
    ...overrides,
  };
}

const LOSSES = {
  player_country: "Ukraine",
  enemy_country: "Russia",
  losses: [
    { label: "Aircraft lost", blue: 1, red: 4 },
    { label: "Bases lost", blue: 0, red: 1 },
  ],
};

function accept() {
  return screen.getByRole("button", { name: "Review results" });
}

describe("WaitingScreen", () => {
  afterEach(restoreFetch);

  it("shows the mission file while waiting for state.json", async () => {
    recordFetch(204, undefined, { [RESULT]: result() });
    renderShell("/waiting");
    expect(
      await screen.findByRole("heading", {
        name: "Waiting for mission result",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(MIZ)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Waiting for state.json",
    );
    expect(screen.getByText("C:\\Retribution\\state.json")).toBeInTheDocument();
    expect(accept()).toBeDisabled();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows the losses of a mission being played", async () => {
    recordFetch(204, undefined, {
      [RESULT]: result({ status: "detected", ...LOSSES }),
    });
    renderShell("/waiting");
    expect(
      await screen.findByRole("heading", { name: "Mission is being played" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Mission in progress");
    const table = screen.getByRole("table", { name: "Mission status" });
    expect(
      within(table).getByRole("columnheader", { name: "Ukraine (OwnFor)" }),
    ).toBeInTheDocument();
    expect(
      within(table).getByRole("columnheader", { name: "Russia (OpFor)" }),
    ).toBeInTheDocument();
    expect(within(table).getByText("Aircraft lost")).toBeInTheDocument();
    expect(accept()).toBeDisabled();
  });

  it("reports a state.json that cannot be read", async () => {
    recordFetch(204, undefined, {
      [RESULT]: result({
        status: "error",
        error: "Could not read state.json: Expecting value",
      }),
    });
    renderShell("/waiting");
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Could not read state.json",
    );
    expect(
      screen.getByText("Could not read state.json: Expecting value"),
    ).toBeInTheDocument();
  });

  it("opens the report of a finished mission", async () => {
    const calls = recordFetch(204, undefined, {
      [RESULT]: result({ status: "detected", mission_ended: true, ...LOSSES }),
    });
    const { router } = renderShell("/waiting");
    expect(
      await screen.findByRole("heading", { name: "Mission is over" }),
    ).toBeInTheDocument();
    // Already over when the screen opened: it stays until asked.
    expect(router.state.location.pathname).toBe("/waiting");
    await userEvent.click(accept());
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/debrief"),
    );
    // Reviewing applies nothing.
    expect(calls).toEqual([]);
  });

  it("shows the report when the mission ends", async () => {
    const gets: Record<string, unknown> = {
      [RESULT]: result({ status: "detected", ...LOSSES }),
    };
    recordFetch(204, undefined, gets);
    const { router, store } = renderShell("/waiting");
    await screen.findByRole("heading", { name: "Mission is being played" });
    gets[RESULT] = result({ status: "detected", mission_ended: true });
    store.dispatch(liberationApi.util.invalidateTags([Tags.MISSION_RESULT]));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/debrief"),
    );
  });

  it("aborts the mission and goes back to the map", async () => {
    const calls = recordFetch(204, undefined, { [RESULT]: result() });
    const { router } = renderShell("/waiting");
    await userEvent.click(
      await screen.findByRole("button", { name: "Abort mission" }),
    );
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(calls).toMatchObject([{ method: "POST", path: `${RESULT}/cancel` }]);
  });

  it("loads a state.json through the native dialog", async () => {
    const calls = recordFetch(
      204,
      undefined,
      { [RESULT]: result() },
      { [`${RESULT}/file`]: { body: result() } },
    );
    const { router } = renderShell("/waiting");
    await userEvent.click(
      await screen.findByRole("button", { name: "Load state.json" }),
    );
    await waitFor(() =>
      expect(calls).toMatchObject([{ method: "POST", path: `${RESULT}/file` }]),
    );
    expect(router.state.location.pathname).toBe("/waiting");
  });

  it("shows the package timeline at the mission time of DCS", async () => {
    recordFetch(204, undefined, {
      [RESULT]: result({
        status: "detected",
        mission_elapsed: 30 * 60 + 15,
        ...LOSSES,
      }),
      "/game/timeline": {
        start_time: "08:00:00",
        packages: [
          {
            id: "p1",
            task: "Strike",
            target: "Bridge",
            startup: 10 * 60,
            tot: 25 * 60,
            landing: 50 * 60,
            flight_ids: ["f1"],
            players: 1,
          },
          {
            id: "p2",
            task: "BARCAP",
            target: "Kutaisi",
            startup: 60 * 60,
            tot: 70 * 60,
            landing: 90 * 60,
            flight_ids: ["f2"],
            players: 0,
          },
        ],
      },
    });
    renderShell("/waiting");
    const timeline = await screen.findByRole("region", {
      name: "Package timeline",
    });
    expect(within(timeline).getByTestId("mission-clock")).toHaveTextContent(
      /Mission time 08:30:1\d/,
    );
    expect(
      within(timeline).getByRole("img", { name: /Mission time 08:30/ }),
    ).toBeInTheDocument();
    const [strike, barcap] = within(timeline).getAllByTitle(/TOT/);
    expect(strike).toHaveAttribute("data-phase", "Egress");
    expect(barcap).toHaveAttribute("data-phase", "Not started");
    // The player's package stands out, on the timeline and above it.
    expect(strike).toHaveAttribute("data-player", "true");
    expect(strike).toHaveTextContent(/^Player/);
    expect(barcap).not.toHaveAttribute("data-player");
    const mine = within(timeline).getByRole("list", { name: "Your packages" });
    const [line] = within(mine).getAllByRole("listitem");
    expect(line).toHaveTextContent("PlayerStrike · BridgeTOT 08:25Egress");
    expect(within(mine).getAllByRole("listitem")).toHaveLength(1);
  });

  it("waits for the DCS clock before placing the cursor", async () => {
    recordFetch(204, undefined, {
      [RESULT]: result({ status: "detected", ...LOSSES }),
      "/game/timeline": {
        start_time: "08:00:00",
        packages: [
          {
            id: "p1",
            task: "Strike",
            target: "Bridge",
            startup: 600,
            tot: 1500,
            landing: 3000,
            flight_ids: ["f1"],
            players: 0,
          },
        ],
      },
    });
    renderShell("/waiting");
    expect(await screen.findByTestId("mission-clock")).toHaveTextContent(
      "Waiting for the DCS clock",
    );
    expect(
      screen.queryByRole("img", { name: /Mission time/ }),
    ).not.toBeInTheDocument();
  });

  it("says when no mission is waiting", async () => {
    recordFetch(204, undefined, {
      [RESULT]: result({ status: "idle", miz_path: undefined }),
    });
    renderShell("/waiting");
    expect(
      await screen.findByText(/No mission is waiting for its result/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Abort mission" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Back to the map" }),
    ).toBeInTheDocument();
  });
});

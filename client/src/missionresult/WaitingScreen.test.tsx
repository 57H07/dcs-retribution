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
  return screen.getByRole("button", { name: "Accept results" });
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

  it("accepts the results of a finished mission", async () => {
    const calls = recordFetch(
      204,
      undefined,
      {
        [RESULT]: result({
          status: "detected",
          mission_ended: true,
          ...LOSSES,
        }),
      },
      {
        [`${RESULT}/accept`]: { body: { turn: 5, campaign_state: "continue" } },
      },
    );
    const { router } = renderShell("/waiting");
    expect(
      await screen.findByRole("heading", { name: "Mission is over" }),
    ).toBeInTheDocument();
    await userEvent.click(accept());
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(calls).toMatchObject([{ method: "POST", path: `${RESULT}/accept` }]);
    expect(await screen.findByText("Results accepted")).toBeInTheDocument();
  });

  it("shows why the results were refused", async () => {
    recordFetch(
      204,
      undefined,
      { [RESULT]: result({ status: "detected", mission_ended: true }) },
      {
        [`${RESULT}/accept`]: {
          status: 409,
          body: { detail: "The mission is still being played." },
        },
      },
    );
    const { router } = renderShell("/waiting");
    await screen.findByRole("heading", { name: "Mission is over" });
    await userEvent.click(accept());
    expect(
      await screen.findByText("The mission is still being played."),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/waiting");
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

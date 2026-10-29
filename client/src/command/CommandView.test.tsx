import { GameUpdateEvents, topBarChanged } from "../api/eventstream";
import { recordFetch, renderShell, restoreFetch } from "../shell/testing";
import {
  formatIncome,
  formatMoney,
  weatherDetails,
  weatherSummary,
} from "./format";
import { missionChecks, topBar } from "./testdata";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

afterEach(restoreFetch);

const TOP_BAR = "/game/top-bar";
const CHECKS = "/game/mission/checks";
const MISSION = { status: 200, body: { path: "C:/Missions/next.miz" } };

describe("command view layout", () => {
  it("has the packages, map, inspector and timeline regions", async () => {
    recordFetch();
    const { container } = renderShell();
    expect(
      screen.getByRole("complementary", { name: "Packages" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Expand Inspector" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Mission timeline" }),
    ).toBeInTheDocument();
    expect(container.querySelector(".leaflet-container")).not.toBeNull();
  });

  it("collapses the side panels and the timeline", async () => {
    recordFetch();
    renderShell();
    await userEvent.click(
      screen.getByRole("button", { name: "Collapse Packages" }),
    );
    expect(
      screen.getByRole("button", { name: "Expand Packages" }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Hide" }));
    expect(screen.getByRole("button", { name: "Show" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("fills the left slot with the packages panel (WEB-01.2)", async () => {
    recordFetch();
    renderShell();
    expect(
      await screen.findByRole("tab", { name: /Packages · 0/ }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Open packages" }),
    ).not.toBeInTheDocument();
  });
});

describe("top bar", () => {
  it("says when no campaign is loaded and disables the turn buttons", async () => {
    recordFetch();
    renderShell();
    expect(await screen.findByText("No campaign loaded")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "End turn" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Take off" })).toBeDisabled();
  });

  it("shows the campaign state from the API", async () => {
    recordFetch(204, undefined, { [TOP_BAR]: topBar() });
    renderShell();
    const header = screen.getByRole("banner");
    expect(await within(header).findByText("Slava Ukraini")).toBeVisible();
    expect(header).toHaveTextContent("Caucasus · Ukraine 2020 vs Russia 2020");
    expect(header).toHaveTextContent("04");
    expect(header).toHaveTextContent("17 MAY 2022 · 06:40");
    expect(header).toHaveTextContent("Scattered 2 · 270°/12 kt");
    expect(header).toHaveTextContent("$1 240M");
    expect(header).toHaveTextContent("+180M/turn");
    expect(header).toHaveTextContent("Air96/132Armor64/52");
    expect(
      screen.getByLabelText(/Cloud base: 2400m \/ 7874ft/),
    ).toBeInTheDocument();
  });

  it("opens the campaign screens", async () => {
    const calls = recordFetch(204, undefined, { [TOP_BAR]: topBar() });
    const { router } = renderShell();
    await userEvent.click(
      await screen.findByRole("button", { name: /Budget/ }),
    );
    await userEvent.click(screen.getByRole("button", { name: /open intel/ }));
    await userEvent.click(screen.getByRole("button", { name: "Transfers" }));
    await waitFor(() => expect(calls).toHaveLength(3));
    expect(calls.map((c) => c.path)).toEqual([
      "/qt/dialogs/finances",
      "/qt/dialogs/intel",
      "/qt/dialogs/transfers",
    ]);
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    // Settings is a web screen (WEB-07.1).
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/settings"),
    );
    expect(calls).toHaveLength(3);
  });
});

describe("turn actions", () => {
  it("offers Begin Campaign on turn 0, without take off", async () => {
    const calls = recordFetch(
      200,
      { turn: 1, campaign_state: "continue" },
      { [TOP_BAR]: topBar({ turn: 0 }) },
    );
    renderShell();
    const begin = await screen.findByRole("button", { name: "Begin Campaign" });
    expect(screen.getByRole("button", { name: "Take off" })).toBeDisabled();
    await userEvent.click(begin);
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe("/game/turn/pass");
  });

  it("shows the player slot count", async () => {
    recordFetch(204, undefined, { [TOP_BAR]: topBar() });
    renderShell();
    expect(await screen.findByText(/Max players/)).toHaveTextContent(
      "Max players 2",
    );
  });

  it("takes off straight away when nothing needs confirming", async () => {
    const calls = recordFetch(
      204,
      undefined,
      { [TOP_BAR]: topBar(), [CHECKS]: missionChecks() },
      { "/game/mission": MISSION },
    );
    renderShell();
    await userEvent.click(
      await screen.findByRole("button", { name: "Take off" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({ method: "POST", path: "/game/mission" });
    expect(await screen.findByText("Mission generated")).toBeInTheDocument();
  });

  it("asks before an AI only mission and stops on No", async () => {
    const calls = recordFetch(204, undefined, {
      [TOP_BAR]: topBar(),
      [CHECKS]: missionChecks({ has_player_pilots: false }),
    });
    renderShell();
    await userEvent.click(
      await screen.findByRole("button", { name: "Take off" }),
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Continue without player pilots?",
    });
    await userEvent.click(within(dialog).getByRole("button", { name: "No" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls).toHaveLength(0);
  });

  it("blocks take off on missing pilots", async () => {
    const calls = recordFetch(204, undefined, {
      [TOP_BAR]: topBar(),
      [CHECKS]: missionChecks({
        has_player_pilots: false,
        flights_missing_pilots: ["DEAD Krasnodar: Viper 1"],
      }),
    });
    renderShell();
    await userEvent.click(
      await screen.findByRole("button", { name: "Take off" }),
    );
    await userEvent.click(
      within(await screen.findByRole("dialog")).getByRole("button", {
        name: "Yes",
      }),
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Flights are missing pilots",
    });
    expect(dialog).toHaveTextContent("DEAD Krasnodar: Viper 1");
    await userEvent.click(
      within(dialog).getAllByRole("button", { name: "Close" })[0],
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls).toHaveLength(0);
  });

  it("fixes past TOTs automatically, then takes off", async () => {
    const calls = recordFetch(
      204,
      undefined,
      {
        [TOP_BAR]: topBar(),
        [CHECKS]: missionChecks({
          packages_starting_in_the_past: ["STRIKE Ammo depot"],
        }),
      },
      {
        "/game/mission/fix-tots": {
          status: 200,
          body: { packages: ["STRIKE Ammo depot"] },
        },
        "/game/mission": MISSION,
      },
    );
    renderShell();
    await userEvent.click(
      await screen.findByRole("button", { name: "Take off" }),
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Continue with past start times?",
    });
    expect(dialog).toHaveTextContent("STRIKE Ammo depot");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Fix TOTs automatically" }),
    );
    await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls.map((c) => c.path)).toEqual([
      "/game/mission/fix-tots",
      "/game/mission",
    ]);
  });

  it("can take off with past TOTs unfixed", async () => {
    const calls = recordFetch(
      204,
      undefined,
      {
        [TOP_BAR]: topBar(),
        [CHECKS]: missionChecks({ packages_starting_in_the_past: ["CAS"] }),
      },
      { "/game/mission": MISSION },
    );
    renderShell();
    await userEvent.click(
      await screen.findByRole("button", { name: "Take off" }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Continue without fixing" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe("/game/mission");
  });

  it("shows the server's refusal", async () => {
    recordFetch(
      204,
      undefined,
      { [TOP_BAR]: topBar(), [CHECKS]: missionChecks() },
      {
        "/game/mission": {
          status: 409,
          body: { detail: "Some flights are missing pilots." },
        },
      },
    );
    renderShell();
    await userEvent.click(
      await screen.findByRole("button", { name: "Take off" }),
    );
    expect(await screen.findByText("Could not take off")).toBeInTheDocument();
    expect(
      screen.getByText("Some flights are missing pilots."),
    ).toBeInTheDocument();
  });

  it("hides the sim speed controls unless enabled", async () => {
    recordFetch(204, undefined, { [TOP_BAR]: topBar() });
    renderShell();
    await screen.findByText("Slava Ukraini");
    expect(
      screen.queryByRole("group", { name: "Simulation speed" }),
    ).toBeNull();
  });

  it("changes the sim speed", async () => {
    const calls = recordFetch(
      200,
      { speed: "5x", time: "06:41:00" },
      { [TOP_BAR]: topBar({ show_sim_speed_controls: true }) },
    );
    renderShell();
    const group = await screen.findByRole("group", {
      name: "Simulation speed",
    });
    expect(
      within(group).getByRole("button", { name: "Paused" }),
    ).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(within(group).getByRole("button", { name: "5x" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: "/game/sim/speed",
      body: { speed: "5x" },
    });
  });
});

describe("live updates", () => {
  const quiet = {
    new_turn: false,
    budget_updated: false,
    game_unloaded: false,
    reset_on_map_center: null,
    new_flights: [],
    updated_flights: [],
    deleted_flights: [],
    updated_control_points: [],
  } as unknown as GameUpdateEvents;

  it("refreshes the top bar on a new turn or a budget change", () => {
    expect(topBarChanged(quiet)).toBe(false);
    expect(topBarChanged({ ...quiet, new_turn: true })).toBe(true);
    expect(topBarChanged({ ...quiet, budget_updated: true })).toBe(true);
    expect(topBarChanged({ ...quiet, deleted_flights: ["f"] })).toBe(true);
  });
});

describe("formatting", () => {
  it("formats money and income", () => {
    expect(formatMoney(1240.4)).toBe("$1 240M");
    expect(formatMoney(-12)).toBe("-$12M");
    expect(formatIncome(180.2)).toBe("+180M/turn");
    expect(formatIncome(-20)).toBe("-20M/turn");
  });

  it("summarises the weather and details it", () => {
    const weather = topBar().weather;
    expect(weatherSummary(weather)).toBe("Scattered 2 · 270°/12 kt");
    expect(weatherDetails(weather)[0]).toBe("Cloud base: 2400m / 7874ft");
    expect(weatherDetails({ ...weather, cloud_base_m: undefined })[0]).toBe(
      "No cloud base",
    );
  });
});

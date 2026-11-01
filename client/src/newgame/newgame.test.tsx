import type {
  AirWingConfig,
  CampaignDefaults,
  CampaignPreview,
  FactionSheet,
  NewGameCampaign,
  NewGameOptions,
} from "../api/liberationApi";
import { setupStore } from "../app/store";
import { AirWingConfigPanel } from "../airwingconfig/AirWingConfigPanel";
import { recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { NewGameScreen } from "./NewGameScreen";
import { RichText } from "./RichText";
import {
  factionDraft,
  filterCampaigns,
  stateFromDefaults,
  toggleUnit,
  addUnit,
  toRequest,
} from "./wizardState";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const GOLAN: NewGameCampaign = {
  id: "golan",
  name: "Battle for Golan",
  theater: "Syria",
  authors: "Khopa",
  description: "<p>Hold the <strong>heights</strong>.</p><script>x()</script>",
  version: "10.0",
  compatible: true,
  era: "Modern",
  start_date: "2010-06-01",
  performance: 1,
  performance_label: "Medium",
  performance_text: "Needs a good computer.",
  recommended_blue_faction: "Israel 2000",
  recommended_red_faction: "Syria 2011",
};

const CAUCASUS: NewGameCampaign = {
  ...GOLAN,
  id: "caucasus",
  name: "Black Sea",
  theater: "Caucasus",
  era: "Cold War",
};

const OLD: NewGameCampaign = {
  ...GOLAN,
  id: "old",
  name: "Old one",
  compatible: false,
  warning: "Another version.",
};

const OPTIONS: NewGameOptions = {
  campaigns: [GOLAN, CAUCASUS, OLD],
  factions: ["Israel 2000", "Syria 2011", "USA 2005"],
  time_periods: [{ name: "Modern - Summer [2010]", start_date: "2010-06-01" }],
  default_time_period: "Modern - Summer [2010]",
  mods: [{ key: "uh_60l", label: "UH-60L Black Hawk" }],
};

const DEFAULTS: CampaignDefaults = {
  settings_pages: [
    {
      id: "difficulty",
      name: "Difficulty",
      sections: [
        {
          name: "General",
          settings: [
            {
              key: "supercarrier",
              label: "Use supercarrier",
              kind: "bool",
              value: false,
              default: false,
              modified: false,
            },
          ],
        },
      ],
    },
  ],
  blue_faction: "Israel 2000",
  red_faction: "Syria 2011",
  start_date: "2010-06-01",
  player_budget: 2000,
  enemy_budget: 1500,
  advanced_iads_available: false,
  no_carrier: false,
  no_lha: true,
  no_player_navy: false,
  no_enemy_navy: false,
  squadrons_start_full: true,
  mods: [],
};

const PREVIEW: CampaignPreview = {
  width: 1,
  height: 0.5,
  bases: [
    { name: "Ramat David", x: 0, y: 0, side: "blue", kind: "AIRBASE" },
    { name: "Damascus", x: 1, y: 0.5, side: "red", kind: "AIRBASE" },
  ],
  links: [{ from_index: 0, to_index: 1, front_line: true }],
  blue_bases: 1,
  red_bases: 1,
  front_lines: 1,
};

const SHEET: FactionSheet = {
  name: "Israel 2000",
  description: "<p>IDF.</p>",
  authors: "Khopa",
  requirements: {},
  has_jtac: true,
  doctrine: "modern",
  doctrines: ["coldwar", "modern"],
  groups: [
    {
      key: "aircraft",
      label: "Aircraft",
      units: ["F-15C", "F-16C"],
      addable: ["F-22A"],
    },
  ],
};

function gets(status: string, more: Record<string, unknown> = {}) {
  return {
    "/new-game/options": OPTIONS,
    "/new-game/generation": { status, step_index: 0, step_count: 0 },
    "/new-game/campaigns/golan/preview": PREVIEW,
    "/new-game/campaigns/golan/defaults": DEFAULTS,
    "/new-game/faction": SHEET,
    ...more,
  };
}

function renderScreen() {
  const router = createMemoryRouter(
    [
      { path: "/new-game", element: <NewGameScreen /> },
      { path: "/", element: <p>command view</p> },
    ],
    { initialEntries: ["/new-game"] },
  );
  render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </Provider>,
  );
  return router;
}

describe("wizard state", () => {
  it("filters by text, theater, era and compatibility", () => {
    const base = {
      query: "",
      theater: null,
      era: null,
      showIncompatible: false,
    };
    const names = (filter: typeof base | Record<string, unknown>) =>
      filterCampaigns(OPTIONS.campaigns, { ...base, ...filter }).map(
        (c) => c.id,
      );
    expect(names({})).toEqual(["golan", "caucasus"]);
    expect(names({ showIncompatible: true })).toHaveLength(3);
    expect(names({ query: "black" })).toEqual(["caucasus"]);
    expect(names({ theater: "Syria" })).toEqual(["golan"]);
    expect(names({ era: "Cold War" })).toEqual(["caucasus"]);
  });

  it("builds the request from the recommendations", () => {
    const state = stateFromDefaults("golan", DEFAULTS, OPTIONS);
    expect(toRequest(state, OPTIONS)).toMatchObject({
      campaign_id: "golan",
      blue: { name: "Israel 2000" },
      red: { name: "Syria 2011" },
      start_date: "2010-06-01",
      player_budget: 2000,
      enemy_budget: 1500,
      no_lha: true,
      squadrons_start_full: true,
      settings: {},
    });
  });

  it("proposes the time period when the campaign has no date", () => {
    const state = stateFromDefaults(
      "golan",
      {
        ...DEFAULTS,
        start_date: undefined,
        time_period: "Modern - Summer [2010]",
      },
      OPTIONS,
    );
    expect(state.timePeriod).toBe("Modern - Summer [2010]");
    expect(toRequest(state, OPTIONS)?.start_date).toBe("2010-06-01");
    expect(
      toRequest({ ...state, timePeriod: null, customDate: "" }, OPTIONS),
    ).toBeUndefined();
  });

  it("sends a seed only when there is one", () => {
    const state = stateFromDefaults("golan", DEFAULTS, OPTIONS);
    expect(toRequest(state, OPTIONS)?.seed).toBeUndefined();
    expect(toRequest({ ...state, seed: "42" }, OPTIONS)?.seed).toBe(42);
  });

  it("takes units out, brings them back and undoes an addition", () => {
    let draft = factionDraft("x");
    draft = toggleUnit(draft, "aircraft", "F-15C");
    expect(draft.removed.aircraft).toEqual(["F-15C"]);
    draft = toggleUnit(draft, "aircraft", "F-15C");
    expect(draft.removed.aircraft).toEqual([]);
    draft = addUnit(draft, "aircraft", "F-22A");
    expect(draft.added.aircraft).toEqual(["F-22A"]);
    draft = toggleUnit(draft, "aircraft", "F-22A");
    expect(draft.added.aircraft).toEqual([]);
  });
});

describe("RichText", () => {
  it("keeps simple tags and drops the others, with their markup", () => {
    const { container } = render(
      <RichText html='<p>a <strong>b</strong></p><script>x()</script><img src="x" onerror="y()"><a href="https://x">c</a>' />,
    );
    expect(container.querySelector("strong")).toHaveTextContent("b");
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("a")).toBeNull();
    expect(container).toHaveTextContent("c");
  });
});

describe("new campaign wizard", () => {
  it("goes through the five steps and sends the full request", async () => {
    const calls = recordFetch(
      200,
      {
        status: "generating",
        step_index: 0,
        step_count: 2,
      },
      gets("idle"),
    );
    const user = userEvent.setup();
    renderScreen();

    expect(
      await screen.findByRole("heading", { name: "Battle for Golan" }),
    ).toBeInTheDocument();
    expect(screen.getByText("heights")).toBeInTheDocument();
    expect(screen.getByText("Blue · Israel 2000")).toBeInTheDocument();
    expect(
      await screen.findByRole("img", { name: /Campaign map preview/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("1 : 1")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next · Factions" }));
    const player = await screen.findByRole("region", {
      name: "Player faction",
    });
    await user.click(await within(player).findByLabelText("F-15C"));

    await user.click(
      screen.getByRole("button", { name: "Next · Campaign options" }),
    );
    await user.click(
      await screen.findByRole("switch", { name: "Use supercarrier" }),
    );

    await user.click(screen.getByRole("button", { name: "Next · Generator" }));
    await user.click(await screen.findByLabelText("UH-60L Black Hawk"));
    await user.type(screen.getByLabelText("Seed"), "7");

    await user.click(screen.getByRole("button", { name: "Next · Summary" }));
    expect(
      await screen.findByRole("heading", { name: "Summary" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Israel 2000 (1 unit change)")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Generate campaign" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/new-game/generation",
      body: {
        campaign_id: "golan",
        blue: { name: "Israel 2000", removed: { aircraft: ["F-15C"] } },
        settings: { supercarrier: true },
        mods: ["uh_60l"],
        seed: 7,
      },
    });
  });

  it("offers only matching campaigns", async () => {
    recordFetch(204, undefined, gets("idle"));
    const user = userEvent.setup();
    renderScreen();
    await screen.findByRole("heading", { name: "Battle for Golan" });
    await user.click(screen.getByRole("button", { name: "Caucasus" }));
    const list = screen.getByRole("list", { name: "Campaigns" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    expect(within(list).getByText("Black Sea")).toBeInTheDocument();
  });

  it("shows the progress of the generation", async () => {
    recordFetch(
      204,
      undefined,
      gets("generating", {
        "/new-game/generation": {
          status: "generating",
          step: "Loading the theater",
          step_index: 0,
          step_count: 2,
        },
      }),
    );
    renderScreen();
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Loading the theater · step 1 of 2",
    );
  });

  it("shows why a generation failed", async () => {
    recordFetch(
      204,
      undefined,
      gets("failed", {
        "/new-game/generation": {
          status: "failed",
          error: "The campaign could not be generated: broken miz",
          step_index: 0,
          step_count: 0,
        },
      }),
    );
    renderScreen();
    expect(await screen.findByRole("alert")).toHaveTextContent("broken miz");
  });

  it("configures the air wing, then starts the campaign", async () => {
    const config: AirWingConfig = {
      replans: false,
      sides: [
        {
          side: "blue",
          faction: "Israel 2000",
          aircraft_options: [],
          squadrons: [],
        },
        {
          side: "red",
          faction: "Syria 2011",
          aircraft_options: [],
          squadrons: [],
        },
      ],
    };
    const calls = recordFetch(
      200,
      { status: "starting", step_index: 0, step_count: 1 },
      gets("configuring", { "/air-wing-config/draft": config }),
    );
    const user = userEvent.setup();
    renderScreen();
    expect(
      await screen.findByRole("heading", { name: "Air wing configuration" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Start campaign" }));
    await waitFor(() =>
      expect(calls.map((call) => call.path)).toContain(
        "/new-game/generation/begin",
      ),
    );
  });

  it("returns to the command view once the campaign is installed", async () => {
    const calls = recordFetch(
      200,
      { status: "idle", step_index: 0, step_count: 0 },
      gets("done"),
    );
    const router = renderScreen();
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    await waitFor(() =>
      expect(calls[0]).toMatchObject({
        method: "DELETE",
        path: "/new-game/generation",
      }),
    );
  });
});

describe("air wing configuration", () => {
  const CONFIG: AirWingConfig = {
    replans: true,
    sides: [
      {
        side: "blue",
        faction: "Israel 2000",
        aircraft_options: [
          {
            aircraft_id: "F-16C",
            aircraft: "F-16C",
            primary_tasks: ["BARCAP"],
            bases: [{ id: "b1", name: "Ramat David" }],
            presets: [],
          },
        ],
        squadrons: [
          {
            id: "s1",
            name: "First",
            nickname: "Bees",
            aircraft: "F-16C",
            aircraft_id: "F-16C",
            primary_task: "BARCAP",
            primary_tasks: ["BARCAP", "CAS"],
            tasks: [{ task: "CAS", auto_assign: false }],
            max_size: 12,
            base_id: "b1",
            bases: [
              { id: "b1", name: "Ramat David" },
              { id: "b2", name: "Haifa" },
            ],
            parking: { required: 12, total: 40, fitting: 30 },
            player_names: ["Maverick"],
            presets: [],
          },
        ],
      },
      { side: "red", faction: "Syria", aircraft_options: [], squadrons: [] },
    ],
  };

  function renderPanel() {
    render(
      <Provider store={setupStore()}>
        <ToastProvider>
          <AirWingConfigPanel target="campaign" />
        </ToastProvider>
      </Provider>,
    );
  }

  const GETS = {
    "/air-wing-config/campaign": CONFIG,
    "/air-wing-config/campaign/squadrons/s1/liveries": [],
    "/air-wing-config/campaign/sides/blue/faction": SHEET,
  };

  it("sends each change as a command and warns about replanning", async () => {
    const calls = recordFetch(204, undefined, GETS);
    const user = userEvent.setup();
    renderPanel();
    expect(await screen.findByText(/replans this turn/)).toBeInTheDocument();
    expect(
      screen.getByText(/Parking slots required: 12 · available: 40/),
    ).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Base"), "b2");
    await user.click(screen.getByRole("checkbox", { name: "CAS" }));
    await user.click(screen.getByRole("button", { name: "Remove squadron" }));
    await waitFor(() => expect(calls).toHaveLength(3));
    expect(calls[0]).toMatchObject({
      method: "PATCH",
      path: "/air-wing-config/campaign/squadrons/s1",
      body: { base_id: "b2" },
    });
    expect(calls[1]).toMatchObject({
      method: "PUT",
      path: "/air-wing-config/campaign/squadrons/s1/auto-assign",
      body: { task: "CAS", enabled: true },
    });
    expect(calls[2]).toMatchObject({
      method: "DELETE",
      path: "/air-wing-config/campaign/squadrons/s1",
    });
  });

  it("adds a unit from the faction tab", async () => {
    const calls = recordFetch(204, undefined, GETS);
    const user = userEvent.setup();
    renderPanel();
    await user.click(
      await screen.findByRole("tab", { name: "Faction OWNFOR" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Add to Aircraft" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/air-wing-config/campaign/sides/blue/faction/units",
      body: { group: "aircraft", unit: "F-22A" },
    });
  });

  it("shows the refusal when the cheat is off", async () => {
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ detail: "Enable Air Wing adjustments" }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      });
    renderPanel();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Enable Air Wing adjustments",
    );
  });
});

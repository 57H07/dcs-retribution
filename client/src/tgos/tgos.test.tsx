import {
  PurchaseQuote,
  TgoPurchaseOptions,
  TgoSheet,
  UnitInfo,
} from "../api/liberationApi";
import { setupStore } from "../app/store";
import { recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { TgoScreen, repairText, unitStateText } from "./TgoScreen";
import { UnitInfoScreen, unitBannerUrl } from "./UnitInfoScreen";
import { PATHS } from "../shell/paths";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const TGO_ID = "tgo-1";
const SHEET_PATH = `/tgos/${TGO_ID}/sheet`;

function unit(overrides: Partial<TgoSheet["units"][number]> = {}) {
  return {
    id: 7,
    name: "SA-10 launcher",
    info_kind: "ground" as const,
    info_name: "SA-10/launcher v2",
    state: "operational" as const,
    turns_remaining: 0,
    repair_turns: 0,
    repair_affordable: false,
    ...overrides,
  };
}

function sheet(overrides: Partial<TgoSheet> = {}): TgoSheet {
  return {
    summary: {
      id: TGO_ID,
      name: "SA-10 Krymsk",
      blue: true,
      sidc: "10031500001301000000",
      category: "LORAD",
      control_point_id: "cp-1",
      control_point_name: "Krymsk",
      distance_to_front_nm: 30,
      units: { current: 1, total: 2 },
      dead: false,
    },
    budget: 500,
    is_building_site: false,
    units: [unit()],
    heading: { degrees: 90, can_adjust: true, to_conflict: 180 },
    can_buy: true,
    disband_value: 50,
    ...overrides,
  };
}

const OPTIONS: TgoPurchaseOptions = {
  force_groups: [
    {
      name: "SA-10",
      layouts: [
        {
          name: "Battery",
          slots: [
            {
              id: 0,
              group_name: "Main",
              options: [
                { id: "launcher", name: "Launcher", price: 25 },
                { id: "other", name: "Other launcher", price: 30 },
              ],
              amount: 2,
              max_amount: 4,
              optional: false,
            },
            {
              id: 1,
              group_name: "Point defense",
              options: [{ id: "tor", name: "Tor", price: 10 }],
              amount: 1,
              max_amount: 1,
              optional: true,
            },
          ],
        },
      ],
    },
    {
      name: "SA-2",
      layouts: [
        {
          name: "Site",
          slots: [
            {
              id: 0,
              group_name: "Main",
              options: [{ id: "sa2", name: "SA-2", price: 5 }],
              amount: 1,
              max_amount: 1,
              optional: false,
            },
          ],
        },
      ],
    },
  ],
};

const QUOTE: PurchaseQuote = {
  price: 60,
  credit: 50,
  cost: 10,
  affordable: true,
};

function renderScreen(
  gets: Record<string, unknown>,
  answers: Parameters<typeof recordFetch>[3] = {},
  initial = `/tgos/${TGO_ID}`,
) {
  const calls = recordFetch(204, undefined, gets, {
    [`/tgos/${TGO_ID}/purchase/quote`]: { status: 200, body: QUOTE },
    ...answers,
  });
  const router = createMemoryRouter(
    [
      { path: "/tgos/:id", element: <TgoScreen /> },
      { path: "/units/:kind/:name", element: <UnitInfoScreen /> },
      { path: "/bases/:id", element: <p>Base screen</p> },
      { path: "/", element: <p>Command view</p> },
    ],
    { initialEntries: ["/", initial] },
  );
  render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </Provider>,
  );
  return { calls, router };
}

describe("status text", () => {
  it("says how long a unit is out", () => {
    expect(unitStateText(unit())).toBe("Operational");
    expect(unitStateText(unit({ state: "destroyed" }))).toBe("Destroyed");
    expect(
      unitStateText(unit({ state: "repairing", turns_remaining: 1 })),
    ).toBe("Repairing · 1 turn left");
    expect(
      unitStateText(unit({ state: "inoperative", turns_remaining: 3 })),
    ).toBe("Inoperative · 3 turns left");
  });

  it("gives the terms of a repair", () => {
    expect(repairText(unit({ repair_cost: 25 }))).toBe("Repair · $25M");
    expect(repairText(unit({ repair_cost: 2.5, repair_turns: 4 }))).toBe(
      "Repair · $2.5M · 4 turns",
    );
  });
});

describe("ground object sheet", () => {
  it("shows the units and repairs one", async () => {
    const { calls } = renderScreen(
      {
        [SHEET_PATH]: sheet({
          units: [
            unit(),
            unit({
              id: 8,
              name: "SA-10 radar",
              state: "destroyed",
              repair_cost: 40,
              repair_affordable: true,
            }),
          ],
        }),
      },
      { [`/tgos/${TGO_ID}/units/8/repair`]: { status: 200, body: sheet() } },
    );
    const units = await screen.findByRole("region", { name: "Units" });
    expect(units).toHaveTextContent("Operational");
    expect(units).toHaveTextContent("Destroyed");
    expect(within(units).getAllByRole("button")).toHaveLength(1);

    await userEvent.click(
      within(units).getByRole("button", { name: "Repair SA-10 radar (8)" }),
    );

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: `/tgos/${TGO_ID}/units/8/repair`,
    });
  });

  it("disables a repair the budget cannot pay, and shows a refusal", async () => {
    renderScreen({
      [SHEET_PATH]: sheet({
        units: [unit({ state: "destroyed", repair_cost: 40 })],
      }),
    });
    expect(
      await screen.findByRole("button", { name: /^Repair SA-10/ }),
    ).toBeDisabled();
  });

  it("shows a refused repair as a toast", async () => {
    renderScreen(
      {
        [SHEET_PATH]: sheet({
          units: [
            unit({
              state: "destroyed",
              repair_cost: 40,
              repair_affordable: true,
            }),
          ],
        }),
      },
      {
        [`/tgos/${TGO_ID}/units/7/repair`]: {
          status: 409,
          body: { detail: "This unit cannot be repaired now." },
        },
      },
    );
    await userEvent.click(
      await screen.findByRole("button", { name: /^Repair SA-10/ }),
    );
    expect(
      await screen.findByText("This unit cannot be repaired now."),
    ).toBeInTheDocument();
  });

  it("offers nothing on an enemy site", async () => {
    renderScreen({
      [SHEET_PATH]: sheet({
        summary: { ...sheet().summary, blue: false },
        heading: { degrees: 90, can_adjust: false, to_conflict: 180 },
        can_buy: false,
        disband_value: 0,
        hidden_on_mfd: false,
      }),
    });
    await screen.findByRole("region", { name: "Units" });
    expect(screen.queryByRole("region", { name: "Forces" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Head to conflict" }),
    ).toBeNull();
    expect(screen.getByRole("switch", { name: "Hidden on MFD" })).toBeEnabled();
    // The sheet carries the owner's budget: the enemy's is not ours to see.
    expect(screen.queryByText(/Budget/)).not.toBeInTheDocument();
  });

  it("hides the site on the MFD", async () => {
    const { calls } = renderScreen({
      [SHEET_PATH]: sheet({ hidden_on_mfd: false }),
    });
    await userEvent.click(
      await screen.findByRole("switch", { name: "Hidden on MFD" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: `/tgos/${TGO_ID}/hidden-on-mfd`,
      body: { hidden: true },
    });
  });

  it("shows the buildings and income of a building site", async () => {
    renderScreen({
      [SHEET_PATH]: sheet({
        is_building_site: true,
        heading: undefined,
        can_buy: false,
        disband_value: 0,
        income: { per_building: 2, available: 6, receiving: 4 },
        units: [unit({ info_kind: undefined, info_name: undefined })],
      }),
    });
    const buildings = await screen.findByRole("region", { name: "Buildings" });
    expect(within(buildings).queryByRole("link")).toBeNull();
    expect(screen.getByRole("region", { name: "Finances" })).toHaveTextContent(
      "Receiving $4M of $6M per turn ($2M per building).",
    );
    expect(screen.queryByRole("region", { name: "Orientation" })).toBeNull();
  });

  it("turns the site to the conflict", async () => {
    const { calls } = renderScreen({ [SHEET_PATH]: sheet() });
    await userEvent.click(
      await screen.findByRole("button", { name: "Head to conflict" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: `/tgos/${TGO_ID}/heading`,
      body: { degrees: 180 },
    });
  });

  it("disbands after a confirmation", async () => {
    const { calls } = renderScreen({ [SHEET_PATH]: sheet() });
    await userEvent.click(
      await screen.findByRole("button", { name: "Disband · +$50M" }),
    );
    expect(calls).toHaveLength(0);
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Disband",
      }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "DELETE",
      path: `/tgos/${TGO_ID}/group`,
    });
  });

  it("links to the base and the unit sheet", async () => {
    const { router } = renderScreen({ [SHEET_PATH]: sheet() });
    const link = await screen.findByRole("link", { name: "SA-10 launcher" });
    await userEvent.click(link);
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(
        PATHS.unit("ground", "SA-10/launcher v2"),
      ),
    );
  });

  it("says when the site cannot be loaded", async () => {
    renderScreen({});
    expect(await screen.findByText("No campaign loaded.")).toBeInTheDocument();
  });
});

describe("buying a group", () => {
  const openDialog = async (answers = {}) => {
    const result = renderScreen(
      {
        [SHEET_PATH]: sheet(),
        [`/tgos/${TGO_ID}/purchase-options`]: OPTIONS,
      },
      answers,
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Buy / Replace" }),
    );
    await screen.findByRole("dialog");
    return result;
  };
  const quotes = (calls: { path: string; body: unknown }[]) =>
    calls.filter((call) => call.path.endsWith("/quote"));

  it("quotes the default layout and buys it", async () => {
    const { calls } = await openDialog({
      [`/tgos/${TGO_ID}/purchase`]: { status: 200, body: sheet() },
    });
    const quote = await screen.findByLabelText("Quote");
    expect(quote).toHaveTextContent(
      "New group $60M, current group worth $50M: you pay $10M",
    );
    const expected = {
      force_group: "SA-10",
      layout: "Battery",
      choices: [
        { slot: 0, unit_type: "launcher", amount: 2 },
        { slot: 1, unit_type: "tor", amount: 1 },
      ],
    };
    expect(quotes(calls)[0].body).toEqual(expected);

    await userEvent.click(screen.getByRole("button", { name: "Buy" }));

    await waitFor(() =>
      expect(calls.at(-1)).toMatchObject({
        path: `/tgos/${TGO_ID}/purchase`,
        body: expected,
      }),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("asks a new quote when the choice changes", async () => {
    const { calls } = await openDialog();
    await screen.findByLabelText("Quote");
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Unit type 1" }),
      "other",
    );
    await userEvent.click(screen.getByRole("switch", { name: "Include 2" }));
    await waitFor(() =>
      expect(quotes(calls).at(-1)?.body).toEqual({
        force_group: "SA-10",
        layout: "Battery",
        choices: [{ slot: 0, unit_type: "other", amount: 2 }],
      }),
    );
  });

  it("starts over when another force group is picked", async () => {
    const { calls } = await openDialog();
    await screen.findByLabelText("Quote");
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Armed forces group" }),
      "SA-2",
    );
    await waitFor(() =>
      expect(quotes(calls).at(-1)?.body).toEqual({
        force_group: "SA-2",
        layout: "Site",
        choices: [{ slot: 0, unit_type: "sa2", amount: 1 }],
      }),
    );
  });

  it("refuses what the server says cannot be paid", async () => {
    await openDialog({
      [`/tgos/${TGO_ID}/purchase/quote`]: {
        status: 200,
        body: { ...QUOTE, affordable: false },
      },
    });
    await screen.findByLabelText("Quote");
    expect(screen.getByRole("button", { name: "Buy" })).toBeDisabled();
  });

  it("shows why a purchase is not possible", async () => {
    await openDialog({
      [`/tgos/${TGO_ID}/purchase/quote`]: {
        status: 409,
        body: { detail: "Choose at least one unit." },
      },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Choose at least one unit.",
    );
    expect(screen.getByRole("button", { name: "Buy" })).toBeDisabled();
  });
});

describe("unit info sheet", () => {
  const INFO: UnitInfo = {
    kind: "aircraft",
    name: "F-16C/50 Falcon",
    display_name: "F-16C Falcon",
    manufacturer: "General Dynamics",
    country_of_origin: "USA",
    role: "Multirole",
    year_introduced: "1991",
    tasks: ["CAP", "SEAD"],
    unit_class: "Plane",
    purpose: "",
    description: "A fighter.",
  };

  it("shows the unit and goes back", async () => {
    const { router } = renderScreen(
      { "/unit-info": INFO },
      {},
      PATHS.unit("aircraft", "F-16C/50 Falcon"),
    );
    expect(await screen.findByText("A fighter.")).toBeInTheDocument();
    expect(screen.getByText("General Dynamics F-16C Falcon")).toBeVisible();
    expect(screen.getByText("CAP, SEAD")).toBeVisible();
    expect(screen.getByRole("img")).toHaveAttribute(
      "src",
      unitBannerUrl("aircraft", "F-16C/50 Falcon"),
    );
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
  });

  it("does not list tasks for a ground unit", async () => {
    renderScreen(
      { "/unit-info": { ...INFO, kind: "ground", tasks: [] } },
      {},
      PATHS.unit("ground", "Tor"),
    );
    await screen.findByText("A fighter.");
    expect(screen.queryByText("In-game tasks")).toBeNull();
  });

  it("encodes the names in the banner URL", () => {
    expect(unitBannerUrl("ground", "SA-10/launcher v2")).toContain(
      "unit-info/banner?kind=ground&name=SA-10%2Flauncher+v2",
    );
  });
});

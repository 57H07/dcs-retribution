import type { FinancesJs, IntelJs, StatsJs } from "../api/liberationApi";
import { setupStore } from "../app/store";
import { recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { ReportsScreen } from "./ReportsScreen";
import { formatMillions } from "./common";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const INTEL: IntelJs = {
  friendly: {
    aircraft: {
      total: 16,
      bases: [
        {
          id: "cp-1",
          name: "Incirlik",
          total: 16,
          units: [
            { name: "A-10C", count: 4 },
            { name: "F-16CM", count: 12 },
          ],
        },
      ],
    },
    ground: {
      total: 10,
      bases: [
        {
          id: "cp-1",
          name: "Incirlik",
          total: 8,
          units: [{ name: "M1A2 Abrams", count: 8 }],
        },
        {
          id: "cp-2",
          name: "FARP Alpha",
          total: 2,
          units: [{ name: "M2A2 Bradley", count: 2 }],
        },
      ],
    },
  },
  enemy: {
    aircraft: {
      total: 8,
      bases: [
        {
          id: "cp-3",
          name: "Hama",
          total: 8,
          units: [{ name: "MiG-29S", count: 8 }],
        },
      ],
    },
    ground: { total: 0, bases: [] },
  },
};

const STATS: StatsJs = {
  turns: [
    {
      turn: 0,
      friendly_aircraft: 20,
      enemy_aircraft: 12,
      friendly_vehicles: 10,
      enemy_vehicles: 14,
    },
    {
      turn: 1,
      friendly_aircraft: 16,
      enemy_aircraft: 8,
      friendly_vehicles: 8,
      enemy_vehicles: 10,
    },
  ],
};

const FINANCES: FinancesJs = {
  friendly: {
    budget: 812.5,
    multiplier: 1.5,
    from_bases: 25,
    from_buildings: 26,
    total: 76.5,
    bases: [
      { id: "cp-1", name: "Incirlik", income: 20 },
      { id: "cp-2", name: "FARP Alpha", income: 5 },
    ],
    buildings: [
      {
        name: "Oil field",
        category: "oil",
        count: 2,
        income_per_building: 10,
        income: 20,
      },
      {
        name: "Ammo depot",
        category: "ammo",
        count: 3,
        income_per_building: 2,
        income: 6,
      },
    ],
  },
  enemy: {
    budget: 300,
    multiplier: 1,
    from_bases: 10,
    from_buildings: 1,
    total: 11,
    bases: [{ id: "cp-3", name: "Hama", income: 10 }],
    buildings: [],
  },
};

const GETS = {
  "/reports/intel": INTEL,
  "/reports/stats": STATS,
  "/reports/finances": FINANCES,
};

function renderReports(
  path = "/reports",
  gets: Record<string, unknown> = GETS,
) {
  const calls = recordFetch(204, undefined, gets);
  const router = createMemoryRouter(
    [
      { path: "/reports", element: <ReportsScreen /> },
      { path: "/reports/:tab", element: <ReportsScreen /> },
      { path: "/", element: <p>Command view</p> },
    ],
    { initialEntries: [path] },
  );
  render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </Provider>,
  );
  return { router, calls };
}

describe("reports screen", () => {
  it("opens on the Intel tab and switches tabs through the URL", async () => {
    const { router, calls } = renderReports();
    expect(screen.getByRole("tab", { name: "Intel" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await userEvent.click(screen.getByRole("tab", { name: "Finances" }));
    expect(router.state.location.pathname).toBe("/reports/finances");
    expect(
      await screen.findByRole("table", { name: "Income by base" }),
    ).toBeInTheDocument();
    // Reads only: nothing is sent to Qt or changed.
    expect(calls).toHaveLength(0);
  });

  it("goes back to the command view", async () => {
    const { router } = renderReports();
    await userEvent.click(screen.getByRole("link", { name: /Command view/ }));
    expect(router.state.location.pathname).toBe("/");
  });

  it("says when no campaign is loaded", async () => {
    renderReports("/reports/stats", {});
    expect(await screen.findByText("No campaign loaded.")).toBeVisible();
  });
});

describe("Intel tab", () => {
  it("lists units by base and type, with totals", async () => {
    renderReports("/reports/intel");
    const air = await screen.findByRole("region", { name: "Air forces" });
    expect(within(air).getByRole("heading")).toHaveTextContent("Air forces 16");
    const incirlik = within(air).getByRole("table", { name: "Incirlik (16)" });
    const rows = within(incirlik).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual(["A-10C4", "F-16CM12"]);

    const ground = screen.getByRole("region", { name: "Ground forces" });
    expect(
      within(ground)
        .getAllByRole("table")
        .map((t) => t.querySelector("caption")?.textContent),
    ).toEqual(["Incirlik (8)", "FARP Alpha (2)"]);
  });

  it("shows the enemy forces with Enemy info", async () => {
    renderReports("/reports/intel");
    await screen.findByRole("region", { name: "Air forces" });
    await userEvent.click(screen.getByRole("switch", { name: "Enemy info" }));
    expect(screen.getByRole("table", { name: "Hama (8)" })).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Ground forces" })).getByText(
        "No ground units.",
      ),
    ).toBeVisible();
  });
});

describe("Stats tab", () => {
  it("shows the last turn, one chart per force and the turns table", async () => {
    renderReports("/reports/stats");
    expect(
      await screen.findByRole("img", {
        name: /Aircraft forces over time: Allied aircraft count 16, Enemy aircraft count 8/,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /Combat vehicles over time/ }),
    ).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Forces per turn" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual(["020121014", "1168810"]);
  });

  it("says when no turn is recorded", async () => {
    renderReports("/reports/stats", { "/reports/stats": { turns: [] } });
    expect(await screen.findByText("No turn recorded yet.")).toBeVisible();
  });
});

describe("Finances tab", () => {
  it("shows the balance, the income and its breakdown", async () => {
    renderReports("/reports/finances");
    const bases = await screen.findByRole("table", { name: "Income by base" });
    expect(
      within(bases)
        .getAllByRole("row")
        .slice(1)
        .map((r) => r.textContent),
    ).toEqual(["Incirlik20.0M", "FARP Alpha5.0M"]);
    const buildings = screen.getByRole("table", { name: "Income by building" });
    expect(
      within(buildings)
        .getAllByRole("row")
        .slice(1)
        .map((r) => r.textContent),
    ).toEqual(["Oil fieldOIL2 × 10.0M20.0M", "Ammo depotAMMO3 × 2.0M6.0M"]);
    expect(screen.getByText("812.5M")).toBeVisible();
    expect(screen.getByText("76.5M")).toBeVisible();
    expect(screen.getByText("Income multiplier: 1.5")).toBeVisible();
  });

  it("shows the enemy economy with Enemy info", async () => {
    renderReports("/reports/finances");
    await screen.findByRole("table", { name: "Income by base" });
    await userEvent.click(screen.getByRole("switch", { name: "Enemy info" }));
    expect(screen.getByText("300.0M")).toBeVisible();
    expect(screen.getByText("No building produces income.")).toBeVisible();
  });

  it("formats millions with one decimal", () => {
    expect(formatMillions(812.5)).toBe("812.5M");
    expect(formatMillions(0)).toBe("0.0M");
  });
});

import type { Base } from "../api/liberationApi";
import { setupStore } from "../app/store";
import { Answer, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { BaseScreen, repairTerms } from "./BaseScreen";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const BASE: Base = {
  summary: {
    id: "cp-1",
    name: "Krymsk",
    blue: true,
    sidc: "10031000001213000000",
    category: "Airfield",
    distance_to_front_nm: 12,
    runway: { state: "damaged" },
    parking: { current: 18, total: 25 },
    ammo_depots: { current: 1, total: 1 },
    fuel_depots: { current: 0, total: 1 },
    can_buy_aircraft: true,
    can_buy_ground_units: true,
    can_repair_runway: true,
    can_afford_runway_repair: true,
    runway_repair_cost: 100,
  },
  budget: 1240,
  tabs: [
    { id: "airfield", label: "Airfield command" },
    { id: "ground-forces", label: "Ground forces HQ" },
  ],
  air_defenses: [
    {
      id: "tgo-1",
      name: "SA-15 Krymsk",
      category: "SHORAD",
      units: { current: 1, total: 2 },
      operational: true,
    },
  ],
  repairs: [
    {
      id: "runway",
      kind: "runway",
      label: "Runway",
      cost: 100,
      turns: 4,
      in_progress: false,
      affordable: true,
    },
    {
      id: "squadron:sq-1",
      kind: "aircraft",
      label: "2 damaged MiG-29s (40th TAB)",
      cost: 2000,
      turns: 0,
      in_progress: false,
      affordable: false,
    },
    {
      id: "tgo:tgo-2:repairing",
      kind: "buildings",
      label: "Ammo depot: 1 building",
      cost: 0,
      turns: 2,
      in_progress: true,
      affordable: false,
    },
  ],
  repair_all_cost: 2100,
  repair_all_affordable: false,
  intel: [
    { title: "CAP", units: [{ name: "MiG-29", count: 10 }] },
    { title: "Front line units", units: [] },
  ],
};

const ENEMY: Base = {
  ...BASE,
  summary: { ...BASE.summary, id: "cp-9", name: "Maykop", blue: false },
  tabs: [
    { id: "intel", label: "Intel" },
    { id: "convoys", label: "Departing convoys" },
  ],
  repairs: [],
  air_defenses: [],
};

function renderBase(
  path = "/bases/cp-1",
  answers: Record<string, Answer> = {},
) {
  const calls = recordFetch(
    200,
    BASE,
    {
      "/control-points/cp-1/base": BASE,
      "/control-points/cp-9/base": ENEMY,
    },
    answers,
  );
  const router = createMemoryRouter(
    [
      { path: "/bases/:id", element: <BaseScreen /> },
      { path: "/bases/:id/:tab", element: <BaseScreen /> },
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

describe("base screen", () => {
  it("shows the base, its budget and the tabs the server sends", async () => {
    const { router, calls } = renderBase();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Krymsk" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Airfield · 12 nm from front")).toBeVisible();
    expect(screen.getByText("$1240M")).toBeVisible();
    const tabs = screen.getAllByRole("tab").map((t) => t.textContent);
    expect(tabs).toEqual(["Airfield command", "Ground forces HQ"]);
    expect(
      screen.getByRole("tab", { name: "Airfield command" }),
    ).toHaveAttribute("aria-selected", "true");

    await userEvent.click(
      screen.getByRole("tab", { name: "Ground forces HQ" }),
    );
    expect(router.state.location.pathname).toBe("/bases/cp-1/ground-forces");
    expect(calls).toHaveLength(0);
  });

  it("opens an enemy base on its Intel tab, without repairs", async () => {
    renderBase("/bases/cp-9/airfield");
    expect(await screen.findByRole("tab", { name: "Intel" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.queryByRole("region", { name: "Repairs" })).toBeNull();
    expect(screen.getByRole("table", { name: "CAP" })).toHaveTextContent(
      "MiG-2910",
    );
    expect(screen.getByText("No air defense site at this base.")).toBeVisible();
  });

  it("shows the base status and air defense", async () => {
    renderBase();
    const status = await screen.findByRole("region", { name: "Base status" });
    expect(within(status).getByText("Runway")).toBeVisible();
    expect(within(status).getByText("Damaged")).toBeVisible();
    expect(within(status).getByText("18/25")).toBeVisible();
    const airDefense = screen.getByRole("region", { name: "Air defense" });
    expect(airDefense).toHaveTextContent("SA-15 Krymsk · SHORAD1/2");
  });

  it("hands purchases over to the Qt base menu for now", async () => {
    const { calls } = renderBase();
    await userEvent.click(
      await screen.findByRole("button", { name: "Open the base menu" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/qt/info/control-point/cp-1",
    });
  });
});

describe("repairs", () => {
  it("lists repairs with cost and delay, and repairs underway", async () => {
    renderBase();
    const repairs = await screen.findByRole("region", { name: "Repairs" });
    expect(repairs).toHaveTextContent("Runway$100M · 4 turns");
    expect(repairs).toHaveTextContent("$2000M · at once");
    expect(repairs).toHaveTextContent(
      "Ammo depot: 1 buildingRepairing · 2 turns left",
    );
    expect(
      within(repairs).getByRole("button", {
        name: "Repair 2 damaged MiG-29s (40th TAB)",
      }),
    ).toBeDisabled();
    expect(
      within(repairs).queryByRole("button", {
        name: "Repair Ammo depot: 1 building",
      }),
    ).toBeNull();
    expect(
      within(repairs).getByRole("button", { name: "Repair all · $2100M" }),
    ).toBeDisabled();
  });

  it("orders a repair and confirms it", async () => {
    const { calls } = renderBase();
    await userEvent.click(
      await screen.findByRole("button", { name: "Repair Runway" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/control-points/cp-1/repairs/runway",
    });
    expect(await screen.findByText("Repair ordered: Runway")).toBeVisible();
  });

  it("shows the server refusal as a toast", async () => {
    renderBase("/bases/cp-1", {
      "/control-points/cp-1/repairs/runway": {
        status: 409,
        body: {
          detail:
            "Repairing Runway costs $100M but you have only $40M available.",
        },
      },
    });
    await userEvent.click(
      await screen.findByRole("button", { name: "Repair Runway" }),
    );
    expect(await screen.findByText("Repair refused")).toBeVisible();
    expect(
      screen.getByText(
        "Repairing Runway costs $100M but you have only $40M available.",
      ),
    ).toBeVisible();
  });
});

describe("repairTerms", () => {
  it("words aircraft maintenance that cannot be paid for", () => {
    expect(
      repairTerms({
        id: "squadron:1",
        kind: "aircraft",
        label: "1 damaged F-16",
        cost: 0,
        turns: 1,
        in_progress: true,
        affordable: false,
      }),
    ).toBe("In maintenance · 1 turn left");
  });
});

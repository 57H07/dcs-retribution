import { ControlPointSummary, TgoSummary } from "../../api/liberationApi";
import { setupStore } from "../../app/store";
import { MapSelection } from "../../maplayers/mapSelection";
import { recordFetch, restoreFetch } from "../../shell/testing";
import { MapInspector, distanceText } from "./MapInspector";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const CP_ID = "cp-1";
const TGO_ID = "tgo-1";

function base(
  overrides: Partial<ControlPointSummary> = {},
): ControlPointSummary {
  return {
    id: CP_ID,
    name: "Krymsk",
    blue: true,
    sidc: "10031000001213000000",
    category: "Airfield",
    distance_to_front_nm: 12.3,
    runway: { state: "operational" },
    parking: { current: 18, total: 25 },
    ground_units: { current: 30, total: 24 },
    ammo_depots: { current: 2, total: 3 },
    fuel_depots: { current: 0, total: 0 },
    can_buy_aircraft: true,
    can_buy_ground_units: true,
    can_repair_runway: false,
    can_afford_runway_repair: true,
    runway_repair_cost: 100,
    ...overrides,
  };
}

function site(overrides: Partial<TgoSummary> = {}): TgoSummary {
  return {
    id: TGO_ID,
    name: "SA-10 Krasnodar",
    blue: false,
    sidc: "10061500001301000000",
    category: "LORAD",
    control_point_id: "cp-2",
    control_point_name: "Krasnodar",
    distance_to_front_nm: 30,
    units: { current: 5, total: 8 },
    dead: false,
    ...overrides,
  };
}

function renderInspector(selection: MapSelection | null, onClose = vi.fn()) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <MapInspector selection={selection} onClose={onClose} />,
      },
      { path: "/bases/:id", element: <p>Base screen</p> },
    ],
    { initialEntries: ["/"] },
  );
  render(
    <Provider store={setupStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
  return { router, onClose };
}

function card() {
  return screen.getByRole("region", { name: /^Inspector/ });
}

describe("map inspector", () => {
  it("shows nothing while nothing is selected", () => {
    recordFetch();
    renderInspector(null);
    expect(screen.queryByRole("region")).toBeNull();
  });

  it("says it is loading the selection", () => {
    recordFetch();
    renderInspector({ kind: "controlPoint", id: CP_ID });
    expect(screen.getByRole("status")).toHaveTextContent("Loading the base");
  });

  it("shows a friendly base with its gauges and actions", async () => {
    recordFetch(204, undefined, {
      [`/control-points/${CP_ID}/summary`]: base(),
    });
    const { router } = renderInspector({ kind: "controlPoint", id: CP_ID });
    expect(await screen.findByText("Krymsk")).toBeInTheDocument();
    expect(card()).toHaveTextContent("Airfield · 12 nm from front");
    expect(
      screen.getByRole("img", { name: "Friendly Airfield" }),
    ).toHaveAttribute("data-sidc", "10031000001213000000");
    expect(
      screen.getByRole("progressbar", { name: "Runway" }),
    ).toBeInTheDocument();
    expect(card()).toHaveTextContent("OK");
    expect(card()).toHaveTextContent("18/25");
    expect(card()).toHaveTextContent("2/3");
    // No fuel depot at this base: no gauge.
    expect(
      screen.queryByRole("progressbar", { name: "Fuel depots" }),
    ).toBeNull();
    // Runway intact: nothing to repair.
    expect(screen.queryByRole("button", { name: /Repair/ })).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Buy aircraft" }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/bases/${CP_ID}`),
    );
  });

  it("offers the runway repair, disabled when unaffordable", async () => {
    recordFetch(204, undefined, {
      [`/control-points/${CP_ID}/summary`]: base({
        runway: { state: "damaged" },
        can_repair_runway: true,
        can_afford_runway_repair: false,
      }),
    });
    renderInspector({ kind: "controlPoint", id: CP_ID });
    const repair = await screen.findByRole("button", { name: "Repair $100M" });
    expect(repair).toBeDisabled();
    expect(card()).toHaveTextContent("Damaged");
  });

  it("only shows intel for an enemy base", async () => {
    recordFetch(204, undefined, {
      [`/control-points/${CP_ID}/summary`]: base({
        blue: false,
        can_buy_aircraft: false,
        can_buy_ground_units: false,
      }),
    });
    renderInspector({ kind: "controlPoint", id: CP_ID });
    expect(await screen.findByRole("button", { name: "Intel" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Buy aircraft" })).toBeNull();
  });

  it("says when the base cannot be loaded", async () => {
    recordFetch();
    renderInspector({ kind: "controlPoint", id: CP_ID });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load this base.",
    );
  });

  it("shows a ground object and opens its Qt details", async () => {
    const calls = recordFetch(204, undefined, {
      [`/tgos/${TGO_ID}/summary`]: site(),
    });
    const { router } = renderInspector({ kind: "tgo", id: TGO_ID });
    expect(await screen.findByText("SA-10 Krasnodar")).toBeInTheDocument();
    expect(card()).toHaveTextContent("LORAD · Krasnodar · 30 nm from front");
    expect(card()).toHaveTextContent("5/8");

    await userEvent.click(screen.getByRole("button", { name: "Details" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe(`/qt/info/tgo/${TGO_ID}`);

    await userEvent.click(screen.getByRole("button", { name: "Krasnodar" }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/bases/cp-2"),
    );
  });

  it("closes", async () => {
    recordFetch(204, undefined, { [`/tgos/${TGO_ID}/summary`]: site() });
    const { onClose } = renderInspector({ kind: "tgo", id: TGO_ID });
    await screen.findByText("SA-10 Krasnodar");
    await userEvent.click(
      within(card()).getByRole("button", { name: "Close inspector" }),
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("formats the distance to the front", () => {
    expect(distanceText(12.6)).toBe("13 nm from front");
    expect(distanceText(null)).toBeNull();
    expect(distanceText(undefined)).toBeNull();
  });
});

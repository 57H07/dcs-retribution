import type {
  BaseActions,
  DepartingConvoy,
  GroundForces,
  TransferOptions,
} from "../api/liberationApi";
import { setupStore } from "../app/store";
import { Answer, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { BaseScreen } from "./BaseScreen";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

function base(blue = true) {
  return {
    summary: {
      id: "cp-1",
      name: "Krymsk",
      blue,
      sidc: "10031000001213000000",
      category: "Airfield",
      distance_to_front_nm: 12,
      runway: { state: "operational" },
      parking: { current: 18, total: 25 },
      ammo_depots: { current: 1, total: 1 },
      fuel_depots: { current: 1, total: 1 },
      can_buy_aircraft: true,
      can_buy_ground_units: true,
      can_repair_runway: false,
      can_afford_runway_repair: true,
      runway_repair_cost: 100,
    },
    budget: 100,
    tabs: blue
      ? [
          { id: "ground-forces", label: "Ground forces HQ" },
          { id: "airfield", label: "Airfield command" },
        ]
      : [
          { id: "intel", label: "Intel" },
          { id: "convoys", label: "Departing convoys" },
        ],
    air_defenses: [],
    repairs: [],
    repair_all_cost: 0,
    repair_all_affordable: false,
    intel: [],
    airfield: {
      squadrons: [],
      parking_after_delivery: { current: 0, total: 0 },
      incoming: [],
    },
  };
}

const FORCES: GroundForces = {
  units: [
    {
      unit_id: "t72",
      name: "T-72",
      unit_cost: 20,
      owned: 4,
      pending: 2,
      max_add: 1,
    },
    {
      unit_id: "bmp",
      name: "BMP-2",
      unit_cost: 10,
      owned: 0,
      pending: 0,
      max_add: 10,
    },
  ],
  has_factory: false,
  present: 4,
  ordered: 2,
  transferring: 3,
  deployable_limit: 12,
  reserve: 0,
  front_lines: [
    { enemy_id: "cp-9", enemy: "Maykop", stance: "DEFENSIVE" },
  ],
  stance_options: ["DEFENSIVE", "AGGRESSIVE"],
  front_line_cheats: false,
};

const NO_ACTIONS: BaseActions = {
  can_transfer: false,
  can_plan_transport: false,
  can_attack_airfield: false,
};

const ORDER_PATH = "/control-points/cp-1/purchases/ground-units";

function renderBase(
  options: {
    path?: string;
    blue?: boolean;
    forces?: GroundForces;
    actions?: BaseActions;
    convoys?: DepartingConvoy[];
    transferOptions?: TransferOptions;
    answers?: Record<string, Answer>;
  } = {},
) {
  const calls = recordFetch(
    204,
    undefined,
    {
      "/control-points/cp-1/base": base(options.blue ?? true),
      "/control-points/cp-1/ground-forces": options.forces ?? FORCES,
      "/control-points/cp-1/actions": options.actions ?? NO_ACTIONS,
      "/control-points/cp-1/convoys": options.convoys ?? [],
      "/control-points/cp-1/transfer-options": options.transferOptions ?? null,
    },
    options.answers ?? {},
  );
  const router = createMemoryRouter(
    [
      { path: "/bases/:id/:tab", element: <BaseScreen /> },
      { path: "/packages/:id", element: <p>Package editor</p> },
    ],
    { initialEntries: [options.path ?? "/bases/cp-1/ground-forces"] },
  );
  render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </Provider>,
  );
  return calls;
}

const add = (unit: string) =>
  screen.findByRole("button", { name: `Add one ${unit}` });
const remove = (unit: string) =>
  screen.findByRole("button", { name: `Remove one ${unit}` });

describe("ground unit orders", () => {
  it("shows the units with cost, owned and pending deliveries", async () => {
    renderBase();
    const row = (await screen.findByText("T-72")).closest("tr")!;
    expect(row).toHaveTextContent("$20M");
    expect(row).toHaveTextContent("4");
    expect(row).toHaveTextContent("+2");
    const forces = screen.getByRole("region", { name: "Forces at this base" });
    expect(forces).toHaveTextContent("On their way here3");
    expect(forces).toHaveTextContent("Deployable at the front12");
    expect(forces).toHaveTextContent("FactoryNo");
  });

  it("stays within the limits the server sends for the row", async () => {
    renderBase();
    const plus = await add("T-72");
    await userEvent.click(plus);
    expect(plus).toBeDisabled();
    // Two pending orders can be cancelled, and nothing can be sold.
    const minus = await remove("T-72");
    await userEvent.click(minus);
    await userEvent.click(minus);
    await userEvent.click(minus);
    expect(minus).toBeDisabled();
    expect(await remove("BMP-2")).toBeDisabled();
  });

  it("confirms the whole draft with its summary", async () => {
    const calls = renderBase();
    await userEvent.click(await add("BMP-2"));
    await userEvent.click(await add("BMP-2"));
    const summary = screen.getByRole("complementary", {
      name: "Order summary",
    });
    expect(summary).toHaveTextContent("2 × BMP-2$20M");
    expect(summary).toHaveTextContent("Budget after order$80M");

    await userEvent.click(
      within(summary).getByRole("button", { name: "Confirm order" }),
    );

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: ORDER_PATH,
      body: { orders: [{ unit_id: "bmp", quantity: 2 }] },
    });
    expect(await screen.findByText("Order confirmed")).toBeVisible();
    expect(summary).toHaveTextContent("Use − and +");
  });

  it("shows the refusal of the server and keeps the draft", async () => {
    renderBase({
      answers: {
        [ORDER_PATH]: {
          status: 409,
          body: { detail: "You need a factory." },
        },
      },
    });
    await userEvent.click(await add("BMP-2"));
    await userEvent.click(screen.getByRole("button", { name: "Confirm order" }));
    expect(await screen.findByText("You need a factory.")).toBeVisible();
    expect(screen.getByLabelText("Order for BMP-2")).toHaveTextContent("+1");
  });

  it("cancels a pending order with a negative line", async () => {
    const calls = renderBase();
    await userEvent.click(
      await screen.findByRole("button", {
        name: "Cancel pending order of T-72",
      }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toEqual({
      orders: [{ unit_id: "t72", quantity: -2 }],
    });
  });

  it("explains why nothing can be ordered", async () => {
    renderBase({
      forces: {
        ...FORCES,
        recruitment_refusal: "None of your bases can recruit ground units.",
      },
    });
    expect(
      await screen.findByText("None of your bases can recruit ground units."),
    ).toBeVisible();
  });
});

describe("front lines", () => {
  it("sets a stance", async () => {
    const calls = renderBase();
    const stance = await screen.findByLabelText("Against Maykop");
    expect(stance).toHaveValue("DEFENSIVE");
    await userEvent.selectOptions(stance, "AGGRESSIVE");
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: "/control-points/cp-1/front-lines/cp-9/stance",
      body: { stance: "AGGRESSIVE" },
    });
  });

  it("offers the cheats only when the server does", async () => {
    renderBase();
    await screen.findByLabelText("Against Maykop");
    expect(screen.queryByRole("button", { name: /Cheat/ })).toBeNull();
  });

  it("moves the front line with the cheat on", async () => {
    const calls = renderBase({
      forces: { ...FORCES, front_line_cheats: true },
    });
    await userEvent.click(
      await screen.findByRole("button", {
        name: "Cheat: retreat against Maykop",
      }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      path: "/control-points/cp-1/front-lines/cp-9/cheat",
      body: { advance: false },
    });
  });
});

describe("departing convoys", () => {
  const CONVOY: DepartingConvoy = {
    name: "Convoy 12",
    kind: "cargo-ship",
    destination_id: "cp-2",
    destination: "Sochi",
    size: 3,
    units: [{ name: "T-72", count: 3 }],
  };

  it("lists the convoys and attacks one", async () => {
    const calls = renderBase({
      path: "/bases/cp-1/convoys",
      blue: false,
      convoys: [CONVOY],
      answers: {
        "/control-points/cp-1/convoys/cp-2/package": {
          status: 201,
          body: { id: "pkg-9" },
        },
      },
    });
    const card = await screen.findByRole("listitem", {
      name: "Convoy 12 to Sochi",
    });
    expect(card).toHaveTextContent("3 × T-72");
    await userEvent.click(within(card).getByRole("button", { name: "Attack" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/control-points/cp-1/convoys/cp-2/package",
    });
    expect(await screen.findByText("Package editor")).toBeInTheDocument();
  });

  it("says when no convoy leaves", async () => {
    renderBase({ path: "/bases/cp-1/convoys", blue: false });
    expect(
      await screen.findByText("No convoy is leaving this base."),
    ).toBeVisible();
  });
});

describe("transfers", () => {
  const OPTIONS: TransferOptions = {
    destinations: [
      { id: "cp-2", name: "Sochi" },
      { id: "cp-3", name: "Anapa" },
    ],
    destination_id: "cp-2",
    units: [{ unit_id: "t72", name: "T-72", available: 2 }],
    squadrons: [{ id: "sq-1", label: "Hueys", capacity: 2 }],
  };
  const ACTIONS: BaseActions = {
    ...NO_ACTIONS,
    can_transfer: true,
    can_plan_transport: true,
  };

  it("sends units by convoy, within what the base has", async () => {
    const calls = renderBase({
      actions: ACTIONS,
      transferOptions: OPTIONS,
    });
    await userEvent.click(
      await screen.findByRole("button", { name: "Transfer units" }),
    );
    const submit = await screen.findByRole("button", {
      name: "Create transfer order",
    });
    expect(submit).toBeDisabled();
    const more = screen.getByRole("button", { name: "Send one more T-72" });
    await userEvent.click(more);
    await userEvent.click(more);
    expect(more).toBeDisabled();

    await userEvent.click(submit);

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/transfers/",
      body: {
        origin_id: "cp-1",
        destination_id: "cp-2",
        units: [{ unit_id: "t72", count: 2 }],
        airlift: false,
        squadron_id: null,
      },
    });
  });

  it("starts a Transport mission on the first squadron", async () => {
    const calls = renderBase({
      actions: ACTIONS,
      transferOptions: OPTIONS,
    });
    await userEvent.click(
      await screen.findByRole("button", { name: "Transport mission" }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Send one more T-72" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Create Transport mission" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toMatchObject({
      airlift: true,
      squadron_id: "sq-1",
    });
  });

  it("shows why no squadron can fly and the refusal of the server", async () => {
    renderBase({
      actions: ACTIONS,
      transferOptions: {
        ...OPTIONS,
        squadrons: [],
        no_squadron_warning: "No Transport-capable squadron.",
      },
      answers: {
        "/transfers/": { status: 409, body: { detail: "No route." } },
      },
    });
    await userEvent.click(
      await screen.findByRole("button", { name: "Transport mission" }),
    );
    expect(
      await screen.findByText("No Transport-capable squadron."),
    ).toBeVisible();
    await userEvent.click(
      screen.getByRole("button", { name: "Send one more T-72" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Create transfer order" }),
    );
    expect(await screen.findByText("No route.")).toBeVisible();
  });
});

describe("base actions", () => {
  it("offers only what the server says", async () => {
    renderBase();
    await screen.findByText("T-72");
    expect(screen.queryByRole("region", { name: "Base actions" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Radios" })).toBeNull();
  });

  it("plans an attack and runs the cheats", async () => {
    const calls = renderBase({
      actions: {
        ...NO_ACTIONS,
        can_attack_airfield: true,
        cheat_capture: "Capture",
        cheat_runway: "Destroy runway",
      },
    });
    await userEvent.click(
      await screen.findByRole("button", { name: "Attack airfield" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Cheat: Destroy runway" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Cheat: Capture" }),
    );
    await waitFor(() => expect(calls).toHaveLength(3));
    expect(calls[0]).toMatchObject({
      path: "/packages/",
      body: { target_kind: "control-point", target_id: "cp-1" },
    });
    expect(calls[1].path).toBe("/control-points/cp-1/cheat/runway");
    expect(calls[2].path).toBe("/control-points/cp-1/cheat/capture");
  });

  it("edits the radios of the base", async () => {
    const calls = renderBase({
      actions: {
        ...NO_ACTIONS,
        radios: {
          has_frequency: true,
          has_tacan: true,
          has_icls: false,
          has_link4: false,
          tacan_channel: 74,
          tacan_band: "X",
          tacan_callsign: "STA",
          warnings: ["TACAN 74X is already in use."],
        },
      },
    });
    const panel = await screen.findByRole("region", { name: "Radios" });
    expect(panel).toHaveTextContent("FrequencyAuto");
    expect(panel).toHaveTextContent("TACAN74X (STA)");
    expect(panel).toHaveTextContent("TACAN 74X is already in use.");
    expect(panel).not.toHaveTextContent("ICLS");

    await userEvent.click(
      within(panel).getByRole("button", { name: "Set radios" }),
    );
    await userEvent.type(
      await screen.findByLabelText("Frequency (MHz)"),
      "251.25",
    );
    await userEvent.clear(screen.getByLabelText("TACAN channel"));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: "/control-points/cp-1/radios",
      body: {
        frequency_mhz: 251.25,
        tacan_channel: null,
        tacan_band: null,
        tacan_callsign: "STA",
      },
    });
  });
});

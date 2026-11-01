import type { Base, SquadronChoice } from "../api/liberationApi";
import { setupStore } from "../app/store";
import { Answer, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { BaseScreen } from "./BaseScreen";
import { money } from "./money";
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
  tabs: [{ id: "airfield", label: "Airfield command" }],
  air_defenses: [],
  repairs: [],
  repair_all_cost: 0,
  repair_all_affordable: false,
  intel: [],
  airfield: {
    squadrons: [
      {
        squadron_id: "sq-mig",
        squadron: "40th TAB",
        aircraft: "MiG-29",
        unit_cost: 28,
        owned: 10,
        max_aircraft: 12,
        pending: 0,
        max_add: 2,
        max_remove: 3,
      },
      {
        squadron_id: "sq-su",
        squadron: "299th TAB",
        aircraft: "Su-25T",
        unit_cost: 18,
        owned: 8,
        pending: 2,
        max_add: 5,
        max_remove: 2,
      },
    ],
    parking_after_delivery: { current: 20, total: 25 },
    incoming: [
      { squadron: "16th AAB", aircraft: "Mi-24P", owned: 4, origin: "Sochi" },
    ],
  },
};

const CHOICES: SquadronChoice[] = [
  {
    aircraft: "MiG-29S",
    display_name: "MiG-29S",
    tasks: ["BARCAP", "TARCAP"],
    presets: [],
  },
  {
    aircraft: "Su-25T",
    display_name: "Su-25T",
    tasks: ["CAS"],
    presets: [{ name: "Grach", label: "Grach (Rooks)" }],
  },
];

const ORDER_PATH = "/control-points/cp-1/purchases/aircraft";

function renderTab(answers: Record<string, Answer> = {}) {
  const calls = recordFetch(
    200,
    BASE,
    {
      "/control-points/cp-1/base": BASE,
      "/control-points/cp-1/squadron-choices": CHOICES,
    },
    answers,
  );
  const router = createMemoryRouter(
    [{ path: "/bases/:id/:tab", element: <BaseScreen /> }],
    { initialEntries: ["/bases/cp-1/airfield"] },
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

const add = (squadron: string) =>
  screen.findByRole("button", { name: `Add one to ${squadron}` });
const remove = (squadron: string) =>
  screen.findByRole("button", { name: `Remove one from ${squadron}` });
const summary = () =>
  screen.findByRole("complementary", { name: "Order summary" });

describe("money", () => {
  it("shows refunds as negative", () => {
    expect(money(2.5)).toBe("$2.5M");
    expect(money(-18)).toBe("-$18M");
  });
});

describe("order rows", () => {
  it("shows each squadron with cost, owned/max and pending deliveries", async () => {
    renderTab();
    const row = (await screen.findByText("40th TAB")).closest("tr")!;
    expect(row).toHaveTextContent("MiG-29");
    expect(row).toHaveTextContent("$28M");
    expect(row).toHaveTextContent("10 / 12");
    const other = screen.getByText("299th TAB").closest("tr")!;
    expect(other).toHaveTextContent("+2");
    // No squadron limit: no maximum.
    expect(other).not.toHaveTextContent("8 /");
    expect(
      screen.getByRole("region", { name: "Transferring here" }),
    ).toHaveTextContent("16th AAB (Mi-24P) · 4 aircraft from Sochi");
  });

  it("stays within the limits the server sends for the row", async () => {
    renderTab();
    const plus = await add("40th TAB");
    await userEvent.click(plus);
    await userEvent.click(plus);
    expect(plus).toBeDisabled();
    const minus = await remove("299th TAB");
    await userEvent.click(minus);
    await userEvent.click(minus);
    expect(minus).toBeDisabled();
  });
});

describe("order summary", () => {
  it("totals the order, the budget left and the parking after delivery", async () => {
    renderTab();
    await userEvent.click(await add("40th TAB"));
    await userEvent.click(await add("40th TAB"));
    await userEvent.click(await remove("299th TAB"));
    const panel = await summary();
    expect(panel).toHaveTextContent("2 × MiG-29$56M");
    expect(panel).toHaveTextContent("-1 × Su-25T-$18M");
    expect(panel).toHaveTextContent("Total$38M");
    expect(panel).toHaveTextContent("Budget after order$62M");
    expect(panel).toHaveTextContent("Parking after delivery21 / 25");
  });

  it("has nothing to confirm without an order", async () => {
    renderTab();
    const panel = await summary();
    expect(
      within(panel).getByRole("button", { name: "Confirm order" }),
    ).toBeDisabled();
  });
});

describe("confirm", () => {
  it("sends the whole order, then clears it", async () => {
    const calls = renderTab();
    await userEvent.click(await add("40th TAB"));
    await userEvent.click(await remove("299th TAB"));
    await userEvent.click(
      within(await summary()).getByRole("button", { name: "Confirm order" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: ORDER_PATH,
      body: {
        orders: [
          { squadron_id: "sq-mig", quantity: 1 },
          { squadron_id: "sq-su", quantity: -1 },
        ],
      },
    });
    expect(await screen.findByText("Order confirmed")).toBeInTheDocument();
    expect(await summary()).toHaveTextContent("Total$0M");
  });

  it("shows the refusal of the server and keeps the order", async () => {
    renderTab({
      [ORDER_PATH]: {
        status: 409,
        body: { detail: "No parking left for a MiG-29 at Krymsk." },
      },
    });
    await userEvent.click(await add("40th TAB"));
    await userEvent.click(
      within(await summary()).getByRole("button", { name: "Confirm order" }),
    );
    expect(await screen.findByText("Order refused")).toBeInTheDocument();
    expect(
      screen.getByText("No parking left for a MiG-29 at Krymsk."),
    ).toBeInTheDocument();
    expect(await summary()).toHaveTextContent("1 × MiG-29$28M");
  });
});

describe("cancel pending orders", () => {
  it("cancels at once, only where something is pending", async () => {
    const calls = renderTab();
    await screen.findByText("40th TAB");
    expect(
      screen.queryByRole("button", {
        name: "Cancel pending order of 40th TAB",
      }),
    ).toBeNull();
    await userEvent.click(
      screen.getByRole("button", { name: "Cancel pending order of 299th TAB" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "DELETE",
      path: `${ORDER_PATH}/sq-su`,
    });
    expect(
      await screen.findByText("Orders cancelled: 299th TAB"),
    ).toBeInTheDocument();
  });

  it("shows a refusal", async () => {
    renderTab({
      [`${ORDER_PATH}/sq-su`]: {
        status: 409,
        body: { detail: "299th TAB has no pending order." },
      },
    });
    await userEvent.click(
      await screen.findByRole("button", {
        name: "Cancel pending order of 299th TAB",
      }),
    );
    expect(await screen.findByText("Cancellation refused")).toBeInTheDocument();
    expect(
      screen.getByText("299th TAB has no pending order."),
    ).toBeInTheDocument();
  });
});

describe("create a squadron", () => {
  const open = async () => {
    await userEvent.click(
      await screen.findByRole("button", {
        name: "+ Create a squadron at Krymsk",
      }),
    );
    return screen.findByRole("dialog", { name: "New squadron at Krymsk" });
  };

  it("offers what the server allows and sends the choice", async () => {
    const calls = renderTab();
    const dialog = await open();
    const aircraft = await within(dialog).findByLabelText("Aircraft");
    expect(
      within(aircraft).getAllByRole("option").map((o) => o.textContent),
    ).toEqual(["MiG-29S", "Su-25T"]);

    await userEvent.selectOptions(aircraft, "Su-25T");
    const task = within(dialog).getByLabelText("Primary task");
    expect(task).toHaveValue("CAS");
    await userEvent.selectOptions(
      within(dialog).getByLabelText("Preset"),
      "Grach",
    );
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Create squadron" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/control-points/cp-1/squadrons",
      body: { aircraft: "Su-25T", primary_task: "CAS", preset: "Grach" },
    });
    expect(await screen.findByText("Squadron created")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("keeps the dialog open on a refusal", async () => {
    renderTab({
      "/control-points/cp-1/squadrons": {
        status: 409,
        body: { detail: "The squadron Grach is not available at Krymsk." },
      },
    });
    const dialog = await open();
    await within(dialog).findByLabelText("Aircraft");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Create squadron" }),
    );
    expect(await screen.findByText("Squadron refused")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});

import type {
  AirWing,
  AirWingPilot,
  AirWingSquadron,
  CareerJs,
} from "../api/liberationApi";
import { setupStore } from "../app/store";
import { CareerScreen } from "../secondary/CareerScreen";
import { Answer, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { AirWingScreen } from "./AirWingScreen";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const READY: AirWingPilot = {
  id: "p-ready",
  name: "O. Kravets",
  player: false,
  alive: true,
  status: "ready",
  status_text: "Ready",
  note: "",
  skill: "High",
  sorties: 12,
  kills: 4,
  on_leave: false,
};

const PLAYER: AirWingPilot = {
  ...READY,
  id: "p-player",
  name: "Maverick",
  player: true,
};

const DOWN: AirWingPilot = {
  ...READY,
  id: "p-down",
  name: "D. Hrytsenko",
  status: "down",
  status_text: "Down · awaiting CSAR",
  note: "2 turns left",
  leave_refusal: "D. Hrytsenko is not on active duty: downed.",
};

const PRISONER: AirWingPilot = {
  ...READY,
  id: "p-pow",
  name: "S. Moroz",
  status: "prisoner",
  status_text: "Prisoner of war",
  note: "Held at Abinsk",
  player_refusal: "S. Moroz is a prisoner of war.",
  leave_refusal: "S. Moroz is not on active duty: prisoner of war.",
};

const INJURED: AirWingPilot = {
  ...READY,
  id: "p-med",
  name: "A. Lysenko",
  status: "injured",
  status_text: "Medical · back T05",
  return_turn: 5,
  leave_refusal: "A. Lysenko is not on active duty: recovering.",
};

const FALLEN: AirWingPilot = {
  ...READY,
  id: "p-dead",
  name: "I. Bondar",
  alive: false,
  status: "dead",
  status_text: "Killed in action",
  player_refusal: "I. Bondar is dead.",
  leave_refusal: "I. Bondar is not on active duty: dead.",
};

const SQUADRON: AirWingSquadron = {
  id: "sq-1",
  name: '40th Brigade "Vorona"',
  nickname: "Vorona",
  aircraft: "MiG-29 9.13",
  sidc: "10030100001101000000",
  base_id: "cp-1",
  base: "Krymsk",
  owned: 10,
  max_aircraft: 12,
  initial: 12,
  purchased: 0,
  destroyed: 2,
  available: 10,
  untasked_crewed: 8,
  in_maintenance: 0,
  maintenance_text: "",
  pilots_ready: 2,
  pilots_alive: 5,
  sorties: 38,
  kills: 9,
  next_turn: ["2 aircraft arriving", "1 pilot back from medical"],
  primary_task: "BARCAP",
  tasks: [
    { task: "BARCAP", auto_assign: true },
    { task: "Escort", auto_assign: false },
  ],
  order: {
    squadron_id: "sq-1",
    squadron: "40th Brigade",
    aircraft: "MiG-29 9.13",
    aircraft_id: "F-16C",
    unit_cost: 28,
    owned: 10,
    max_aircraft: 12,
    pending: 0,
    max_add: 2,
    max_remove: 1,
  },
  parking_room: 6,
  pilots: [READY, PLAYER, DOWN, PRISONER, INJURED, FALLEN],
};

const OTHER: AirWingSquadron = {
  ...SQUADRON,
  id: "sq-2",
  name: "299th Brigade",
  aircraft: "Su-25T",
  nickname: undefined,
  base: "Anapa",
  base_id: "cp-2",
  order: undefined,
  pilots: [],
};

const AIR_WING: AirWing = {
  blue: true,
  squadron_count: 2,
  aircraft_count: 20,
  pilot_count: 5,
  bases: [
    { id: "cp-2", name: "Anapa", squadrons: [OTHER] },
    { id: "cp-1", name: "Krymsk", squadrons: [SQUADRON] },
  ],
  inventory: [
    {
      key: "a",
      base: "Krymsk",
      aircraft: "MiG-29 9.13",
      task: "Idle",
      target: "N/A",
      pilot: "N/A",
      crew: "N/A",
      allocated: false,
    },
    {
      key: "b",
      base: "Krymsk",
      aircraft: "MiG-29 9.13",
      task: "BARCAP",
      target: "Abinsk",
      pilot: "O. Kravets",
      crew: "AI",
      allocated: true,
    },
  ],
};

const DESTINATIONS = {
  room_here: 4,
  destinations: [
    {
      id: "cp-2",
      name: "Anapa",
      room: 12,
      overflow: ["299th Brigade"],
      selected: false,
    },
    {
      id: "cp-3",
      name: "Sochi",
      room: 1,
      refusal: "9 additional slots required",
      overflow: [],
      selected: false,
    },
  ],
};

const LIVERIES = [
  { label: "Default", use_livery_set: false, selected: false, livery_id: "d" },
  { label: "Winter", use_livery_set: false, selected: true, livery_id: "w" },
];

function renderScreen(
  path = "/air-wing",
  airWing: AirWing | null = AIR_WING,
  answers: Record<string, Answer> = {},
) {
  const calls = recordFetch(
    204,
    undefined,
    {
      "/air-wing": airWing,
      "/squadrons/sq-1/destinations": DESTINATIONS,
      "/squadrons/sq-2/destinations": DESTINATIONS,
      "/squadrons/sq-1/liveries": LIVERIES,
      "/squadrons/sq-2/liveries": [],
    },
    answers,
  );
  const router = createMemoryRouter(
    [
      { path: "/air-wing", element: <AirWingScreen /> },
      { path: "/air-wing/:view", element: <AirWingScreen /> },
      { path: "/career", element: <p>Career screen</p> },
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
  return { calls, router };
}

async function selectKrymsk() {
  await userEvent.click(
    await screen.findByRole("button", { name: /40th Brigade/ }),
  );
}

describe("squadrons view", () => {
  it("says when no campaign is loaded", async () => {
    renderScreen("/air-wing", null);
    expect(await screen.findByText("No campaign loaded.")).toBeInTheDocument();
  });

  it("groups squadrons by base and shows the sheet of the selected one", async () => {
    renderScreen();
    const list = await screen.findByRole("complementary", {
      name: "Squadrons by base",
    });
    expect(within(list).getByRole("heading", { name: "Anapa" })).toBeVisible();
    expect(within(list).getByRole("heading", { name: "Krymsk" })).toBeVisible();
    expect(screen.getByText(/2 squadrons · 20\s+aircraft/)).toBeInTheDocument();

    // The first squadron is shown first.
    expect(
      screen.getByRole("heading", { level: 2, name: "299th Brigade" }),
    ).toBeInTheDocument();
    await selectKrymsk();
    const sheet = screen.getByRole("main", { name: /40th Brigade/ });
    expect(within(sheet).getByText(/based at Krymsk/)).toBeInTheDocument();
    expect(within(sheet).getByText("2 aircraft arriving")).toBeInTheDocument();
    expect(
      within(sheet).getByText("1 pilot back from medical"),
    ).toBeInTheDocument();
    expect(
      within(sheet).getByText("2 aircraft lost this campaign"),
    ).toBeInTheDocument();
    expect(within(sheet).getByLabelText("Primary task")).toHaveValue("BARCAP");
  });

  it("shows each pilot status and locks what the engine refuses", async () => {
    renderScreen();
    await selectKrymsk();
    const pilots = screen.getByRole("region", { name: "Pilots" });
    expect(within(pilots).getAllByText(/● Ready/)).toHaveLength(2);
    expect(within(pilots).getByText(/Down · awaiting CSAR/)).toBeVisible();
    expect(within(pilots).getByText(/Prisoner of war/)).toBeVisible();
    expect(within(pilots).getByText(/Medical · back T05/)).toBeVisible();
    expect(within(pilots).getByText("Held at Abinsk")).toBeVisible();

    expect(
      within(pilots).getByRole("checkbox", { name: "Player pilot: S. Moroz" }),
    ).toBeDisabled();
    expect(
      within(pilots).getByRole("checkbox", {
        name: "Player pilot: O. Kravets",
      }),
    ).toBeEnabled();
    expect(
      within(pilots).getByRole("button", { name: "Send A. Lysenko on leave" }),
    ).toBeDisabled();

    // The fallen have their own list, without actions.
    const fallen = screen.getByRole("region", { name: "Killed in action" });
    expect(within(fallen).getByText("I. Bondar")).toBeInTheDocument();
    expect(within(pilots).queryByText("I. Bondar")).not.toBeInTheDocument();
    expect(
      within(fallen).queryByRole("button", { name: /Rename/ }),
    ).not.toBeInTheDocument();
  });

  it("links player pilots to their career, and only them", async () => {
    const { router } = renderScreen();
    await selectKrymsk();
    expect(
      screen.queryByRole("link", { name: "Career of O. Kravets" }),
    ).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("link", { name: "Career of Maverick" }),
    );
    expect(router.state.location.pathname).toBe("/career");
    expect(router.state.location.search).toBe("?pilot=p-player");
  });

  it("sends the player box to the server", async () => {
    const { calls } = renderScreen();
    await selectKrymsk();
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Player pilot: O. Kravets" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PATCH",
      path: "/squadrons/sq-1/pilots/p-ready",
      body: { player: true },
    });
  });

  it("sends leave and rename, and keeps the modal on a refusal", async () => {
    const { calls } = renderScreen("/air-wing", AIR_WING, {
      "/squadrons/sq-1/pilots/p-ready": {
        status: 409,
        body: { detail: "A pilot needs a name." },
      },
    });
    await selectKrymsk();
    await userEvent.click(
      screen.getByRole("button", { name: "Rename O. Kravets" }),
    );
    const dialog = await screen.findByRole("dialog");
    await userEvent.clear(within(dialog).getByLabelText("New name"));
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Rename" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toEqual({ name: "" });
    expect(
      (await screen.findAllByText("A pilot needs a name.")).length,
    ).toBeGreaterThan(0);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("adds a player pilot", async () => {
    const { calls } = renderScreen();
    await selectKrymsk();
    await userEvent.click(
      screen.getByRole("button", { name: "New player pilot" }),
    );
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Pilot name"), "Iceman");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Add pilot" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/squadrons/sq-1/pilots",
      body: { name: "Iceman" },
    });
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
  });

  it("disables a new pilot with the engine's reason", async () => {
    renderScreen("/air-wing", {
      ...AIR_WING,
      bases: [
        {
          id: "cp-1",
          name: "Krymsk",
          squadrons: [{ ...SQUADRON, new_pilot_refusal: "It is full." }],
        },
      ],
    });
    const button = await screen.findByRole("button", {
      name: "New player pilot",
    });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("title", "It is full.");
  });

  it("changes the primary task, auto tasks and livery", async () => {
    const { calls } = renderScreen();
    await selectKrymsk();
    await userEvent.selectOptions(
      screen.getByLabelText("Primary task"),
      "Escort",
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: "/squadrons/sq-1/primary-task",
      body: { task: "Escort" },
    });
    await userEvent.click(screen.getByRole("checkbox", { name: "Escort" }));
    await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls[1]).toMatchObject({
      path: "/squadrons/sq-1/auto-assign",
      body: { task: "Escort", enabled: true },
    });
    const livery = await screen.findByLabelText("Livery");
    await waitFor(() => expect(livery).toHaveDisplayValue("Winter"));
    await userEvent.selectOptions(livery, "Default");
    await waitFor(() => expect(calls).toHaveLength(3));
    expect(calls[2]).toMatchObject({
      path: "/squadrons/sq-1/livery",
      body: { livery_id: "d", use_livery_set: false },
    });
  });

  it("buys through the base orders, within the limits of the server", async () => {
    const { calls } = renderScreen();
    await selectKrymsk();
    const buy = screen.getByRole("button", { name: "Buy aircraft" });
    expect(buy).toBeDisabled();
    const more = screen.getByRole("button", { name: "One aircraft more" });
    await userEvent.click(more);
    await userEvent.click(more);
    expect(more).toBeDisabled(); // max_add
    await userEvent.click(
      screen.getByRole("button", { name: "Buy 2 aircraft · $56M" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/control-points/cp-1/purchases/aircraft",
      body: { orders: [{ squadron_id: "sq-1", quantity: 2 }] },
    });
  });

  it("shows no order for an enemy squadron", async () => {
    renderScreen("/air-wing", { ...AIR_WING, blue: false });
    await screen.findByRole("heading", { level: 2, name: "299th Brigade" });
    expect(
      screen.queryByRole("group", { name: "Aircraft order" }),
    ).not.toBeInTheDocument();
  });

  it("transfers to a base with room, and shows why others are refused", async () => {
    const { calls } = renderScreen();
    await selectKrymsk();
    await userEvent.click(screen.getByRole("button", { name: "Transfer" }));
    const dialog = await screen.findByRole("dialog");
    expect(
      await within(dialog).findByText("9 additional slots required"),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText("May start in the air: 299th Brigade"),
    ).toBeInTheDocument();
    const buttons = within(dialog).getAllByRole("button", { name: "Transfer" });
    expect(buttons[1]).toBeDisabled();
    await userEvent.click(buttons[0]);
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: "/squadrons/sq-1/destination",
      body: { destination_id: "cp-2" },
    });
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
  });

  it("offers to cancel a transfer in progress", async () => {
    const { calls } = renderScreen("/air-wing", {
      ...AIR_WING,
      bases: [
        {
          id: "cp-1",
          name: "Krymsk",
          squadrons: [{ ...SQUADRON, destination: "Anapa" }],
        },
      ],
    });
    expect(
      await screen.findByText(/transfer ordered to Anapa/),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Transfer" }));
    await userEvent.click(await screen.findByRole("button", { name: "Stay" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toEqual({ destination_id: null });
  });
});

describe("other views", () => {
  it("lists aircraft and filters the unallocated", async () => {
    renderScreen("/air-wing/aircraft");
    const row = await screen.findByRole("row", { name: /Abinsk/ });
    expect(row).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Unallocated only" }),
    );
    expect(screen.queryByRole("row", { name: /Abinsk/ })).toBeNull();
    expect(screen.getByRole("row", { name: /Idle/ })).toBeInTheDocument();
  });

  it("lists every pilot with their squadron", async () => {
    renderScreen("/air-wing/pilots");
    const row = await screen.findByRole("row", { name: /S\. Moroz/ });
    expect(within(row).getByText(/40th Brigade/)).toBeInTheDocument();
    expect(within(row).getByText("Krymsk")).toBeInTheDocument();
  });

  it("asks the enemy air wing and switches views by route", async () => {
    const { router } = renderScreen();
    await screen.findByRole("heading", { level: 2, name: "299th Brigade" });
    await userEvent.click(screen.getByRole("tab", { name: "Pilots" }));
    expect(router.state.location.pathname).toBe("/air-wing/pilots");
    await userEvent.click(screen.getByRole("checkbox", { name: "Show enemy" }));
    expect(screen.getByRole("checkbox", { name: "Show enemy" })).toBeChecked();
  });

  it("goes back to the squadrons from an unknown view", async () => {
    const { router } = renderScreen("/air-wing/nope");
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/air-wing"),
    );
  });
});

describe("career link", () => {
  const CAREER: CareerJs = {
    pilot_id: "a",
    pilot: "Goose",
    squadron: "VF-1",
    status: "Active",
    alive: true,
    totals: [],
    awards: [],
    history: [],
  };

  it("opens the career of the pilot in the link", async () => {
    recordFetch(204, undefined, {
      "/careers/": [CAREER, { ...CAREER, pilot_id: "b", pilot: "Maverick" }],
    });
    const router = createMemoryRouter(
      [{ path: "/career", element: <CareerScreen /> }],
      { initialEntries: ["/career?pilot=b"] },
    );
    render(
      <Provider store={setupStore()}>
        <RouterProvider router={router} />
      </Provider>,
    );
    expect(await screen.findByRole("combobox")).toHaveDisplayValue(
      "Maverick (VF-1)",
    );
  });
});

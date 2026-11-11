import type {
  AutoCreateOptions,
  FlightOptions,
  PackageDetail,
} from "../api/liberationApi";
import { setupStore } from "../app/store";
import { Answer, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { PackageEditor } from "./PackageEditor";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const PACKAGE: PackageDetail = {
  id: "pkg-1",
  blue: true,
  task: "DEAD",
  description: "DEAD",
  target: "SA-11 Krasnodar East",
  tot: "2022-05-17T07:12:30",
  auto_asap: false,
  tot_locked: false,
  can_auto_create: false,
  closest_base: "Krymsk",
  closest_base_distance_nm: 64,
  objectives: ["Blind the air defences"],
  flights: [
    {
      id: "f-1",
      task: "DEAD",
      aircraft: "F/A-18C",
      count: 2,
      clients: 1,
      missing_pilots: 0,
      squadron: "VFA-25",
      departure: "Anapa",
      start_type: "Cold",
      startup: "2022-05-17T06:28:00",
      takeoff: "2022-05-17T06:38:00",
      cancelable: true,
    },
    {
      id: "f-2",
      task: "Escort",
      aircraft: "F-15C",
      count: 2,
      clients: 0,
      missing_pilots: 1,
      squadron: "58th TFS",
      departure: "Krymsk",
      start_type: "Warm",
      startup: "2022-05-17T06:33:00",
      takeoff: "2022-05-17T06:43:00",
      cancelable: false,
    },
  ],
};

const EMPTY: PackageDetail = {
  ...PACKAGE,
  task: undefined,
  description: "No mission",
  auto_asap: true,
  can_auto_create: true,
  closest_base: undefined,
  closest_base_distance_nm: undefined,
  flights: [],
};

const squadron = (id: string, overrides: object = {}) => ({
  id,
  name: id,
  base: "Krymsk",
  available: 6,
  max_size: 4,
  ...overrides,
});

const FLIGHT_OPTIONS: FlightOptions = {
  start_types: ["Cold", "Warm", "Runway", "In Flight"],
  tasks: [
    {
      task: "DEAD",
      aircraft: [
        {
          id: "fa18",
          name: "F/A-18C",
          player_module: true,
          squadrons: [squadron("vfa-25")],
        },
        {
          id: "f16",
          name: "F-16CM",
          player_module: false,
          squadrons: [
            squadron("sq-16", { max_size: 2 }),
            squadron("sq-carrier", { required_start_type: "In Flight" }),
          ],
        },
      ],
    },
    { task: "SEAD", aircraft: [] },
  ],
};

const AUTO_OPTIONS: AutoCreateOptions = {
  primary: [
    {
      task: "DEAD",
      default_count: 3,
      aircraft: [
        { id: "fa18", name: "F/A-18C", max_count: 4 },
        { id: "f16", name: "F-16C", max_count: 1 },
      ],
    },
    {
      task: "CAS",
      default_count: 2,
      aircraft: [{ id: "a10", name: "A-10C", max_count: 4 }],
    },
  ],
  support: [
    {
      task: "TARCAP",
      default_count: 2,
      aircraft: [{ id: "f15", name: "F-15C", max_count: 4 }],
    },
    {
      task: "Escort",
      default_count: 2,
      aircraft: [{ id: "f15", name: "F-15C", max_count: 1 }],
    },
    { task: "SEAD", default_count: 2, aircraft: [] },
  ],
  excluded_with_cas: ["Escort"],
  min_count: 1,
  max_count: 4,
};

function renderEditor(
  pkg: PackageDetail = PACKAGE,
  answers: Record<string, Answer> = {},
) {
  const store = setupStore();
  const calls = recordFetch(
    200,
    pkg,
    {
      "/packages/pkg-1": pkg,
      "/packages/pkg-1/flight-options": FLIGHT_OPTIONS,
      "/packages/pkg-1/auto-create": AUTO_OPTIONS,
    },
    answers,
  );
  const router = createMemoryRouter(
    [
      { path: "/", element: null },
      {
        path: "/packages/:id",
        element: (
          <ToastProvider>
            <PackageEditor />
          </ToastProvider>
        ),
      },
    ],
    { initialEntries: ["/packages/pkg-1"] },
  );
  render(
    <Provider store={store}>
      <RouterProvider router={router} />
    </Provider>,
  );
  return { calls, router, store };
}

describe("package editor", () => {
  it("shows the task, target, TOT and flights", async () => {
    renderEditor();
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "SA-11 Krasnodar East",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("64 nm from Krymsk")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Objective: Blind the air defences"),
    ).toHaveTextContent("Objective");
    expect(screen.getByLabelText("Time on target")).toHaveValue("07:12:30");
    const card = screen.getByRole("button", { name: /F\/A-18C/ });
    expect(card).toHaveTextContent("2 × F/A-18C");
    expect(within(card).getByRole("img", { name: "Player" })).toBeVisible();
    expect(card).toHaveTextContent("DEAD · Anapa");
    expect(card).toHaveTextContent("Start 06:28 · T/O 06:38");
    expect(screen.getByRole("button", { name: /F-15C/ })).toHaveTextContent(
      "Missing 1 pilot",
    );
  });

  it("explains an unknown package", async () => {
    const calls = recordFetch();
    globalThis.fetch = async () =>
      new Response(
        JSON.stringify({ detail: "This package is no longer planned." }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      );
    const router = createMemoryRouter(
      [{ path: "/packages/:id", element: <PackageEditor /> }],
      { initialEntries: ["/packages/gone"] },
    );
    render(
      <Provider store={setupStore()}>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </Provider>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This package is no longer planned.",
    );
    expect(calls).toHaveLength(0);
  });

  it("sends a typed TOT when leaving the field", async () => {
    const { calls } = renderEditor();
    const input = await screen.findByLabelText("Time on target");
    fireEvent.change(input, { target: { value: "08:30" } });
    expect(calls).toHaveLength(0);
    fireEvent.blur(input);
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: "/packages/pkg-1/tot",
      body: { tot: "08:30:00" },
    });
  });

  it("does not send an unchanged TOT", async () => {
    const { calls } = renderEditor();
    fireEvent.blur(await screen.findByLabelText("Time on target"));
    expect(calls).toHaveLength(0);
  });

  it("asks for the earliest TOT", async () => {
    const { calls } = renderEditor();
    await userEvent.click(
      await screen.findByRole("button", { name: "Earliest TOT" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/packages/pkg-1/tot/earliest",
    });
  });

  it("locks the TOT once flights have started", async () => {
    renderEditor({ ...PACKAGE, tot_locked: true });
    expect(await screen.findByLabelText("Time on target")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Earliest TOT" })).toBeDisabled();
  });

  it("shows a refusal as a toast", async () => {
    renderEditor(PACKAGE, {
      "/packages/pkg-1/tot/earliest": {
        status: 409,
        body: { detail: "Flights of this package have started." },
      },
    });
    await userEvent.click(
      await screen.findByRole("button", { name: "Earliest TOT" }),
    );
    expect(
      await screen.findByText("Flights of this package have started."),
    ).toBeInTheDocument();
  });

  it("deletes the package and goes back to the command view", async () => {
    const { calls, router } = renderEditor();
    await userEvent.click(
      await screen.findByRole("button", { name: "Delete package" }),
    );
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(calls[0]).toMatchObject({
      method: "DELETE",
      path: "/packages/pkg-1",
    });
  });

  it("renames the package when leaving the field", async () => {
    const { calls } = renderEditor();
    const input = await screen.findByLabelText("Package name");
    await userEvent.type(input, "Viper");
    fireEvent.blur(input);
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: "/packages/pkg-1/name",
      body: { name: "Viper" },
    });
  });

  it("removes the selected flight, or aborts it under way", async () => {
    const { calls } = renderEditor();
    await userEvent.click(
      await screen.findByRole("button", { name: "Remove flight" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "DELETE",
      path: "/packages/pkg-1/flights/f-1",
    });
    await userEvent.click(screen.getByRole("button", { name: /F-15C/ }));
    expect(
      screen.getByRole("button", { name: "Abort flight" }),
    ).toBeInTheDocument();
  });

  it("lays out the flight tabs", async () => {
    renderEditor();
    for (const name of [
      "General",
      "Route",
      "Payload",
      "Pilots",
      "Radios & TACAN",
    ]) {
      expect(await screen.findByRole("tab", { name })).toBeInTheDocument();
    }
    expect(
      screen.queryByRole("button", { name: "Open the Qt editor" }),
    ).not.toBeInTheDocument();
  });

  it("says what to do with an empty package, with auto-create", async () => {
    renderEditor(EMPTY);
    expect(await screen.findByText(/No flight yet/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Auto-create" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });

  it("offers auto-create on an empty package only", async () => {
    renderEditor();
    await screen.findByRole("button", { name: "+ Flight" });
    expect(
      screen.queryByRole("button", { name: "Auto-create" }),
    ).not.toBeInTheDocument();
  });
});

describe("add flight form", () => {
  const open = async () => {
    await userEvent.click(
      await screen.findByRole("button", { name: "+ Flight" }),
    );
    await screen.findByLabelText("Task");
  };

  it("lists the player's modules first, marked, and the others apart", async () => {
    renderEditor();
    await open();
    const own = screen.getByRole("group", { name: "Your modules" });
    expect(within(own).getByRole("option")).toHaveTextContent("★ F/A-18C");
    const others = screen.getByRole("group", { name: "AI only" });
    expect(within(others).getByRole("option")).toHaveTextContent("F-16CM");
  });

  it("adds a flight with the first choices and the default start", async () => {
    const { calls } = renderEditor();
    await open();
    expect(screen.getByLabelText("Size")).toHaveValue("4");
    await userEvent.click(screen.getByRole("button", { name: "Add flight" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/packages/pkg-1/flights",
      body: { task: "DEAD", squadron_id: "vfa-25", size: 4 },
    });
    expect(calls[0].body).not.toHaveProperty("start_type");
    await waitFor(() =>
      expect(screen.queryByLabelText("Task")).not.toBeInTheDocument(),
    );
  });

  it("follows the task, aircraft and squadron, and keeps the size possible", async () => {
    const { calls } = renderEditor();
    await open();
    await userEvent.selectOptions(screen.getByLabelText("Aircraft"), "f16");
    expect(screen.getByLabelText("Squadron")).toHaveValue("sq-16");
    expect(screen.getByLabelText("Size")).toHaveValue("2");
    await userEvent.selectOptions(
      screen.getByLabelText("Start type"),
      "Runway",
    );
    await userEvent.click(screen.getByRole("button", { name: "Add flight" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toEqual({
      task: "DEAD",
      squadron_id: "sq-16",
      size: 2,
      start_type: "Runway",
    });
  });

  it("locks the start type a base dictates", async () => {
    renderEditor();
    await open();
    await userEvent.selectOptions(screen.getByLabelText("Aircraft"), "f16");
    await userEvent.selectOptions(
      screen.getByLabelText("Squadron"),
      "sq-carrier",
    );
    expect(screen.getByLabelText("Start type")).toBeDisabled();
    expect(screen.getByLabelText("Start type")).toHaveValue("In Flight");
  });

  it("cannot add a flight of a task without aircraft", async () => {
    renderEditor();
    await open();
    await userEvent.selectOptions(screen.getByLabelText("Task"), "SEAD");
    expect(screen.getByLabelText("Aircraft")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add flight" })).toBeDisabled();
  });

  it("keeps the form open on a refusal", async () => {
    renderEditor(PACKAGE, {
      "/packages/pkg-1/flights": {
        status: 409,
        body: { detail: "Add the flight to escort first." },
      },
    });
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Add flight" }));
    expect(
      await screen.findByText("Add the flight to escort first."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Task")).toBeInTheDocument();
  });
});

describe("auto-create form", () => {
  const open = async () => {
    await userEvent.click(
      await screen.findByRole("button", { name: "Auto-create" }),
    );
    await screen.findByLabelText("Main task");
  };

  it("sends the main flight and the ticked ones", async () => {
    const { calls } = renderEditor(EMPTY);
    await open();
    await userEvent.click(screen.getByLabelText("TARCAP"));
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/packages/pkg-1/auto-create",
      body: {
        flights: [
          { task: "DEAD", count: 3, aircraft: "fa18" },
          { task: "TARCAP", count: 2, aircraft: "f15" },
        ],
      },
    });
  });

  it("leaves out what a CAS package does not take", async () => {
    const { calls } = renderEditor(EMPTY);
    await open();
    await userEvent.click(screen.getByLabelText("Escort"));
    await userEvent.selectOptions(screen.getByLabelText("Main task"), "CAS");
    expect(screen.getByLabelText("Escort")).toBeDisabled();
    expect(screen.getByLabelText("Escort")).not.toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toEqual({
      flights: [{ task: "CAS", count: 2, aircraft: "a10" }],
    });
  });

  it("keeps a flight within what the chosen aircraft can fill", async () => {
    const { calls } = renderEditor(EMPTY);
    await open();
    expect(screen.getByRole("option", { name: "F/A-18C" })).toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("DEAD aircraft type"),
      screen.getByRole("option", { name: "F-16C (1 at most)" }),
    );
    await userEvent.click(screen.getByLabelText("Escort"));
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toEqual({
      flights: [
        { task: "DEAD", count: 1, aircraft: "f16" },
        { task: "Escort", count: 1, aircraft: "f15" },
      ],
    });
  });

  it("does not offer a flight no aircraft can fly", async () => {
    renderEditor(EMPTY);
    await open();
    expect(screen.getByLabelText("SEAD")).toBeDisabled();
    expect(screen.getByLabelText("SEAD aircraft type")).toHaveDisplayValue(
      "None available",
    );
  });

  it("explains why it failed and stays open", async () => {
    renderEditor(EMPTY, {
      "/packages/pkg-1/auto-create": {
        status: 409,
        body: { detail: "Auto-create package failed." },
      },
    });
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(
      await screen.findByText("Auto-create package failed."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Main task")).toBeInTheDocument();
  });
});

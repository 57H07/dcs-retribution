import type { FlightSettings, PackageDetail } from "../api/liberationApi";
import { setupStore } from "../app/store";
import { Answer, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { PackageEditor } from "./PackageEditor";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const PACKAGE: PackageDetail = {
  id: "pkg-1",
  blue: true,
  task: "DEAD",
  description: "DEAD",
  target: "SA-11",
  tot: "2022-05-17T07:12:30",
  auto_asap: false,
  tot_locked: false,
  can_auto_create: false,
  flights: [
    {
      id: "f-1",
      task: "DEAD",
      aircraft: "F-16CM",
      count: 2,
      clients: 0,
      missing_pilots: 1,
      squadron: "101st",
      departure: "Ramat David",
      start_type: "Cold",
      startup: "2022-05-17T06:28:00",
      takeoff: "2022-05-17T06:38:00",
      cancelable: true,
    },
    {
      id: "f-2",
      task: "DEAD",
      aircraft: "F-15E",
      count: 2,
      clients: 0,
      missing_pilots: 0,
      squadron: "69th",
      departure: "Ramat David",
      start_type: "Cold",
      startup: "2022-05-17T06:28:00",
      takeoff: "2022-05-17T06:38:00",
      cancelable: true,
    },
  ],
};

const SETTINGS: FlightSettings = {
  id: "f-1",
  task: "DEAD",
  aircraft: "F-16CM",
  departure: "Ramat David",
  arrival: "Ramat David",
  startup: "2022-05-17T06:28:00",
  editable: true,
  squadron: {
    id: "sq-101",
    name: "101st",
    aircraft: "F-16CM",
    base: "Ramat David",
    available: 8,
  },
  squadron_options: [
    {
      id: "sq-69",
      name: "69th",
      aircraft: "F-15E",
      base: "Ramat David",
      available: 8,
    },
  ],
  count: 2,
  max_count: 4,
  start_type: "Cold",
  start_types: ["Cold", "Warm", "Runway", "In Flight"],
  start_type_locked: false,
  divert_options: [{ id: "cp-1", name: "Ramat David" }],
  tot_offset_seconds: -90,
  callsign_names: ["Enfield", "Springfield"],
  callsign_min_number: 1,
  callsign_max_number: 9,
  slots: [{ pilot: { id: "p-1", name: "Maverick", player: true } }, {}],
  free_pilots: [{ id: "p-2", name: "Goose", player: false }],
};

const SETTINGS_PATH = "/packages/pkg-1/flights/f-1/settings";

function renderEditor(
  settings: FlightSettings = SETTINGS,
  answers: Record<string, Answer> = {},
) {
  const store = setupStore();
  const calls = recordFetch(
    200,
    PACKAGE,
    { "/packages/pkg-1": PACKAGE, [SETTINGS_PATH]: settings },
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
  return calls;
}

describe("General tab of a flight", () => {
  it("shows what the engine has and offers", async () => {
    renderEditor();
    expect(await screen.findByLabelText("Squadron")).toHaveValue("sq-101");
    expect(
      screen.getByRole("option", { name: /69th · F-15E/ }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Start type")).toHaveValue("Cold");
    expect(screen.getByLabelText("Divert")).toHaveValue("");
    expect(screen.getByLabelText("Callsign")).toHaveValue("");
    expect(screen.getByLabelText("Minutes")).toHaveValue("1");
    expect(screen.getByLabelText("Seconds")).toHaveValue("30");
    expect(screen.getByLabelText("Ahead of package")).toBeChecked();
    expect(screen.getByLabelText("Number")).toBeDisabled();
  });

  it("sends each field as its own command", async () => {
    const calls = renderEditor();
    await screen.findByLabelText("Squadron");

    await userEvent.selectOptions(screen.getByLabelText("Start type"), "Warm");
    await userEvent.selectOptions(
      screen.getByLabelText("Divert"),
      "Ramat David",
    );
    await userEvent.selectOptions(screen.getByLabelText("Callsign"), "Enfield");
    await userEvent.click(
      screen.getByRole("button", { name: "Increase Size" }),
    );
    await userEvent.click(screen.getByLabelText("Ahead of package"));

    await waitFor(() => expect(calls).toHaveLength(5));
    const flight = "/packages/pkg-1/flights/f-1";
    expect(calls.map(({ method, path, body }) => [method, path, body])).toEqual(
      [
        ["PUT", `${flight}/start-type`, { start_type: "Warm" }],
        ["PUT", `${flight}/divert`, { divert_id: "cp-1" }],
        ["PUT", `${flight}/callsign`, { name: "Enfield", number: 1 }],
        ["PUT", `${flight}/size`, { size: 3 }],
        ["PUT", `${flight}/tot-offset`, { seconds: 90 }],
      ],
    );
  });

  it("removes the divert field and resets the callsign", async () => {
    const calls = renderEditor({
      ...SETTINGS,
      divert_id: "cp-1",
      callsign: { name: "Enfield", number: 2 },
    });
    expect(await screen.findByLabelText("Divert")).toHaveValue("cp-1");

    await userEvent.selectOptions(screen.getByLabelText("Divert"), "None");
    await userEvent.selectOptions(
      screen.getByLabelText("Callsign"),
      "Automatic",
    );

    await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls[0].body).toEqual({});
    expect(calls[1].method).toBe("DELETE");
    expect(calls[1].path).toBe("/packages/pkg-1/flights/f-1/callsign");
  });

  it("commits the custom name on blur and shows a refusal", async () => {
    const path = "/packages/pkg-1/flights/f-1/custom-name";
    const calls = renderEditor(SETTINGS, {
      [path]: {
        status: 409,
        body: { detail: "Cannot include | in flight name" },
      },
    });
    const input = await screen.findByLabelText("Custom name");

    await userEvent.type(input, "a|b");
    fireEvent.blur(input);

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toEqual({ name: "a|b" });
    expect(
      await screen.findByText("Cannot include | in flight name"),
    ).toBeInTheDocument();
    await waitFor(() => expect(input).toHaveValue(""));
  });

  it("moves to the flight that replaces this one on a squadron change", async () => {
    const path = "/packages/pkg-1/flights/f-1/squadron";
    const calls = renderEditor(SETTINGS, {
      [path]: { body: { flight_id: "f-2", package: PACKAGE } },
    });
    const squadron = await screen.findByLabelText("Squadron");

    await userEvent.selectOptions(squadron, "sq-69");

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toEqual({ squadron_id: "sq-69" });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /F-15E/ })).toHaveAttribute(
        "aria-pressed",
        "true",
      ),
    );
  });

  it("locks what the engine locks", async () => {
    renderEditor({
      ...SETTINGS,
      start_type_locked: true,
      squadron_options: [],
    });
    expect(await screen.findByLabelText("Squadron")).toBeDisabled();
    expect(screen.getByLabelText("Start type")).toBeDisabled();
    expect(screen.getByLabelText("Custom name")).toBeEnabled();
  });

  it("leaves only the name and callsign of a flight under way", async () => {
    renderEditor({ ...SETTINGS, editable: false });
    expect(await screen.findByText(/under way/)).toBeInTheDocument();
    expect(screen.getByLabelText("Squadron")).toBeDisabled();
    expect(screen.getByLabelText("Size")).toBeDisabled();
    expect(screen.getByLabelText("Divert")).toBeDisabled();
    expect(screen.getByLabelText("Minutes")).toBeDisabled();
    expect(screen.getByLabelText("Custom name")).toBeEnabled();
    expect(screen.getByLabelText("Callsign")).toBeEnabled();
  });
});

describe("Pilots tab of a flight", () => {
  async function openPilots(settings: FlightSettings = SETTINGS) {
    const calls = renderEditor(settings);
    await userEvent.click(await screen.findByRole("tab", { name: "Pilots" }));
    await screen.findByRole("list", { name: "Pilots" });
    return calls;
  }

  it("lists one slot per aircraft with the free pilots", async () => {
    await openPilots();
    expect(screen.getByLabelText("Pilot 1")).toHaveValue("p-1");
    expect(screen.getByLabelText("Pilot 2")).toHaveValue("");
    expect(screen.getByLabelText("Player 1")).toBeChecked();
    expect(screen.getByLabelText("Player 2")).toBeDisabled();
    expect(screen.getAllByRole("option", { name: "Goose" })).toHaveLength(2);
  });

  it("assigns a pilot, empties a slot and toggles a player", async () => {
    const calls = await openPilots();

    await userEvent.selectOptions(screen.getByLabelText("Pilot 2"), "Goose");
    await userEvent.selectOptions(
      screen.getByLabelText("Pilot 1"),
      "Unassigned",
    );
    await userEvent.click(screen.getByLabelText("Player 1"));

    await waitFor(() => expect(calls).toHaveLength(3));
    const flight = "/packages/pkg-1/flights/f-1";
    expect(calls.map(({ path, body }) => [path, body])).toEqual([
      [`${flight}/pilots/1`, { pilot_id: "p-2" }],
      [`${flight}/pilots/0`, {}],
      [`${flight}/pilots/0/player`, { player: false }],
    ]);
  });

  it("locks the player box with the reason of the engine", async () => {
    await openPilots({
      ...SETTINGS,
      slots: [
        {
          pilot: { id: "p-1", name: "Maverick", player: false },
          player_refusal: "The F-15E is not flyable.",
        },
      ],
    });
    const box = screen.getByLabelText("Player 1");
    expect(box).toBeDisabled();
    expect(box).toHaveAttribute("title", "The F-15E is not flyable.");
  });
});

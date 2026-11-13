import type {
  BaseActions,
  CartridgeSettings,
  FlightRadios,
  PackageDetail,
} from "../api/liberationApi";
import { setupStore } from "../app/store";
import { Answer, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { FlightRadiosTab } from "./FlightRadiosTab";
import { TransportEntry } from "./TransportEntry";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const RADIOS: FlightRadios = {
  frequency_mhz: 251.25,
  modulation: "AM",
  ranges: [
    { min_mhz: 118, max_mhz: 174, step_mhz: 0.025, modulation: "AM" },
    { min_mhz: 225, max_mhz: 400, step_mhz: 0.025, modulation: "AM" },
    { min_mhz: 225, max_mhz: 400, step_mhz: 0.025, modulation: "FM" },
  ],
  warnings: ["The flight frequency is double booked on 251.250 MHz AM."],
  package_min_mhz: 30,
  package_max_mhz: 400,
  package_warnings: [],
  has_tacan: false,
  tacan_warnings: [],
  datalink: {
    name: "Link 16",
    fields: [
      { identifier: "STN_L16", label: "STN", max_length: 5 },
      { identifier: "VoiceCallsignLabel", label: "Label", max_length: 2 },
    ],
    members: [
      { index: 0, pilot: "Maverick", values: { STN_L16: "00017" } },
      { index: 1, values: {} },
    ],
  },
  departure_id: "cp-1",
  departure: "Stennis",
};

const CARTRIDGE: CartridgeSettings = {
  squadron: "VFA-25",
  aircraft: "F/A-18C",
  auto_load: true,
  cmds_fields: [
    {
      id: "chaff_quantity",
      label: "Chaff",
      minimum: 0,
      maximum: 99,
      step: 1,
    },
    {
      id: "flare_quantity",
      label: "Flares",
      minimum: 0,
      maximum: 99,
      step: 1,
    },
  ],
  cmds_programs: [
    {
      id: "MAN_1",
      label: "MAN 1",
      values: { chaff_quantity: 1, flare_quantity: 1 },
    },
  ],
  cmds_modified: false,
  same_aircraft_squadrons: 2,
};

const ACTIONS = {
  can_transfer: false,
  can_plan_transport: false,
  can_attack_airfield: false,
  radios: {
    has_frequency: true,
    has_tacan: true,
    has_icls: true,
    has_link4: true,
    icls_channel: 7,
    icls_callsign: "STN",
    link4_mhz: 336,
    warnings: [],
  },
} as unknown as BaseActions;

const RADIOS_PATH = "/packages/pkg-1/flights/f-1/radios";

function renderTab(
  radios: FlightRadios = RADIOS,
  actions: BaseActions | null = null,
  answers: Record<string, Answer> = {},
) {
  const calls = recordFetch(
    200,
    radios,
    {
      [RADIOS_PATH]: radios,
      "/control-points/cp-1/actions": actions,
    },
    answers,
  );
  const router = createMemoryRouter(
    [
      {
        path: "/packages/:id",
        element: (
          <ToastProvider>
            <FlightRadiosTab flightId="f-1" />
          </ToastProvider>
        ),
      },
    ],
    { initialEntries: ["/packages/pkg-1"] },
  );
  render(
    <Provider store={setupStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
  return calls;
}

describe("flight radios tab", () => {
  it("saves the data cartridge of the last mission (#191)", async () => {
    const calls = renderTab(
      { ...RADIOS, cartridge_file: "Retribution Enfield 1.dtc" },
      null,
      {
        [`${RADIOS_PATH}/cartridge/save`]: {
          body: { outcome: "saved", path: "C:/DTC/Retribution Enfield 1.dtc" },
        },
      },
    );
    const panel = await screen.findByRole("region", {
      name: "Data cartridge",
    });
    expect(panel).toHaveTextContent("Retribution Enfield 1.dtc");
    await userEvent.click(
      within(panel).getByRole("button", { name: "Save the cartridge…" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: `${RADIOS_PATH}/cartridge/save`,
    });
    expect(await screen.findByText("Cartridge saved")).toBeInTheDocument();
  });

  it("sets the cartridge of the squadron and its CMDS programs (#221)", async () => {
    const settingsPath = `${RADIOS_PATH}/cartridge/settings`;
    const calls = renderTab(
      { ...RADIOS, cartridge_settings: CARTRIDGE },
      null,
      {
        [settingsPath]: { body: RADIOS },
        [`${settingsPath}/apply-to-aircraft`]: { body: RADIOS },
      },
    );
    const panel = await screen.findByRole("region", {
      name: "Data cartridge",
    });
    expect(panel).toHaveTextContent("For every player flight of VFA-25");
    expect(
      within(panel).getByRole("button", { name: "Module defaults" }),
    ).toBeDisabled();

    await userEvent.click(
      within(panel).getByRole("switch", { name: "Load at spawn" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: settingsPath,
      body: { auto_load: false },
    });

    const flares = within(panel).getByLabelText("Flares of MAN 1");
    expect(flares).toHaveValue(1);
    const setPrograms = within(panel).getByRole("button", {
      name: "Set the programs",
    });
    expect(setPrograms).toBeDisabled();
    await userEvent.clear(flares);
    await userEvent.type(flares, "3");
    await userEvent.click(setPrograms);
    await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls[1]).toMatchObject({
      method: "PUT",
      path: settingsPath,
      body: { cmds: { MAN_1: { chaff_quantity: 1, flare_quantity: 3 } } },
    });

    await userEvent.click(
      within(panel).getByRole("button", {
        name: "Apply to every F/A-18C squadron",
      }),
    );
    await waitFor(() => expect(calls).toHaveLength(3));
    expect(calls[2]).toMatchObject({
      method: "POST",
      path: `${settingsPath}/apply-to-aircraft`,
    });
  });

  it("turns the F-14 JDAM targets off (#221)", async () => {
    const settingsPath = `${RADIOS_PATH}/cartridge/settings`;
    const calls = renderTab(
      {
        ...RADIOS,
        cartridge_settings: { ...CARTRIDGE, threats: true, jdam_targets: true },
      },
      null,
      { [settingsPath]: { body: RADIOS } },
    );
    const panel = await screen.findByRole("region", {
      name: "Data cartridge",
    });
    expect(panel).toHaveTextContent("aim points of the package target");
    await userEvent.click(
      within(panel).getByRole("switch", { name: "JDAM targets" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: settingsPath,
      body: { jdam_targets: false },
    });
  });

  it("offers no threat switch for an aircraft whose cartridge adds none", async () => {
    renderTab({ ...RADIOS, cartridge_settings: CARTRIDGE });
    const panel = await screen.findByRole("region", {
      name: "Data cartridge",
    });
    expect(
      within(panel).queryByRole("switch", {
        name: "Front lines and enemy air defenses",
      }),
    ).toBeNull();
  });

  it("says when the flight has no data cartridge", async () => {
    renderTab();
    const panel = await screen.findByRole("region", {
      name: "Data cartridge",
    });
    expect(panel).toHaveTextContent("comes with the mission");
    expect(within(panel).queryByRole("button")).toBeNull();
  });

  it("sets the flight frequency, with the modulations its radio has there", async () => {
    const calls = renderTab();
    const panel = await screen.findByRole("region", {
      name: "Flight frequency",
    });
    const input = within(panel).getByLabelText("MHz");
    expect(input).toHaveValue("251.25");
    expect(within(panel).getByLabelText("Modulation")).toBeVisible();
    expect(panel).toHaveTextContent("double booked");

    await userEvent.clear(input);
    await userEvent.type(input, "127.5");
    expect(within(panel).queryByLabelText("Modulation")).toBeNull();
    await userEvent.click(within(panel).getByRole("button", { name: "Set" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: `${RADIOS_PATH}/frequency`,
      body: { mhz: 127.5, modulation: "AM" },
    });
  });

  it("goes back to automatic", async () => {
    const calls = renderTab();
    const panel = await screen.findByRole("region", {
      name: "Flight frequency",
    });
    await userEvent.click(within(panel).getByRole("button", { name: "Auto" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toEqual({ mhz: null, modulation: null });
  });

  it("shows a refused frequency and restores the field", async () => {
    renderTab(RADIOS, null, {
      [`${RADIOS_PATH}/frequency`]: {
        status: 409,
        body: { detail: "The radio cannot tune 500 MHz." },
      },
    });
    const panel = await screen.findByRole("region", {
      name: "Flight frequency",
    });
    const input = within(panel).getByLabelText("MHz");
    await userEvent.clear(input);
    await userEvent.type(input, "500");
    await userEvent.click(within(panel).getByRole("button", { name: "Set" }));
    expect(
      await screen.findByText("The radio cannot tune 500 MHz."),
    ).toBeInTheDocument();
    await waitFor(() => expect(input).toHaveValue("251.25"));
  });

  it("sets the package frequency", async () => {
    const calls = renderTab();
    const panel = await screen.findByRole("region", {
      name: "Package frequency",
    });
    const input = within(panel).getByLabelText("MHz");
    await userEvent.type(input, "305");
    await userEvent.click(within(panel).getByRole("button", { name: "Set" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      path: `${RADIOS_PATH}/package-frequency`,
      body: { mhz: 305 },
    });
  });

  it("has a TACAN section for a tanker only", async () => {
    const first = renderTab();
    await screen.findByRole("region", { name: "Flight frequency" });
    expect(screen.queryByRole("region", { name: "TACAN" })).toBeNull();
    expect(first).toHaveLength(0);
  });

  it("sets the TACAN of a tanker", async () => {
    const calls = renderTab({
      ...RADIOS,
      has_tacan: true,
      datalink: undefined,
    });
    const panel = await screen.findByRole("region", { name: "TACAN" });
    await userEvent.type(within(panel).getByLabelText("Channel"), "74");
    await userEvent.type(within(panel).getByLabelText("Callsign"), "TKR");
    await userEvent.click(within(panel).getByRole("button", { name: "Set" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      path: `${RADIOS_PATH}/tacan`,
      body: { channel: 74, band: "Y", callsign: "TKR" },
    });
  });

  it("edits the datalink of each member", async () => {
    const calls = renderTab();
    const panel = await screen.findByRole("region", { name: "Link 16" });
    expect(within(panel).getByLabelText("STN of Maverick")).toHaveValue(
      "00017",
    );
    const input = within(panel).getByLabelText("STN of Aircraft 2");
    await userEvent.type(input, "21{Enter}");
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      path: `${RADIOS_PATH}/datalink/1`,
      body: { identifier: "STN_L16", value: "21" },
    });
  });

  it("has no datalink section without a datalink", async () => {
    renderTab({ ...RADIOS, datalink: undefined });
    await screen.findByRole("region", { name: "Flight frequency" });
    expect(screen.queryByRole("region", { name: "Link 16" })).toBeNull();
  });

  it("shows ICLS and Link 4 with the panel of the departure base", async () => {
    renderTab(RADIOS, ACTIONS);
    const panel = await screen.findByRole("region", {
      name: "Radios of Stennis",
    });
    expect(panel).toHaveTextContent("7 (STN)");
    expect(panel).toHaveTextContent("336 MHz");
    expect(
      within(panel).getByRole("button", { name: "Set radios" }),
    ).toBeVisible();
  });

  it("explains a flight that is gone", async () => {
    globalThis.fetch = async () =>
      new Response(
        JSON.stringify({ detail: "This flight is no longer planned." }),
        {
          status: 404,
          headers: { "Content-Type": "application/json" },
        },
      );
    const router = createMemoryRouter(
      [{ path: "/packages/:id", element: <FlightRadiosTab flightId="f-1" /> }],
      { initialEntries: ["/packages/pkg-1"] },
    );
    render(
      <Provider store={setupStore()}>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </Provider>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This flight is no longer planned.",
    );
  });
});

describe("transport entry", () => {
  const PKG = {
    id: "pkg-1",
    target: "Krymsk",
    transport_origin_id: "cp-1",
  } as PackageDetail;

  function renderEntry(pkg: PackageDetail) {
    const router = createMemoryRouter(
      [
        {
          path: "/",
          element: (
            <ToastProvider>
              <TransportEntry pkg={pkg} />
            </ToastProvider>
          ),
        },
      ],
      { initialEntries: ["/"] },
    );
    render(
      <Provider store={setupStore()}>
        <RouterProvider router={router} />
      </Provider>,
    );
  }

  it("opens the Transport mission of the base", async () => {
    recordFetch();
    renderEntry(PKG);
    await userEvent.click(
      screen.getByRole("button", { name: "Transport mission" }),
    );
    expect(
      await screen.findByText("New Transport mission from Krymsk"),
    ).toBeInTheDocument();
  });

  it("is absent elsewhere", () => {
    recordFetch();
    renderEntry({ ...PKG, transport_origin_id: undefined });
    expect(screen.queryByRole("button")).toBeNull();
  });
});

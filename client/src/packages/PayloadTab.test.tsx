import type { FlightPayload } from "../api/liberationApi";
import { setupStore } from "../app/store";
import { Call, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { PayloadTab } from "./PayloadTab";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";

afterEach(restoreFetch);

const URL = "/packages/pkg-1/flights/f-1/payload";

const AIM9 = { clsid: "aim9", name: "AIM-9M" };
const AIM120 = { clsid: "aim120", name: "AIM-120C" };

const member = (index: number, overrides: object = {}) => ({
  index,
  pilot: `Pilot ${index + 1}`,
  is_player: false,
  loadout: "Retribution SEAD",
  custom: false,
  pylons: [
    { number: 1, weapon: AIM9, settings: [] },
    { number: 2, settings: [], replaced_weapon: "AGM-88C" },
  ],
  weapon_laser_codes: [],
  liveries: [
    {
      label: "Viper",
      livery_id: "viper",
      use_livery_set: false,
      selected: true,
    },
    {
      label: "Falcon",
      livery_id: "falcon",
      use_livery_set: false,
      selected: false,
    },
  ],
  properties: { hmd: 1, nvg: false },
  ...overrides,
});

const PAYLOAD: FlightPayload = {
  aircraft: "F-16CM",
  fuel: 3000,
  fuel_max: 3249,
  same_loadout: true,
  same_livery: true,
  restrict_weapons_by_date: true,
  date: "2000-05-17",
  loadouts: ["Retribution CAP", "Retribution SEAD"],
  pylons: [
    { number: 1, weapons: [AIM120, AIM9] },
    { number: 2, weapons: [AIM9] },
  ],
  properties: [
    {
      id: "hmd",
      label: "Helmet",
      control: "comboList",
      section: "Cockpit",
      options: [
        { id: 0, label: "Not installed" },
        { id: 1, label: "JHMCS" },
      ],
    },
    {
      id: "nvg",
      label: "NVG",
      control: "checkbox",
      section: "Cockpit",
      options: [],
    },
  ],
  members: [member(0), member(1)],
};

const CUSTOM: FlightPayload = {
  ...PAYLOAD,
  members: [
    member(0, { custom: true, loadout: "Custom" }),
    member(1, { custom: true, loadout: "Custom" }),
  ],
};

function renderTab(payload: FlightPayload = PAYLOAD) {
  const calls = recordFetch(200, payload, { [URL]: payload });
  render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <PayloadTab packageId="pkg-1" flightId="f-1" />
      </ToastProvider>
    </Provider>,
  );
  return calls;
}

function bodyOf(calls: Call[], path: string) {
  return calls.find((call) => call.path === path)?.body;
}

test("a named loadout shows its pylons, read-only, with what the date replaced", async () => {
  renderTab();

  const pylon = await screen.findByLabelText("Pylon 1");
  expect(pylon).toBeDisabled();
  expect(pylon).toHaveValue("aim9");
  expect(screen.getByLabelText("Pylon 2")).toHaveValue("");
  expect(screen.getByLabelText("Named loadout")).toHaveValue(
    "Retribution SEAD",
  );
  expect(screen.getByText(/Replaces AGM-88C/)).toBeInTheDocument();
  expect(screen.getByText(/available on 2000-05-17/)).toBeInTheDocument();
});

test("a pylon offers only what the engine lists", async () => {
  renderTab(CUSTOM);

  const pylon = await screen.findByLabelText("Pylon 2");
  const names = Array.from(pylon.querySelectorAll("option")).map(
    (option) => option.textContent,
  );
  expect(names).toEqual(["None", "AIM-9M"]);
});

test("changing a pylon sends the weapon's CLSID", async () => {
  const user = userEvent.setup();
  const calls = renderTab(CUSTOM);

  const pylon = await screen.findByLabelText("Pylon 1");
  expect(pylon).toBeEnabled();
  await user.selectOptions(pylon, "aim120");

  await waitFor(() =>
    expect(bodyOf(calls, `${URL}/members/0/pylons/1`)).toEqual({
      clsid: "aim120",
    }),
  );
  expect(screen.queryByText("Save payload")).toBeInTheDocument();
});

test("the custom switch and the named list act on the selected member", async () => {
  const user = userEvent.setup();
  const calls = renderTab();

  await user.click(
    await screen.findByRole("switch", { name: "Custom loadout" }),
  );
  await waitFor(() =>
    expect(bodyOf(calls, `${URL}/members/0/custom`)).toEqual({ custom: true }),
  );

  await user.selectOptions(
    screen.getByLabelText("Named loadout"),
    "Retribution CAP",
  );
  await waitFor(() =>
    expect(bodyOf(calls, `${URL}/members/0/loadout`)).toEqual({
      name: "Retribution CAP",
    }),
  );
});

test("other members follow the first while the loadout is shared", async () => {
  const user = userEvent.setup();
  renderTab();

  await user.click(await screen.findByRole("tab", { name: /Pilot 2/ }));

  expect(screen.getByLabelText("Named loadout")).toBeDisabled();
  expect(screen.getByRole("switch", { name: "Custom loadout" })).toBeDisabled();
  expect(screen.getByText(/share the loadout of member 1/)).toBeInTheDocument();
});

test("separate loadouts warn about AI flights and unlock every member", async () => {
  const user = userEvent.setup();
  renderTab({ ...PAYLOAD, same_loadout: false });

  expect(await screen.findByText(/AI flights should use/)).toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: /Pilot 2/ }));
  expect(screen.getByLabelText("Named loadout")).toBeEnabled();
});

test("an AI member has no laser presets, a player has", async () => {
  const code = { code: 1688, label: "JTAC Front (1688)" };
  renderTab({
    ...PAYLOAD,
    members: [
      member(0, {
        is_player: true,
        weapon_laser_codes: [{ label: "Default (1688)" }, code],
      }),
      member(1),
    ],
  });

  expect(
    await screen.findByLabelText("Preset laser code for weapons"),
  ).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: /Pilot 2/ }));
  expect(
    screen.queryByLabelText("Preset laser code for weapons"),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/AI does not use laser codes/)).toBeInTheDocument();
});

test("options send the engine's own value", async () => {
  const user = userEvent.setup();
  const calls = renderTab();

  await user.selectOptions(
    await screen.findByLabelText("Helmet"),
    "Not installed",
  );

  await waitFor(() =>
    expect(bodyOf(calls, `${URL}/members/0/properties`)).toEqual({
      id: "hmd",
      value: 0,
    }),
  );
});

test("a refused command shows the engine's message", async () => {
  const user = userEvent.setup();
  const calls = recordFetch(
    409,
    { detail: "Pylon 1 cannot carry this." },
    {
      [URL]: CUSTOM,
    },
  );
  render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <PayloadTab packageId="pkg-1" flightId="f-1" />
      </ToastProvider>
    </Provider>,
  );

  await user.selectOptions(await screen.findByLabelText("Pylon 1"), "aim120");

  expect(
    await screen.findByText("Pylon 1 cannot carry this."),
  ).toBeInTheDocument();
  expect(calls.length).toBeGreaterThan(0);
});

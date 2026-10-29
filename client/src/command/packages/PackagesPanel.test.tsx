import { GameUpdateEvents, packagesChanged } from "../../api/eventstream";
import { selectFlight } from "../../api/flightsSlice";
import { Package } from "../../api/liberationApi";
import { setupStore } from "../../app/store";
import { recordFetch, restoreFetch } from "../../shell/testing";
import { ToastProvider } from "../../ui";
import {
  flightSummary,
  formatTot,
  matchesFilter,
  missingPilotsLabel,
} from "./packageFormat";
import { PackagesPanel } from "./PackagesPanel";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";

afterEach(restoreFetch);

function flight(id: string, overrides: Record<string, unknown> = {}) {
  return {
    id,
    task: "DEAD",
    aircraft: "F-16CM",
    count: 4,
    clients: 0,
    missing_pilots: 0,
    squadron: "VF-1",
    departure: "Krymsk",
    ...overrides,
  };
}

const DEAD: Package = {
  id: "pkg-dead",
  blue: true,
  task: "DEAD",
  description: "DEAD",
  target: "SA-11 Krasnodar East",
  tot: "2022-05-17T07:12:00",
  auto_asap: false,
  flights: [
    flight("f-dead", { clients: 1 }),
    flight("f-escort", { task: "SEAD Escort", aircraft: "F/A-18C", count: 2 }),
  ],
  missing_pilots: 0,
};

const STRIKE: Package = {
  id: "pkg-strike",
  blue: true,
  task: "Strike",
  description: "Strike",
  target: "Ammo depot Krasnodar",
  tot: "2022-05-17T07:50:00",
  auto_asap: false,
  flights: [
    flight("f-strike", {
      task: "Strike",
      aircraft: "Su-24M",
      missing_pilots: 1,
    }),
  ],
  missing_pilots: 1,
};

const ENEMY: Package = {
  id: "pkg-red",
  blue: false,
  task: "BARCAP",
  description: "BARCAP",
  target: "Maykop",
  auto_asap: true,
  flights: [flight("f-red", { task: "BARCAP", aircraft: "MiG-29S", count: 2 })],
  missing_pilots: 0,
};

function renderPanel(onNewPackage?: () => void) {
  const store = setupStore();
  const calls = recordFetch(204, undefined, {
    "/packages/": [DEAD, STRIKE, ENEMY],
  });
  render(
    <Provider store={store}>
      <ToastProvider>
        <PackagesPanel onNewPackage={onNewPackage} />
      </ToastProvider>
    </Provider>,
  );
  return { store, calls };
}

const card = (name: RegExp) => screen.getByRole("button", { name });

describe("packages panel", () => {
  it("shows the friendly packages as cards", async () => {
    renderPanel();
    expect(
      await screen.findByRole("tab", { name: "Packages · 2" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Enemy ATO · 1" })).toBeVisible();
    const dead = card(/SA-11 Krasnodar East/);
    expect(dead).toHaveTextContent("DEAD");
    expect(dead).toHaveTextContent("TOT 07:12");
    expect(dead).toHaveTextContent("4 × F-16CM · Player");
    expect(dead).toHaveTextContent("2 × F/A-18C");
    expect(card(/Ammo depot/)).toHaveTextContent("Missing 1 pilot");
    expect(screen.queryByText("Maykop")).not.toBeInTheDocument();
  });

  it("switches to the enemy ATO", async () => {
    renderPanel();
    await userEvent.click(
      await screen.findByRole("tab", { name: "Enemy ATO · 1" }),
    );
    expect(card(/Maykop/)).toHaveTextContent("2 × MiG-29S");
    expect(screen.queryByText("SA-11 Krasnodar East")).not.toBeInTheDocument();
  });

  it("filters the packages", async () => {
    renderPanel();
    await screen.findByText("SA-11 Krasnodar East");
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Filter packages" }),
      "su-24",
    );
    expect(screen.queryByText("SA-11 Krasnodar East")).not.toBeInTheDocument();
    expect(screen.getByText("Ammo depot Krasnodar")).toBeInTheDocument();
    await userEvent.clear(screen.getByRole("searchbox"));
    await userEvent.type(screen.getByRole("searchbox"), "nothing like it");
    expect(screen.getByText("No package matches the filter.")).toBeVisible();
  });

  it("selecting a card selects its first flight on the map", async () => {
    const { store } = renderPanel();
    await userEvent.click(await screen.findByText("Ammo depot Krasnodar"));
    expect(store.getState().flights.selected).toBe("f-strike");
    expect(card(/Ammo depot/)).toHaveAttribute("aria-pressed", "true");
  });

  it("selecting a flight of the card selects it on the map", async () => {
    const { store } = renderPanel();
    await userEvent.click(await screen.findByText("SA-11 Krasnodar East"));
    const flights = screen.getByRole("list", { name: "Flights" });
    await userEvent.click(
      within(flights).getByRole("button", { name: /SEAD Escort/ }),
    );
    expect(store.getState().flights.selected).toBe("f-escort");
    expect(card(/SA-11/)).toHaveAttribute("aria-pressed", "true");
  });

  it("follows a flight selected on the map, in either ATO", async () => {
    const { store } = renderPanel();
    await screen.findByText("SA-11 Krasnodar East");
    act(() => {
      store.dispatch(selectFlight("f-escort"));
    });
    expect(card(/SA-11/)).toHaveAttribute("aria-pressed", "true");
    act(() => {
      store.dispatch(selectFlight("f-red"));
    });
    expect(
      await screen.findByRole("tab", { name: "Enemy ATO · 1" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(card(/Maykop/)).toHaveAttribute("aria-pressed", "true");
  });

  it("deletes the selected package through the API", async () => {
    const { calls } = renderPanel();
    await userEvent.click(await screen.findByText("SA-11 Krasnodar East"));
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "DELETE",
      path: "/packages/pkg-dead",
    });
  });

  it("edits a friendly package in the package editor", async () => {
    const { calls } = renderPanel();
    await userEvent.click(await screen.findByText("SA-11 Krasnodar East"));
    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe("/qt/edit-package/flight/f-dead");
  });

  it("+ New explains how to plan a package", async () => {
    let asked = 0;
    renderPanel(() => asked++);
    await userEvent.click(screen.getByRole("button", { name: "+ New" }));
    expect(asked).toBe(1);
  });
});

describe("package formatting", () => {
  it("formats the TOT, the flights and the warnings", () => {
    expect(formatTot("2022-05-17T07:12:00")).toBe("07:12");
    expect(formatTot(undefined)).toBeUndefined();
    expect(flightSummary(flight("f", { clients: 2 }))).toBe(
      "4 × F-16CM · 2 players",
    );
    expect(missingPilotsLabel(1)).toBe("Missing 1 pilot");
    expect(missingPilotsLabel(3)).toBe("Missing 3 pilots");
  });

  it("filters on target, task and aircraft", () => {
    expect(matchesFilter(DEAD, "")).toBe(true);
    expect(matchesFilter(DEAD, "krasnodar")).toBe(true);
    expect(matchesFilter(DEAD, "sead")).toBe(true);
    expect(matchesFilter(DEAD, "F/A-18")).toBe(true);
    expect(matchesFilter(DEAD, "MiG")).toBe(false);
  });

  it("refetches the packages on flight and turn events", () => {
    const quiet = {
      new_turn: false,
      game_unloaded: false,
      reset_on_map_center: null,
      new_flights: [],
      updated_flights: [],
      deleted_flights: [],
    } as unknown as GameUpdateEvents;
    expect(packagesChanged(quiet)).toBe(false);
    expect(packagesChanged({ ...quiet, new_turn: true })).toBe(true);
    expect(packagesChanged({ ...quiet, deleted_flights: ["f"] })).toBe(true);
  });
});

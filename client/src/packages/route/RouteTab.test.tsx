// Must come before leaflet: lets Leaflet draw the path of the route.
import "../../testutils/leafletSvg";
import { FlightRoute, FlightRouteWaypoint } from "../../api/liberationApi";
import { setupStore } from "../../app/store";
import { recordFetch, restoreFetch } from "../../shell/testing";
import { ToastProvider } from "../../ui";
import { RouteTab } from "./RouteTab";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { vi } from "vitest";

// The basemap loads tiles and theatre data: no use to the route.
vi.mock("../../components/basemaps", () => ({ default: () => null }));

afterEach(restoreFetch);

const waypoint = (
  index: number,
  overrides: Partial<FlightRouteWaypoint> = {},
): FlightRouteWaypoint => ({
  index,
  name: `WP${index}`,
  type: "NAV",
  position: { lat: 32 + index / 10, lng: 35 },
  altitude_ft: 20000,
  altitude_reference: "MSL",
  time: `2010-06-01T16:0${index}:30`,
  time_kind: "estimated",
  is_tot: false,
  min_fuel_lb: 5000 - index * 100,
  is_movable: true,
  include_in_path: true,
  can_delete: true,
  delete_degrades: false,
  can_insert_after: true,
  threat: undefined,
  ...overrides,
});

const ROUTE: FlightRoute = {
  flight_id: "f-1",
  blue: true,
  recreate_tasks: ["Strike", "SEAD"],
  is_custom: false,
  bulk_altitude_ft: 20000,
  min_altitude_ft: 0,
  max_altitude_ft: 40000,
  waypoints: [
    waypoint(0, {
      name: "Take off",
      type: "TAKEOFF",
      altitude_ft: 0,
      altitude_reference: "AGL",
      time_kind: "takeoff",
      is_movable: false,
      can_delete: false,
      can_insert_after: true,
    }),
    waypoint(1, { time_kind: "depart", can_insert_after: false }),
    waypoint(2, {
      name: "Target",
      type: "TARGET_POINT",
      time_kind: "tot",
      is_tot: true,
      is_movable: false,
      delete_degrades: true,
      threat: "Waypoint 2 is inside the threat ring of SA-11.",
    }),
    waypoint(3, {
      name: "Bullseye",
      type: "BULLSEYE",
      time: undefined,
      time_kind: undefined,
      min_fuel_lb: undefined,
      include_in_path: false,
    }),
  ],
};

const PATH = "/flights/f-1/route";

function renderTab(route: FlightRoute = ROUTE) {
  const calls = recordFetch(200, route, { [PATH]: route });
  const view = render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <RouteTab flightId="f-1" />
      </ToastProvider>
    </Provider>,
  );
  return { calls, ...view };
}

const row = async (name: string) =>
  (await screen.findByRole("textbox", { name })).closest("tr") as HTMLElement;

describe("RouteTab", () => {
  it("shows altitude, time and fuel, and only what is known", async () => {
    renderTab();
    const target = within(await row("Name of waypoint 2"));
    expect(target.getByText("16:02:30")).toHaveClass(/tot/);
    expect(target.getByText("4,800")).toBeInTheDocument();
    expect(
      target.getByRole("spinbutton", { name: "Altitude of waypoint 2" }),
    ).toHaveValue("20000");

    const hold = within(await row("Name of waypoint 1"));
    expect(hold.getByText("Depart 16:01:30")).toBeInTheDocument();

    const bullseye = within(await row("Name of waypoint 3"));
    expect(bullseye.getAllByText("—")).toHaveLength(2);
  });

  it("warns about the waypoints inside a threat zone", async () => {
    renderTab();
    const warnings = await screen.findByRole("list", {
      name: "Threat warnings",
    });
    expect(warnings).toHaveTextContent(
      "Waypoint 2 is inside the threat ring of SA-11.",
    );
  });

  it("draws the flown path, and only movable waypoints can be dragged", async () => {
    const { container } = renderTab();
    await screen.findByRole("textbox", { name: "Name of waypoint 0" });
    await waitFor(() =>
      expect(container.querySelectorAll(".leaflet-marker-icon")).toHaveLength(
        3,
      ),
    );
    const markers = Array.from(
      container.querySelectorAll(".leaflet-marker-icon"),
    );
    // Bullseye is listed but not flown.
    expect(markers.map((m) => m.textContent)).toEqual(["0", "1", "2"]);
    expect(markers.map((m) => m.className.includes("draggable"))).toEqual([
      false,
      true,
      false,
    ]);
    expect(container.querySelector("path.leaflet-interactive, path")).not.toBeNull();
  });

  it("deletes a waypoint at once when the plan stays the same", async () => {
    const { calls } = renderTab();
    await userEvent.click(
      await screen.findByRole("button", { name: "Delete waypoint 1" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].method).toBe("DELETE");
    expect(calls[0].path).toBe(`${PATH}/waypoints/1`);
  });

  it("asks before a change that makes the plan custom", async () => {
    const { calls } = renderTab();
    await userEvent.click(
      await screen.findByRole("button", { name: "Delete waypoint 2" }),
    );
    expect(calls).toHaveLength(0);
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].method).toBe("DELETE");
    expect(calls[0].path).toBe(`${PATH}/waypoints/2`);
  });

  it("the first waypoint has no delete button", async () => {
    renderTab();
    await screen.findByRole("textbox", { name: "Name of waypoint 0" });
    expect(
      screen.queryByRole("button", { name: "Delete waypoint 0" }),
    ).toBeNull();
  });

  it("inserts a NAV point after the selected waypoint, where the engine allows", async () => {
    const { calls } = renderTab();
    const insert = await screen.findByRole("button", {
      name: "Insert NAV point",
    });
    expect(insert).toBeDisabled();

    await userEvent.click(await row("Name of waypoint 1"));
    expect(insert).toBeDisabled();

    await userEvent.click(await row("Name of waypoint 2"));
    expect(insert).toBeEnabled();
    await userEvent.click(insert);
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe(`${PATH}/waypoints/2/nav`);
  });

  it("sends a typed altitude and a new name", async () => {
    const { calls } = renderTab();
    const altitude = await screen.findByRole("spinbutton", {
      name: "Altitude of waypoint 1",
    });
    await userEvent.clear(altitude);
    await userEvent.type(altitude, "25000{Enter}");
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe(`${PATH}/waypoints/1/altitude`);
    expect(calls[0].body).toEqual({ altitude_ft: 25000 });

    const name = screen.getByRole("textbox", { name: "Name of waypoint 1" });
    await userEvent.clear(name);
    await userEvent.type(name, "Hold on{Enter}");
    await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls[1].path).toBe(`${PATH}/waypoints/1/name`);
    expect(calls[1].body).toEqual({ name: "Hold on" });
  });

  it("recreates the route as the chosen task after asking", async () => {
    const { calls } = renderTab();
    await userEvent.selectOptions(
      await screen.findByRole("combobox", {
        name: "Task of the recreated route",
      }),
      "SEAD",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Recreate route" }),
    );
    expect(calls).toHaveLength(0);
    await userEvent.click(screen.getByRole("button", { name: "Recreate" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe(`${PATH}/recreate`);
    expect(calls[0].body).toEqual({ task: "SEAD" });
  });

  it("applies one altitude to the en-route waypoints", async () => {
    const { calls } = renderTab();
    await userEvent.click(
      await screen.findByRole("button", { name: "Apply to all" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].method).toBe("PUT");
    expect(calls[0].path).toBe(`${PATH}/altitude`);
    expect(calls[0].body).toEqual({ altitude_ft: 20000 });
  });

  it("shows a refusal of the engine as a toast", async () => {
    restoreFetch();
    const calls = recordFetch(
      409,
      { detail: "A NAV point cannot follow this waypoint." },
      { [PATH]: ROUTE },
    );
    render(
      <Provider store={setupStore()}>
        <ToastProvider>
          <RouteTab flightId="f-1" />
        </ToastProvider>
      </Provider>,
    );
    await userEvent.click(await row("Name of waypoint 2"));
    await userEvent.click(
      screen.getByRole("button", { name: "Insert NAV point" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(
      await screen.findByText("A NAV point cannot follow this waypoint."),
    ).toBeInTheDocument();
  });
});

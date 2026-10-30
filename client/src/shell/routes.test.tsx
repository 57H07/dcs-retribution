import { recordFetch, renderShell, restoreFetch } from "./testing";
import { waitFor } from "@testing-library/react";

afterEach(restoreFetch);

describe("web shell routes", () => {
  it("shows the command view (map) and the app bar on /", () => {
    recordFetch();
    const { router, container } = renderShell("/");
    expect(router.state.location.pathname).toBe("/");
    expect(container.querySelector(".leaflet-container")).not.toBeNull();
    expect(container.querySelector("header")).not.toBeNull();
  });

  it.each([
    ["/air-wing", "/qt/dialogs/air-wing"],
    ["/new-game", "/native/new-game"],
    ["/debrief", "/qt/dialogs/debriefing"],
    ["/packages/flight-7", "/qt/edit-package/flight/flight-7"],
  ])(
    "%s opens its Qt screen once and returns to the command view",
    async (path, qtRoute) => {
      const calls = recordFetch();
      const { router } = renderShell(path);
      await waitFor(() => expect(calls).toHaveLength(1));
      expect(calls[0]).toMatchObject({ method: "POST", path: qtRoute });
      expect(router.state.location.pathname).toBe("/");
    },
  );

  it.each(["/bases/cp-1", "/bases/cp-1/intel"])(
    "shows the web base screen on %s, without opening Qt",
    async (path) => {
      const calls = recordFetch();
      const { router, findByText } = renderShell(path);
      expect(await findByText("No campaign loaded.")).toBeInTheDocument();
      expect(router.state.location.pathname).toBe(path);
      expect(calls).toHaveLength(0);
    },
  );

  it("shows the web settings screen on /settings, without opening Qt", async () => {
    const calls = recordFetch(200, { pages: [] });
    const { router, findByRole } = renderShell("/settings");
    expect(
      await findByRole("heading", { level: 1, name: "Settings" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/settings");
    expect(calls.some((call) => call.path.startsWith("/qt/"))).toBe(false);
  });

  it.each(["/reports", "/reports/finances"])(
    "shows the web reports screen on %s, without opening Qt",
    async (path) => {
      const calls = recordFetch();
      const { router, findByRole } = renderShell(path);
      expect(
        await findByRole("heading", { level: 1, name: "Reports" }),
      ).toBeInTheDocument();
      expect(router.state.location.pathname).toBe(path);
      expect(calls).toHaveLength(0);
    },
  );

  it("sends an unknown reports tab to the first tab", async () => {
    recordFetch();
    const { router } = renderShell("/reports/nowhere");
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/reports"),
    );
  });

  it("sends unknown paths back to the command view", async () => {
    const calls = recordFetch();
    const { router } = renderShell("/nowhere");
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(calls).toHaveLength(0);
  });
});

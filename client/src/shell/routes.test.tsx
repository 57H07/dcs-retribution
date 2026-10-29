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
    ["/settings", "/qt/dialogs/settings"],
    ["/debrief", "/qt/dialogs/debriefing"],
    ["/reports", "/qt/dialogs/reports"],
    ["/bases/cp-1", "/qt/info/control-point/cp-1"],
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

  it("sends unknown paths back to the command view", async () => {
    const calls = recordFetch();
    const { router } = renderShell("/nowhere");
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(calls).toHaveLength(0);
  });
});

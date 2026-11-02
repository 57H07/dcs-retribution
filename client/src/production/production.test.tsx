import { Production, ProductionItem } from "../api/liberationApi";
import { recordFetch, renderShell, restoreFetch } from "../shell/testing";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

afterEach(restoreFetch);

const ORDER: ProductionItem = {
  id: "aircraft-order:s1",
  group: "aircraft-orders",
  label: "4 × F-16CM",
  detail: "VFA-25 · Ramat David",
  turns: 1,
  base_id: "b1",
  action: { label: "Cancel", cost: -96, affordable: true },
};

const MAINTENANCE: ProductionItem = {
  id: "maintenance:s2",
  group: "maintenance",
  label: "2 × F-4E",
  detail: "Sqn 69 · Ramat David",
  turns: 2,
  base_id: "b1",
};

const RUNWAY: ProductionItem = {
  id: "repair:b1:runway",
  group: "damage",
  label: "Runway",
  detail: "Ramat David · 4 turns once started",
  base_id: "b1",
  action: { label: "Repair", cost: 100, affordable: true },
};

const SHIP: ProductionItem = {
  id: "site-damage:t1",
  group: "ships",
  label: "CVN-74: 2 units destroyed",
  detail: "CVN-74",
  base_id: "b2",
  tgo_id: "t1",
  action: { label: "Repair", cost: 2400, affordable: false },
};

const FULL: Production = {
  in_progress: [ORDER, MAINTENANCE],
  to_handle: [RUNWAY, SHIP],
  next_end_turns: 1,
  budget: 2000,
};

const EMPTY: Production = {
  in_progress: [],
  to_handle: [],
  budget: 2000,
};

function serve(production: Production, status = 200, answer: unknown = FULL) {
  return recordFetch(status, answer, { "/production/": production });
}

describe("Production & repairs screen", () => {
  it("lists what is in progress and what waits, by group", async () => {
    serve(FULL);
    renderShell("/production");
    const running = await screen.findByRole("region", { name: "In progress" });
    expect(
      within(running).getByRole("list", { name: "Aircraft on order" }),
    ).toHaveTextContent("4 × F-16CM");
    expect(within(running).getByText("2 turns")).toBeInTheDocument();
    const waiting = screen.getByRole("region", { name: "To handle" });
    expect(within(waiting).getByText("Runway")).toBeInTheDocument();
  });

  it("runs an action through the engine", async () => {
    const calls = serve(FULL);
    renderShell("/production");
    await userEvent.click(
      await screen.findByRole("button", { name: /^Cancel/ }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/production/items/aircraft-order:s1/action",
    });
  });

  it("says why an action is refused", async () => {
    serve(FULL, 409, { detail: "Not today." });
    renderShell("/production");
    await userEvent.click(
      await screen.findByRole("button", { name: /^Repair · \$100/ }),
    );
    expect(await screen.findByText("Not today.")).toBeInTheDocument();
  });

  it("greys out what the budget cannot pay", async () => {
    serve(FULL);
    renderShell("/production");
    expect(
      await screen.findByRole("button", { name: /^Repair · \$2/ }),
    ).toBeDisabled();
  });

  it("opens the base or site of a line", async () => {
    serve(FULL);
    const { router } = renderShell("/production");
    await userEvent.click(
      await screen.findByRole("button", { name: /CVN-74: 2 units/ }),
    );
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/tgos/t1"),
    );
  });

  it("says when nothing is under way", async () => {
    serve(EMPTY);
    renderShell("/production");
    expect(
      await screen.findByText("Nothing in progress, nothing waiting."),
    ).toBeInTheDocument();
  });
});

describe("Production badge", () => {
  it("shows the count and the next end, and opens the screen", async () => {
    serve(FULL);
    const { router } = renderShell("/");
    const badge = await screen.findByRole("button", {
      name: "Production and repairs: 2 in progress, next ends in 1 turn",
    });
    expect(badge).toHaveTextContent("2 · 1 turn");
    await userEvent.click(badge);
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/production"),
    );
  });

  it("stays discreet when nothing is under way", async () => {
    serve(EMPTY);
    renderShell("/");
    const badge = await screen.findByRole("button", {
      name: "Production and repairs: 0 in progress",
    });
    expect(badge).not.toHaveAttribute("data-active");
  });

  it("is hidden without a campaign", async () => {
    recordFetch();
    renderShell("/");
    await screen.findByRole("navigation", { name: "Campaign screens" });
    expect(
      screen.queryByRole("button", { name: /Production and repairs/ }),
    ).toBeNull();
  });
});

import type {
  CampaignObjective,
  CampaignObjectives,
} from "../api/liberationApi";
import { setupStore } from "../app/store";
import { recordFetch, restoreFetch } from "../shell/testing";
import { ObjectivesScreen } from "./ObjectivesScreen";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

function objective(
  overrides: Partial<CampaignObjective> = {},
): CampaignObjective {
  return {
    title: "Destroy the enemy IADS",
    kind: "destroy",
    target: "the enemy IADS",
    state: "In progress",
    deadline: 10,
    turns_left: 3,
    done: 2,
    total: 5,
    reward: "+500 budget",
    expected: "+500 budget",
    granted: "",
    resolved_turn: undefined,
    targets: [],
    ...overrides,
  };
}

function renderObjectives(data: CampaignObjectives | null) {
  recordFetch(204, undefined, { "/objectives": data });
  const router = createMemoryRouter(
    [
      { path: "/", element: null },
      { path: "/objectives", element: <ObjectivesScreen /> },
    ],
    { initialEntries: ["/objectives"] },
  );
  const store = setupStore();
  render(
    <Provider store={store}>
      <RouterProvider router={router} />
    </Provider>,
  );
  return { router, store };
}

describe("objectives screen", () => {
  it("shows each objective with its state, progress and reward", async () => {
    renderObjectives({
      turn: 8,
      objectives: [
        objective(),
        objective({
          title: "Capture Kutaisi",
          kind: "capture",
          state: "Met",
          deadline: 6,
          turns_left: undefined,
          done: undefined,
          total: undefined,
          reward: "+500 budget, +80 income per turn",
          expected: "",
          granted: "+400 budget, +50 income per turn",
          resolved_turn: 5,
        }),
        objective({
          title: "Hold Batumi",
          kind: "hold",
          state: "Missed",
          turns_left: undefined,
          done: undefined,
          total: undefined,
          resolved_turn: 4,
        }),
      ],
    });

    const iads = within(
      await screen.findByRole("article", { name: "Destroy the enemy IADS" }),
    );
    expect(
      iads.getByText("2 / 5 destroyed · by turn 10 · 3 turns left"),
    ).toBeVisible();
    expect(iads.getByText("Reward: +500 budget")).toBeVisible();
    // The settings grant all of it: no need to say so.
    expect(iads.queryByText(/With your settings/)).not.toBeInTheDocument();

    const kutaisi = within(
      screen.getByRole("article", { name: "Capture Kutaisi" }),
    );
    expect(kutaisi.getByText("Met on turn 5")).toHaveAttribute(
      "data-tone",
      "good",
    );
    expect(
      kutaisi.getByText("Reward granted: +400 budget, +50 income per turn"),
    ).toBeVisible();

    const batumi = within(screen.getByRole("article", { name: "Hold Batumi" }));
    expect(batumi.getByText("Missed on turn 4")).toHaveAttribute(
      "data-tone",
      "bad",
    );
    expect(batumi.getByText("until turn 10")).toBeVisible();
  });

  it("tells what the player's settings would grant today", async () => {
    renderObjectives({
      turn: 3,
      objectives: [
        objective({ title: "Capture Kutaisi", expected: "+200 budget" }),
        objective({ title: "Hold Batumi", expected: "" }),
      ],
    });

    const kutaisi = within(
      await screen.findByRole("article", { name: "Capture Kutaisi" }),
    );
    expect(
      kutaisi.getByText("With your settings today: +200 budget"),
    ).toBeVisible();
    const batumi = within(screen.getByRole("article", { name: "Hold Batumi" }));
    expect(
      batumi.getByText("With your settings today: no reward"),
    ).toBeVisible();
  });

  it("centres the map on what is left of an objective", async () => {
    const { router, store } = renderObjectives({
      turn: 3,
      objectives: [
        objective({
          targets: [
            {
              id: "sam",
              name: "SA-6",
              position: { lat: 33, lng: 36 },
              remaining: false,
            },
            {
              id: "ewr",
              name: "EWR",
              position: { lat: 33.2, lng: 35.8 },
              remaining: true,
            },
          ],
        }),
        objective({ title: "Hold Batumi", state: "Missed" }),
      ],
    });

    const iads = within(
      await screen.findByRole("article", { name: "Destroy the enemy IADS" }),
    );
    expect(
      within(screen.getByRole("article", { name: "Hold Batumi" })).queryByRole(
        "button",
        { name: "Show on map" },
      ),
    ).not.toBeInTheDocument();
    await userEvent.click(iads.getByRole("button", { name: "Show on map" }));

    expect(store.getState().map.center).toEqual({ lat: 33.2, lng: 35.8 });
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
  });

  it("explains when the campaign has none", async () => {
    renderObjectives({ turn: 1, objectives: [] });
    expect(
      await screen.findByText(
        "This campaign has no objectives: its makers can set some in its YAML file.",
      ),
    ).toBeVisible();
  });
});

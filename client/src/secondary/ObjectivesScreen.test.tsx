import type {
  CampaignObjective,
  CampaignObjectives,
} from "../api/liberationApi";
import { setupStore } from "../app/store";
import { recordFetch, restoreFetch } from "../shell/testing";
import { ObjectivesScreen } from "./ObjectivesScreen";
import { render, screen, within } from "@testing-library/react";
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
    granted: "",
    resolved_turn: undefined,
    ...overrides,
  };
}

function renderObjectives(data: CampaignObjectives | null) {
  recordFetch(204, undefined, { "/objectives": data });
  const router = createMemoryRouter(
    [{ path: "/objectives", element: <ObjectivesScreen /> }],
    { initialEntries: ["/objectives"] },
  );
  render(
    <Provider store={setupStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
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

  it("explains when the campaign has none", async () => {
    renderObjectives({ turn: 1, objectives: [] });
    expect(
      await screen.findByText(
        "This campaign has no objectives: its makers can set some in its YAML file.",
      ),
    ).toBeVisible();
  });
});

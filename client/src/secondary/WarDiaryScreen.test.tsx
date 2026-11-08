import type { WarDiary, WarDiaryEntry } from "../api/liberationApi";
import { setupStore } from "../app/store";
import { Answer, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { WarDiaryScreen } from "./WarDiaryScreen";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const DIARY_PATH = "/war-diary";
const EXPORT_PATH = "/war-diary/export";

function entry(overrides: Partial<WarDiaryEntry> = {}): WarDiaryEntry {
  return {
    turn: 4,
    date: "17 May 2022",
    weather: "Partly Cloudy, no rain, no fog",
    verdict: "Tactical victory",
    verdict_tone: "good",
    summary: "Krymsk taken, 1 aircraft lost, Lt. Moroz rescued",
    air_kills_friendly: 2,
    air_kills_enemy: 1,
    ground_kills_friendly: 3,
    ground_kills_enemy: 0,
    bases: [{ id: "cp-1", name: "Krymsk", taken: true }],
    fronts: [{ name: "Krymsk – Krasnodar", moved_km: 2.4 }],
    packages: [
      {
        task: "Strike",
        target: "Ammo depot",
        flights: ["Uzi 1"],
        lost: 1,
        aircraft: 2,
        result: "Target 40%",
        tone: "mixed",
      },
    ],
    friendly_losses: [{ name: "F/A-18C", count: 1 }],
    enemy_losses: [{ name: "MiG-29A", count: 2 }],
    pilots: [
      {
        pilot_id: "p-1",
        name: "Lt. Moroz",
        squadron: "VF-11",
        aircraft: "F/A-18C",
        fate: "Rescued",
      },
      {
        name: "Lt. Petrenko",
        squadron: "VF-11",
        aircraft: "F/A-18C",
        fate: "Killed in action",
      },
    ],
    awards: [
      {
        pilot_id: "p-1",
        pilot: "Lt. Moroz",
        kind: "Rank",
        name: "First Lieutenant",
        abbreviation: "1st Lt",
        reason: "",
      },
    ],
    budget_next_turn: 1420.5,
    income_next_turn: 180,
    ...overrides,
  };
}

const DIARY: WarDiary = {
  campaign: "Operation Dawn",
  since_turn: 3,
  entries: [entry(), entry({ turn: 3, summary: "Tactical victory: quiet" })],
};

function renderDiary(
  diary: WarDiary | null,
  answers: Record<string, Answer> = {},
) {
  const calls = recordFetch(204, undefined, { [DIARY_PATH]: diary }, answers);
  const router = createMemoryRouter(
    [
      { path: "/diary", element: <WarDiaryScreen /> },
      { path: "/bases/:id", element: <p>Base screen</p> },
      { path: "/career", element: <p>Career screen</p> },
      { path: "/", element: <p>Command view</p> },
    ],
    { initialEntries: ["/diary"] },
  );
  render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </Provider>,
  );
  return { router, calls };
}

describe("war diary screen", () => {
  it("shows one entry per turn, newest first, with its summary", async () => {
    renderDiary(DIARY);

    const turns = await screen.findAllByRole("article");
    expect(
      turns.map((t) => within(t).getByRole("heading").textContent),
    ).toEqual(["Turn 4 · 17 May 2022", "Turn 3 · 17 May 2022"]);
    const latest = within(turns[0]);
    expect(
      latest.getByText("Krymsk taken, 1 aircraft lost, Lt. Moroz rescued"),
    ).toBeVisible();
    expect(latest.getByText("Tactical victory")).toHaveAttribute(
      "data-tone",
      "good",
    );
    expect(latest.getByText(/Partly Cloudy/)).toBeVisible();
    expect(
      screen.getByText(
        "This campaign was started before the war diary existed: it begins at turn 3.",
      ),
    ).toBeVisible();
    // The details wait for a click.
    expect(latest.queryByText("Ammo depot")).not.toBeInTheDocument();
  });

  it("opens the details of a turn, linked to its bases and pilots", async () => {
    const { router } = renderDiary(DIARY);
    const [latest] = await screen.findAllByRole("article");
    const details = within(latest).getByRole("button", { name: "Details" });

    await userEvent.click(details);

    expect(details).toHaveAttribute("aria-expanded", "true");
    const turn = within(latest);
    expect(turn.getByText("Krymsk – Krasnodar: +2.4 km")).toBeVisible();
    expect(turn.getByText("Ammo depot")).toBeVisible();
    expect(turn.getByText("Target 40%")).toHaveAttribute("data-tone", "mixed");
    expect(turn.getByText("MiG-29A × 2")).toBeVisible();
    expect(turn.getByText(/Killed in action/)).toBeVisible();
    expect(turn.getByText(/Promoted to First Lieutenant/)).toBeVisible();
    // Only player pilots have a career.
    expect(
      turn.getByRole("link", { name: "Career of Lt. Moroz" }),
    ).toHaveAttribute("href", "/career?pilot=p-1");
    expect(
      turn.queryByRole("link", { name: "Career of Lt. Petrenko" }),
    ).not.toBeInTheDocument();

    await userEvent.click(turn.getByRole("link", { name: "Krymsk" }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/bases/cp-1"),
    );
  });

  it("exports the whole diary", async () => {
    const { calls } = renderDiary(DIARY, {
      [EXPORT_PATH]: {
        body: { outcome: "saved", path: "C:/Diaries/dawn.html" },
      },
    });

    await userEvent.click(
      await screen.findByRole("button", { name: "Export…" }),
    );

    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({ method: "POST", path: EXPORT_PATH }),
      ),
    );
    expect(await screen.findByText("War diary exported")).toBeInTheDocument();
  });

  it("explains when no turn was recorded yet", async () => {
    renderDiary({ campaign: "Operation Dawn", entries: [] });
    expect(
      await screen.findByText(
        "No turn recorded yet: an entry is written each time you accept a mission result.",
      ),
    ).toBeVisible();
  });
});

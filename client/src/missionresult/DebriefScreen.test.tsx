import type {
  AfterActionReport,
  Debriefing,
  SortieCard,
} from "../api/liberationApi";
import { recordFetch, renderShell, restoreFetch } from "../shell/testing";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const REPORT = "/game/mission/result/report";
const ACCEPT = "/game/mission/result/accept";

function report(overrides: Partial<AfterActionReport> = {}): AfterActionReport {
  return {
    turn: 4,
    date: "17 May 2022",
    player_country: "Ukraine",
    enemy_country: "Russia",
    verdict: "Tactical victory",
    verdict_tone: "good",
    summary: "Enemy lost 25 units, we lost 3 units. 1 base captured.",
    air_kills_friendly: 7,
    air_kills_enemy: 2,
    ground_kills_friendly: 23,
    ground_kills_enemy: 9,
    bases_captured: 1,
    bases_lost: 0,
    pilots_rescued: [
      { name: "Capt. Hrytsenko", aircraft: "Su-25T", squadron: "Rooks" },
    ],
    rescue_bounty: 0,
    packages: [
      {
        task: "DEAD",
        target: "SA-11 Krasnodar East",
        flights: ["Viper 1", "Hornet 2"],
        lost: 0,
        aircraft: 8,
        result: "Target destroyed",
        tone: "good",
      },
      {
        task: "Strike",
        target: "Ammo depot Krasnodar",
        flights: ["Fencer 8"],
        lost: 1,
        aircraft: 3,
        result: "Target 40%",
        tone: "mixed",
      },
    ],
    friendly_losses: [{ name: "Su-24M", count: 1 }],
    enemy_losses: [
      { name: "MiG-31", count: 1 },
      { name: "SA-11 TELAR", count: 2 },
    ],
    damaged_units: [],
    events: [
      { text: "Krasnodar captured", tone: "good" },
      { text: "Su-24M of Fencers lost · Lt. Moroz", tone: "bad" },
    ],
    your_sorties: [],
    applied: false,
    ...overrides,
  };
}

const MOROZ_ID = "5f0b5a4e-0000-4000-8000-000000000001";

function card(overrides: Partial<SortieCard> = {}): SortieCard {
  return {
    pilot_id: MOROZ_ID,
    pilot: "Lt. Moroz",
    squadron: "Fencers",
    aircraft: "Su-24M",
    flight: "Fencer 8",
    task: "Strike",
    target: "Ammo depot Krasnodar",
    package_result: "Target 40%",
    package_tone: "mixed",
    air_kills: 1,
    ground_kills: 3,
    naval_kills: 0,
    fate: "Ejected",
    fate_tone: "mixed",
    flight_time: "1:05",
    ...overrides,
  };
}

function yourSortie() {
  return within(screen.getByRole("region", { name: "Your sortie" }));
}

const APPLIED = report({
  applied: true,
  pilots_captured: [
    {
      name: "Lt. Moroz",
      aircraft: "Su-24M",
      squadron: "Fencers",
      held_at: "Maykop",
    },
  ],
  pilots_still_down: 1,
  your_sorties: [
    card({
      fate: "Ejected, awaiting rescue",
      sorties_logged: 1,
      rescues: 0,
      awards: [
        {
          kind: "Rank",
          name: "First Lieutenant",
          abbreviation: "1st Lt",
          reason: "",
        },
        {
          kind: "Decoration",
          name: "Purple Heart",
          abbreviation: "",
          reason: "Wounded in action.",
        },
      ],
    }),
  ],
  budget_next_turn: 1420,
  income_next_turn: 180,
  objectives: [
    { title: "Capture Krymsk", met: true, granted: "+150 budget" },
    { title: "Hold Anapa", met: false, granted: "" },
  ],
  events: [
    ...report().events,
    { time: "21:05:09", text: "Lt. Moroz was captured", tone: "neutral" },
  ],
});

function pending(canAccept = true): Debriefing {
  return { status: "pending", can_accept: canAccept, report: report() };
}

// The command view stays mounted under the report: look inside the report.
function inReport() {
  return within(screen.getByRole("region", { name: "After-action report" }));
}

function headline(label: string) {
  return inReport().getByText(label).parentElement as HTMLElement;
}

describe("DebriefScreen", () => {
  afterEach(restoreFetch);

  it("shows the report of a result waiting to be accepted", async () => {
    recordFetch(204, undefined, { [REPORT]: pending() });
    renderShell("/debrief");

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Tactical victory",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("After-action report · Turn 04 · 17 May 2022"),
    ).toBeInTheDocument();
    expect(screen.getByText(/1 base captured/)).toBeInTheDocument();

    expect(headline("Air kills")).toHaveTextContent("7 : 2");
    expect(headline("Ground units destroyed")).toHaveTextContent("23 : 9");
    expect(headline("Pilots")).toHaveTextContent("1 rescued");
    expect(headline("Pilots")).toHaveTextContent(
      "Known once the results are accepted",
    );
    expect(headline("Budget next turn")).toHaveTextContent("—");

    const packages = inReport().getByRole("region", { name: "Packages" });
    expect(within(packages).getByText("SA-11 Krasnodar East")).toBeVisible();
    expect(within(packages).getByText("Viper 1, Hornet 2")).toBeVisible();
    expect(within(packages).getByText("0 / 8 lost")).toBeVisible();
    expect(within(packages).getByText("Target 40%")).toHaveAttribute(
      "data-tone",
      "mixed",
    );

    const log = inReport().getByRole("region", { name: "Event log" });
    expect(within(log).getAllByRole("listitem")).toHaveLength(2);
    expect(within(log).getByText("Krasnodar captured")).toBeVisible();

    expect(
      screen.getByRole("table", { name: "Russia lost units" }),
    ).toBeInTheDocument();
    expect(screen.getByText("SA-11 TELAR")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Accept results" }),
    ).toBeEnabled();
    // No player pilot flew: no card.
    expect(
      screen.queryByRole("region", { name: "Your sortie" }),
    ).not.toBeInTheDocument();
  });

  it("shows a card per player pilot, linked to their career", async () => {
    const kovalenko = card({
      pilot_id: "5f0b5a4e-0000-4000-8000-000000000002",
      pilot: "Capt. Kovalenko",
      flight: "Viper 1",
      air_kills: 0,
      ground_kills: 0,
      fate: "Returned",
      fate_tone: "good",
    });
    recordFetch(204, undefined, {
      [REPORT]: {
        status: "pending",
        can_accept: true,
        report: report({ your_sorties: [card(), kovalenko] }),
      },
    });
    renderShell("/debrief");

    const moroz = await screen.findByRole("article", { name: "Lt. Moroz" });
    expect(yourSortie().getAllByRole("article")).toHaveLength(2);
    const first = within(moroz);
    expect(first.getByText("Fencer 8 · Su-24M · Fencers")).toBeVisible();
    expect(first.getByText("Ammo depot Krasnodar")).toBeVisible();
    expect(first.getByText("Target 40%")).toHaveAttribute("data-tone", "mixed");
    expect(first.getByText("Ejected")).toHaveAttribute("data-tone", "mixed");
    expect(first.getByText("1 air · 3 ground · 0 naval")).toBeVisible();
    expect(first.getByText(/1:05 planned/)).toBeVisible();
    expect(
      first.getByText("Awards are decided when you accept the results."),
    ).toBeVisible();
    expect(
      first.getByRole("link", { name: "Career of Lt. Moroz" }),
    ).toHaveAttribute("href", `/career?pilot=${MOROZ_ID}`);
  });

  it("cannot accept a mission still being played", async () => {
    recordFetch(204, undefined, { [REPORT]: pending(false) });
    renderShell("/debrief");
    expect(
      await screen.findByRole("button", { name: "Accept results" }),
    ).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("still being played");
  });

  it("accepts the results, shows what they decided, then continues", async () => {
    const gets: Record<string, unknown> = { [REPORT]: pending() };
    const calls = recordFetch(204, undefined, gets, {
      [ACCEPT]: { body: { turn: 5, campaign_state: "continue" } },
    });
    const { router } = renderShell("/debrief");
    const accept = await screen.findByRole("button", {
      name: "Accept results",
    });

    // The engine applies the result; the report then has the final figures.
    gets[REPORT] = { status: "accepted", can_accept: false, report: APPLIED };
    await userEvent.click(accept);

    expect(calls).toMatchObject([{ method: "POST", path: ACCEPT }]);
    expect(await screen.findByText("Results accepted")).toBeInTheDocument();
    const next = await screen.findByRole("button", { name: "Continue" });
    expect(headline("Pilots")).toHaveTextContent("1 rescued · 1 POW");
    expect(headline("Pilots")).toHaveTextContent("1 still down");
    expect(headline("Budget next turn")).toHaveTextContent("$1 420M");
    expect(headline("Budget next turn")).toHaveTextContent("+180M/turn income");
    expect(screen.getByText(/held at Maykop/)).toBeInTheDocument();
    expect(screen.getByText("21:05:09")).toBeInTheDocument();
    const objectives = within(
      inReport().getByRole("region", { name: "Objectives" }),
    );
    expect(
      objectives.getByText("Met: Capture Krymsk · +150 budget"),
    ).toHaveAttribute("data-tone", "good");
    expect(objectives.getByText("Missed: Hold Anapa")).toHaveAttribute(
      "data-tone",
      "bad",
    );
    const moroz = within(
      yourSortie().getByRole("article", { name: "Lt. Moroz" }),
    );
    expect(moroz.getByText("Ejected, awaiting rescue")).toBeVisible();
    expect(moroz.getByText(/1 sortie logged · 1:05/)).toBeVisible();
    expect(moroz.getByText("1st Lt")).toBeVisible();
    expect(moroz.getByText("Promoted to First Lieutenant")).toBeVisible();
    expect(moroz.getByText("Awarded Purple Heart")).toBeVisible();
    expect(moroz.getByText("Wounded in action.")).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Accept results" }),
    ).not.toBeInTheDocument();

    await userEvent.click(next);
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
  });

  it("announces the end of the campaign", async () => {
    recordFetch(
      204,
      undefined,
      { [REPORT]: pending() },
      { [ACCEPT]: { body: { turn: 5, campaign_state: "win" } } },
    );
    renderShell("/debrief");
    await userEvent.click(
      await screen.findByRole("button", { name: "Accept results" }),
    );
    expect(await screen.findByText("Victory!")).toBeInTheDocument();
  });

  it("shows why the results were refused", async () => {
    recordFetch(
      204,
      undefined,
      { [REPORT]: pending() },
      {
        [ACCEPT]: {
          status: 409,
          body: { detail: "No mission result has been received yet." },
        },
      },
    );
    const { router } = renderShell("/debrief");
    await userEvent.click(
      await screen.findByRole("button", { name: "Accept results" }),
    );
    expect(
      await screen.findByText("No mission result has been received yet."),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/debrief");
  });

  it("says when there is no debriefing", async () => {
    recordFetch(204, undefined, {
      [REPORT]: { status: "none", can_accept: false },
    });
    renderShell("/debrief");
    expect(
      await screen.findByRole("heading", { name: "No debriefing yet" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Back to the map" }),
    ).toBeInTheDocument();
  });
});

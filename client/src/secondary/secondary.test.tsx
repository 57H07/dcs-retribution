import type {
  AboutJs,
  CareerJs,
  InformationJs,
  LogTailJs,
  TransferJs,
} from "../api/liberationApi";
import { setupStore } from "../app/store";
import { Answer, recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { AboutScreen } from "./AboutScreen";
import { CareerScreen } from "./CareerScreen";
import { InfoPanelScreen } from "./InfoPanelScreen";
import { LogsScreen } from "./LogsScreen";
import { NotesScreen } from "./NotesScreen";
import { TransfersScreen } from "./TransfersScreen";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReactElement } from "react";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

function renderScreen(
  element: ReactElement,
  gets: Record<string, unknown> = {},
  answers: Record<string, Answer> = {},
) {
  const calls = recordFetch(204, undefined, gets, answers);
  const router = createMemoryRouter(
    [
      { path: "/screen", element },
      { path: "/", element: <p>Command view</p> },
    ],
    { initialEntries: ["/screen"] },
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

const TRANSFER: TransferJs = {
  id: "t-1",
  origin: "Incirlik",
  destination: "Hatay",
  position: "Incirlik",
  size: 6,
  units: [
    { name: "M1A2 Abrams", count: 4 },
    { name: "M2A2 Bradley", count: 2 },
  ],
  transport: "Convoy to Hatay",
};

describe("transfers screen", () => {
  it("lists the pending transfers", async () => {
    renderScreen(<TransfersScreen />, { "/transfers/": [TRANSFER] });
    const card = await screen.findByRole("listitem", {
      name: "Incirlik → Hatay",
    });
    expect(card).toHaveTextContent("4 × M1A2 Abrams, 2 × M2A2 Bradley");
    expect(card).toHaveTextContent("Convoy to Hatay");
  });

  it("cancels a transfer with the API command", async () => {
    const { calls } = renderScreen(<TransfersScreen />, {
      "/transfers/": [TRANSFER],
    });
    await userEvent.click(
      await screen.findByRole("button", { name: "Cancel transfer" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "DELETE",
      path: "/transfers/t-1",
    });
    expect(await screen.findByText("Transfer cancelled")).toBeInTheDocument();
  });

  it("shows why a cancellation is refused", async () => {
    renderScreen(
      <TransfersScreen />,
      { "/transfers/": [TRANSFER] },
      {
        "/transfers/t-1": {
          status: 404,
          body: { detail: "This transfer is no longer pending." },
        },
      },
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Cancel transfer" }),
    );
    expect(
      await screen.findByText("This transfer is no longer pending."),
    ).toBeInTheDocument();
  });

  it("says when nothing is pending", async () => {
    renderScreen(<TransfersScreen />, { "/transfers/": [] });
    expect(await screen.findByText("No pending transfer.")).toBeVisible();
  });

  it("says when no campaign is loaded", async () => {
    renderScreen(<TransfersScreen />);
    expect(await screen.findByText("No campaign loaded.")).toBeVisible();
  });
});

describe("notes screen", () => {
  it("edits and saves the notes", async () => {
    const { calls } = renderScreen(
      <NotesScreen />,
      { "/notes": { text: "Bring tankers." } },
      { "/notes": { status: 200, body: { text: "Bring tankers. SEAD." } } },
    );
    const editor = await screen.findByRole("textbox", { name: "Notes" });
    expect(editor).toHaveValue("Bring tankers.");
    expect(screen.getByRole("button", { name: "Saved" })).toBeDisabled();

    await userEvent.type(editor, " SEAD.");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "PUT",
      path: "/notes",
      body: { text: "Bring tankers. SEAD." },
    });
    expect(await screen.findByText("Notes saved")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Saved" })).toBeDisabled();
  });

  it("reopens on the saved notes, not the cached ones", async () => {
    const gets = { "/notes": { text: "Old" } };
    const { router } = renderScreen(<NotesScreen />, gets, {
      "/notes": { status: 200, body: { text: "New" } },
    });
    const editor = await screen.findByRole("textbox", { name: "Notes" });
    await userEvent.clear(editor);
    await userEvent.type(editor, "New");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText("Notes saved");
    gets["/notes"] = { text: "New" };

    await userEvent.click(screen.getByRole("link", { name: /Command view/ }));
    await act(() => router.navigate("/screen"));
    expect(await screen.findByRole("textbox", { name: "Notes" })).toHaveValue(
      "New",
    );
  });

  it("clears the editor without saving", async () => {
    const { calls } = renderScreen(<NotesScreen />, {
      "/notes": { text: "Old" },
    });
    await userEvent.click(await screen.findByRole("button", { name: "Clear" }));
    expect(screen.getByRole("textbox", { name: "Notes" })).toHaveValue("");
    expect(calls).toHaveLength(0);
  });
});

describe("logs screen", () => {
  it("shows the tail of the log, read-only", async () => {
    const log: LogTailJs = {
      lines: ["line 1", "line 2"],
      total: 1500,
      available: true,
    };
    const { calls } = renderScreen(<LogsScreen />, { "/logs": log });
    const console = await screen.findByLabelText("Application log");
    expect(console).toHaveTextContent("line 1 line 2");
    expect(screen.getByText(/Last 2 of 1500 lines/)).toBeVisible();
    expect(screen.queryByRole("button")).toBeNull();
    expect(calls).toHaveLength(0);
  });

  it("explains a log kept out of memory", async () => {
    renderScreen(<LogsScreen />, {
      "/logs": { lines: [], total: 0, available: false },
    });
    expect(await screen.findByText(/keeps no log in memory/)).toBeVisible();
  });
});

describe("info panel screen", () => {
  it("lists the campaign messages", async () => {
    const messages: InformationJs[] = [
      {
        turn: 2,
        title: "Budget",
        text: "Income 20M",
        timestamp: "2026-10-01T12:05:00",
      },
      { turn: 1, title: "Base captured", text: "Hatay" },
    ];
    renderScreen(<InfoPanelScreen />, { "/informations": messages });
    const table = await screen.findByRole("table", {
      name: "Campaign messages",
    });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual([
      "2BudgetIncome 20M2026-10-01 12:05",
      "1Base capturedHatay",
    ]);
  });
});

const CAREER: CareerJs = {
  pilot_id: "pilot-1",
  pilot: "Maverick",
  squadron: "VF-1 Wolfpack",
  status: "Active",
  alive: true,
  rank: "Lieutenant",
  totals: [
    { label: "Sorties", value: "1" },
    { label: "Flight time", value: "1:05" },
  ],
  awards: [
    {
      name: "Lieutenant",
      kind: "Rank",
      date: "2026-06-01 08:30",
      turn: 1,
      description: "",
    },
  ],
  history: [
    {
      turn: 1,
      date: "2026-06-01 08:30",
      squadron: "VF-1",
      aircraft: "F-14B",
      task: "BARCAP",
      combat: true,
      flight_time: "1:05",
      air_kills: 2,
      ground_kills: 0,
      naval_kills: 0,
      rescues: 0,
      loss: "Ejected",
    },
  ],
};

describe("career screen", () => {
  it("shows the logbook, awards and missions", async () => {
    renderScreen(<CareerScreen />, { "/careers/": [CAREER] });
    expect(
      await screen.findByRole("heading", { name: "Lieutenant Maverick" }),
    ).toBeVisible();
    expect(screen.getByText("VF-1 Wolfpack — Active")).toBeVisible();
    const history = screen.getByRole("table", { name: "Mission history" });
    expect(
      within(history)
        .getAllByRole("row")
        .slice(1)
        .map((r) => r.textContent),
    ).toEqual(["12026-06-01 08:30VF-1F-14BBARCAPYes1:052Ejected"]);
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("switches between player pilots", async () => {
    const goose = { ...CAREER, pilot: "Goose", rank: null, awards: [] };
    renderScreen(<CareerScreen />, { "/careers/": [CAREER, goose] });
    await userEvent.selectOptions(
      await screen.findByRole("combobox"),
      "Goose (VF-1 Wolfpack)",
    );
    expect(
      screen.getByRole("heading", { name: "No rank yet Goose" }),
    ).toBeVisible();
    expect(
      screen.getByText("Ranks and decorations are awarded after each mission."),
    ).toBeVisible();
  });

  it("explains how to start a career", async () => {
    renderScreen(<CareerScreen />, { "/careers/": [] });
    expect(await screen.findByText(/No player pilot/)).toBeVisible();
  });
});

describe("about screen", () => {
  it("shows the version and credits, and opens the repository", async () => {
    const about: AboutJs = {
      version: "1.6.0",
      source_url: "https://github.com/dcs-retribution/dcs-retribution",
      authors: "A fork of DCS Liberation.",
      contributors: ["shdwp", "Khopa"],
      special_thanks: [{ name: "rp-", reason: "for the pydcs framework" }],
      attributions: [{ text: "NASA EarthData", url: "https://nasa.example/" }],
    };
    const { calls } = renderScreen(<AboutScreen />, { "/about": about });
    expect(await screen.findByText("1.6.0")).toBeVisible();
    expect(screen.getByText("shdwp, Khopa")).toBeVisible();
    expect(screen.getByText("for the pydcs framework")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Source code" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe("/native/open-link/github");
  });

  it("goes back to the command view", async () => {
    const { router } = renderScreen(<AboutScreen />);
    await userEvent.click(screen.getByRole("link", { name: /Command view/ }));
    expect(router.state.location.pathname).toBe("/");
  });
});

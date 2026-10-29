import type { Setting, Settings } from "../api/liberationApi";
import { setupStore } from "../app/store";
import { restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { SettingsScreen } from "./SettingsScreen";
import { modifiedCount, searchSettings } from "./search";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";

function setting(overrides: Partial<Setting> & Pick<Setting, "key">): Setting {
  return {
    label: overrides.key,
    kind: "bool",
    value: true,
    default: true,
    modified: false,
    ...overrides,
  };
}

// Invented settings: the screen must render whatever the schema describes.
function schema(): Settings {
  return {
    pages: [
      {
        id: "difficulty",
        name: "Difficulty",
        sections: [
          {
            name: "AI Difficulty",
            settings: [
              setting({
                key: "player_skill",
                label: "Player coalition skill",
                kind: "choice",
                value: "Good",
                default: "High",
                modified: true,
                choices: ["Average", "Good", "High", "Excellent"],
              }),
              setting({
                key: "income",
                label: "Player income multiplier",
                kind: "float",
                value: 1,
                default: 1,
                min: 0,
                max: 5,
                step: 0.1,
              }),
              setting({
                key: "invulnerable",
                label: "Player pilots cannot be killed",
                detail: "The pilot returns to the squadron after the mission",
                tooltip: "Aircraft stay vulnerable.",
              }),
            ],
          },
        ],
      },
      {
        id: "campaign-doctrine",
        name: "Campaign Doctrine",
        sections: [
          {
            name: "General",
            settings: [
              setting({
                key: "barcap",
                label: "Desired BARCAP on-station time",
                kind: "minutes",
                value: 60,
                default: 60,
                min: 30,
                max: 150,
                step: 1,
              }),
              setting({
                key: "culling",
                label: "Culling distance (km)",
                kind: "int",
                value: 100,
                default: 100,
                min: 10,
                max: 10000,
                step: 1,
              }),
            ],
          },
        ],
      },
      {
        id: "lua-plugins-options",
        name: "LUA Plugins Options",
        sections: [
          {
            name: "Skynet IADS",
            description: "Skynet is an IADS script.",
            settings: [setting({ key: "plugin-option.skynet.debug" })],
          },
        ],
      },
    ],
  };
}

type Request = { method: string; path: string; body: unknown };

/** A fake server holding the schema: PUT changes a value, POST resets a page. */
function fakeServer(options: { getStatus?: number; putStatus?: number } = {}) {
  const state = schema();
  const requests: Request[] = [];
  const all = () =>
    state.pages.flatMap((p) => p.sections.flatMap((s) => s.settings));
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    const path = new URL(request.url).pathname;
    const text = await request.text();
    const body = text ? JSON.parse(text) : undefined;
    requests.push({ method: request.method, path, body });
    const json = (status: number, data: unknown) =>
      new Response(JSON.stringify(data), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    if (request.method === "GET") {
      return options.getStatus
        ? json(options.getStatus, { detail: "No campaign is loaded." })
        : json(200, state);
    }
    const put = path.match(/^\/settings\/values\/(.+)$/);
    if (put) {
      if (options.putStatus) {
        return json(options.putStatus, { detail: "Out of bounds." });
      }
      const target = all().find((s) => s.key === decodeURIComponent(put[1]))!;
      target.value = body.value;
      target.modified = target.value !== target.default;
      return json(200, target);
    }
    const reset = path.match(/^\/settings\/pages\/(.+)\/reset$/);
    if (reset) {
      const page = state.pages.find((p) => p.id === reset[1])!;
      for (const s of page.sections.flatMap((section) => section.settings)) {
        s.value = s.default;
        s.modified = false;
      }
      return json(200, page);
    }
    return new Response(null, { status: 404 });
  };
  return requests;
}

function renderScreen() {
  return render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <MemoryRouter initialEntries={["/settings"]}>
          <SettingsScreen />
        </MemoryRouter>
      </ToastProvider>
    </Provider>,
  );
}

afterEach(restoreFetch);

describe("SettingsScreen", () => {
  it("shows a loading state, then the first page", async () => {
    fakeServer();
    renderScreen();
    expect(screen.getByText("Loading settings…")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "AI Difficulty" }),
    ).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Settings pages" });
    expect(
      within(nav)
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual(["Difficulty1", "Campaign Doctrine", "LUA Plugins Options"]);
    expect(
      within(nav).getByRole("button", { name: /Difficulty/ }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("renders one control per setting kind", async () => {
    fakeServer();
    renderScreen();
    expect(
      await screen.findByRole("combobox", { name: "Player coalition skill" }),
    ).toHaveValue("Good");
    expect(
      screen.getByRole("switch", { name: "Player pilots cannot be killed" }),
    ).toBeChecked();
    expect(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "1");

    await userEvent.click(
      screen.getByRole("button", { name: "Campaign Doctrine" }),
    );
    const barcap = screen.getByTestId("setting-barcap");
    expect(within(barcap).getByRole("spinbutton")).toHaveValue("60");
    expect(within(barcap).getByText("min")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("setting-culling")).getByRole("spinbutton"),
    ).toHaveValue("100");
  });

  it("shows help text, section descriptions and the Modified marker", async () => {
    fakeServer();
    renderScreen();
    expect(
      await screen.findByText(
        "The pilot returns to the squadron after the mission",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "About Player pilots cannot be killed",
      }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("setting-player_skill")).getByText("Modified"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("setting-income")).queryByText("Modified"),
    ).toBeNull();
    expect(screen.getByText("1 change from defaults")).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "LUA Plugins Options" }),
    );
    expect(screen.getByText("Skynet is an IADS script.")).toBeInTheDocument();
  });

  it("sends a command when a control changes and shows the new value", async () => {
    const requests = fakeServer();
    renderScreen();
    const toggle = await screen.findByRole("switch", {
      name: "Player pilots cannot be killed",
    });
    await userEvent.click(toggle);
    await waitFor(() =>
      expect(requests).toContainEqual({
        method: "PUT",
        path: "/settings/values/invulnerable",
        body: { value: false },
      }),
    );
    await waitFor(() =>
      expect(
        within(screen.getByTestId("setting-invulnerable")).getByText(
          "Modified",
        ),
      ).toBeInTheDocument(),
    );
    expect(toggle).not.toBeChecked();

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Player coalition skill" }),
      "Excellent",
    );
    await waitFor(() =>
      expect(requests).toContainEqual({
        method: "PUT",
        path: "/settings/values/player_skill",
        body: { value: "Excellent" },
      }),
    );
  });

  it("shows the server's refusal and keeps the server value", async () => {
    fakeServer({ putStatus: 422 });
    renderScreen();
    const toggle = await screen.findByRole("switch", {
      name: "Player pilots cannot be killed",
    });
    await userEvent.click(toggle);
    expect(await screen.findByText("Out of bounds.")).toBeInTheDocument();
    expect(toggle).toBeChecked();
  });

  it("searches across every page", async () => {
    fakeServer();
    renderScreen();
    await screen.findByRole("heading", { name: "AI Difficulty" });
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Search all settings" }),
      "time",
    );
    expect(
      screen.getByRole("heading", { name: "Campaign Doctrine › General" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("setting-barcap")).toBeInTheDocument();
    expect(screen.queryByTestId("setting-player_skill")).toBeNull();
    expect(screen.queryByText("Reset page")).toBeNull();

    await userEvent.clear(screen.getByRole("searchbox"));
    await userEvent.type(screen.getByRole("searchbox"), "zzz");
    expect(screen.getByText("No setting matches “zzz”.")).toBeInTheDocument();
  });

  it("resets the current page after confirmation", async () => {
    const requests = fakeServer();
    renderScreen();
    await screen.findByRole("heading", { name: "AI Difficulty" });
    await userEvent.click(screen.getByRole("button", { name: "Reset page" }));
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByText(/1 setting of this page/),
    ).toBeInTheDocument();
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Reset" }),
    );
    await waitFor(() =>
      expect(requests).toContainEqual({
        method: "POST",
        path: "/settings/pages/difficulty/reset",
        body: undefined,
      }),
    );
    await waitFor(() =>
      expect(screen.getByText("0 changes from defaults")).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "Reset page" })).toBeDisabled();
  });

  it("shows the server error when no campaign is loaded", async () => {
    fakeServer({ getStatus: 409 });
    renderScreen();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No campaign is loaded.",
    );
  });
});

describe("settings search helpers", () => {
  const pages = schema().pages;

  it("matches every word in label, help, section or page", () => {
    const keys = (query: string) =>
      searchSettings(pages, query).map((m) => m.setting.key);
    expect(keys("")).toEqual([]);
    expect(keys("PLAYER")).toEqual(["player_skill", "income", "invulnerable"]);
    expect(keys("squadron")).toEqual(["invulnerable"]);
    expect(keys("doctrine distance")).toEqual(["culling"]);
    expect(keys("skynet")).toEqual(["plugin-option.skynet.debug"]);
  });

  it("counts the modified settings of a page", () => {
    expect(pages.map(modifiedCount)).toEqual([1, 0, 0]);
  });
});

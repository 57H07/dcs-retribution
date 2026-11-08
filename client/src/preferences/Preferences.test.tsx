import type {
  InstallPreferences,
  InstallPreferencesState,
  PlayerModule,
} from "../api/liberationApi";
import { renderShell, restoreFetch } from "../shell/testing";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

type Request = { method: string; path: string; body: unknown };

const SAVED: InstallPreferences = {
  saved_game_dir: "C:/Users/me/Saved Games/DCS",
  dcs_install_dir: "D:/DCS World",
  prefer_liberation_payloads: false,
  setup_preferences_on_every_start: false,
  server_port: 16880,
  autosave_turns: 5,
};

/**
 * A fake server holding the preferences: PUT saves them (or answers `refuse`),
 * pick-folder answers `picked`. Saving ends the first start.
 */
function fakeServer(
  options: {
    firstStart?: boolean;
    preferences?: Partial<InstallPreferences>;
    refuse?: string;
    picked?: string | null;
  } = {},
) {
  let state: InstallPreferencesState = {
    preferences: { ...SAVED, ...options.preferences },
    first_start: options.firstStart ?? false,
    saved_game_dir_problem: options.firstStart
      ? "Choose your DCS Saved Games folder."
      : undefined,
    dcs_install_dir_problem: undefined,
    warning: null,
  };
  const requests: Request[] = [];
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    const path = new URL(request.url).pathname;
    const text = await request.text();
    const body = text === "" ? undefined : JSON.parse(text);
    if (request.method !== "GET") {
      requests.push({ method: request.method, path, body });
    }
    if (path === "/preferences/" && request.method === "GET") {
      return json(state);
    }
    if (path === "/preferences/" && request.method === "PUT") {
      if (options.refuse) {
        return json({ detail: options.refuse }, 409);
      }
      const { allow_empty_install_dir: _, ...preferences } = body;
      state = {
        ...state,
        preferences,
        first_start: false,
        saved_game_dir_problem: undefined,
      };
      return json(state);
    }
    if (path === "/native/pick-folder") {
      return json({ path: options.picked ?? null });
    }
    return json(null);
  };
  return requests;
}

afterEach(restoreFetch);

describe("Preferences screen", () => {
  it("shows the saved preferences and applies changes", async () => {
    const requests = fakeServer();
    renderShell("/preferences");
    const saved = await screen.findByRole("textbox", {
      name: "DCS Saved Games folder",
    });
    expect(saved).toHaveValue(SAVED.saved_game_dir);
    expect(
      screen.getByRole("textbox", { name: "DCS installation folder" }),
    ).toHaveValue(SAVED.dcs_install_dir);

    await userEvent.click(
      screen.getByRole("switch", { name: "Prefer custom Liberation payloads" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    await waitFor(() => expect(requests).toHaveLength(1));
    expect(requests[0]).toEqual({
      method: "PUT",
      path: "/preferences/",
      body: {
        ...SAVED,
        prefer_liberation_payloads: true,
        allow_empty_install_dir: false,
      },
    });
    expect(await screen.findByText("Preferences saved")).toBeInTheDocument();
  });

  it("browses for a folder through the native bridge", async () => {
    const requests = fakeServer({ picked: "E:/DCS" });
    renderShell("/preferences");
    await screen.findByRole("textbox", { name: "DCS installation folder" });
    const browse = screen.getAllByRole("button", { name: "Browse…" });
    await userEvent.click(browse[1]);
    await waitFor(() =>
      expect(
        screen.getByRole("textbox", { name: "DCS installation folder" }),
      ).toHaveValue("E:/DCS"),
    );
    expect(requests[0]).toEqual({
      method: "POST",
      path: "/native/pick-folder",
      body: { purpose: "dcs-install", start: SAVED.dcs_install_dir },
    });
  });

  it("keeps the field when the folder dialog is cancelled", async () => {
    fakeServer({ picked: null });
    renderShell("/preferences");
    const field = await screen.findByRole("textbox", {
      name: "DCS Saved Games folder",
    });
    await userEvent.click(
      screen.getAllByRole("button", { name: "Browse…" })[0],
    );
    await waitFor(() => expect(field).toHaveValue(SAVED.saved_game_dir));
  });

  it("shows the server's refusal", async () => {
    fakeServer({ refuse: "X:/nowhere is not a valid directory." });
    renderShell("/preferences");
    await screen.findByRole("textbox", { name: "DCS Saved Games folder" });
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(
      await screen.findByText("Preferences not saved"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("X:/nowhere is not a valid directory."),
    ).toBeInTheDocument();
  });

  it("asks before leaving the DCS installation folder empty", async () => {
    const requests = fakeServer({ preferences: { dcs_install_dir: "" } });
    renderShell("/preferences");
    await screen.findByRole("textbox", { name: "DCS installation folder" });
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Leave the DCS installation folder empty?",
    });
    expect(requests).toHaveLength(0);
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Leave it empty" }),
    );
    await waitFor(() => expect(requests).toHaveLength(1));
    expect(requests[0].body).toMatchObject({
      dcs_install_dir: "",
      allow_empty_install_dir: true,
    });
  });
});

describe("first start", () => {
  it("is not shown when the preferences are valid", async () => {
    fakeServer();
    renderShell("/");
    await screen.findByRole("button", { name: "File" });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(
      screen.queryByRole("dialog", { name: "Welcome to DCS Retribution" }),
    ).toBeNull();
  });

  it("covers the shell until valid preferences are accepted", async () => {
    const requests = fakeServer({
      firstStart: true,
      preferences: { saved_game_dir: "" },
    });
    renderShell("/");
    const dialog = await screen.findByRole("dialog", {
      name: "Welcome to DCS Retribution",
    });
    expect(dialog).toHaveTextContent("MissionScripting.lua");
    expect(
      within(dialog).getByText("Choose your DCS Saved Games folder."),
    ).toBeInTheDocument();

    await userEvent.type(
      within(dialog).getByRole("textbox", { name: "DCS Saved Games folder" }),
      "C:/SG",
    );
    await userEvent.click(
      within(dialog).getByRole("button", {
        name: "I have read everything and I accept",
      }),
    );
    await waitFor(() => expect(requests).toHaveLength(1));
    expect(requests[0].body).toMatchObject({ saved_game_dir: "C:/SG" });
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", { name: "Welcome to DCS Retribution" }),
      ).toBeNull(),
    );
  });
});

describe("Modules you own", () => {
  const MODULES: PlayerModule[] = [
    { id: "F-14B", name: "F-14B Tomcat", owned: true },
    { id: "FA-18C_hornet", name: "F/A-18C Hornet", owned: false },
  ];

  function modulesServer(refuse = false) {
    const puts: unknown[] = [];
    const json = (body: unknown, status = 200) =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    let modules = MODULES;
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = new Request(input, init);
      const path = new URL(request.url).pathname;
      if (path !== "/preferences/modules") {
        return json(null);
      }
      if (request.method === "PUT") {
        const body = await request.json();
        puts.push(body);
        if (refuse) {
          return json({ detail: "Unknown modules: F-14B." }, 409);
        }
        modules = modules.map((m) => ({
          ...m,
          owned: body.owned.includes(m.id),
        }));
      }
      return json(modules);
    };
    return puts;
  }

  it("shows what is owned and saves each tick", async () => {
    const puts = modulesServer();
    renderShell("/preferences");
    const tomcat = await screen.findByRole("checkbox", {
      name: "F-14B Tomcat",
    });
    expect(tomcat).toBeChecked();
    const hornet = screen.getByRole("checkbox", { name: "F/A-18C Hornet" });
    expect(hornet).not.toBeChecked();
    await userEvent.click(hornet);
    await waitFor(() => expect(puts).toHaveLength(1));
    expect(puts[0]).toEqual({ owned: ["F-14B", "FA-18C_hornet"] });
    await waitFor(() => expect(hornet).toBeChecked());
  });

  it("filters the list", async () => {
    modulesServer();
    renderShell("/preferences");
    await screen.findByRole("checkbox", { name: "F-14B Tomcat" });
    await userEvent.type(
      screen.getByRole("textbox", { name: "Filter modules" }),
      "hornet",
    );
    expect(screen.queryByRole("checkbox", { name: "F-14B Tomcat" })).toBeNull();
    expect(
      screen.getByRole("checkbox", { name: "F/A-18C Hornet" }),
    ).toBeInTheDocument();
  });

  it("goes back to the saved state when the server refuses", async () => {
    modulesServer(true);
    renderShell("/preferences");
    const tomcat = await screen.findByRole("checkbox", {
      name: "F-14B Tomcat",
    });
    await userEvent.click(tomcat);
    expect(await screen.findByText("Modules not saved")).toBeInTheDocument();
    expect(tomcat).toBeChecked();
  });
});

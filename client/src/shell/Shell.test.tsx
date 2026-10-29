import { registerOverlayToggler } from "../maplayers/layerToggle";
import { OVERLAYS } from "../maplayers/overlays";
import { MenuAction } from "../ui";
import { appMenus } from "./AppBar";
import { recordFetch, renderShell, restoreFetch } from "./testing";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

afterEach(restoreFetch);

describe("shortcuts in the shell", () => {
  it("Ctrl+S saves through the Qt save action", async () => {
    const calls = recordFetch();
    renderShell();
    fireEvent.keyDown(window, { key: "s", ctrlKey: true });
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/qt/dialogs/save-game",
    });
  });

  it("N opens the packages and explains how to plan one", async () => {
    const calls = recordFetch();
    renderShell();
    fireEvent.keyDown(window, { key: "n" });
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe("/qt/dialogs/air-tasking-order");
    expect(await screen.findByText(/Right-click a target/)).toBeInTheDocument();
  });

  it("1-5 toggle map layers", () => {
    recordFetch();
    renderShell();
    const toggled: string[] = [];
    const unregister = registerOverlayToggler((name) => {
      toggled.push(name);
      return true;
    });
    fireEvent.keyDown(window, { key: "1" });
    fireEvent.keyDown(window, { key: "4" });
    unregister();
    expect(toggled).toEqual([
      OVERLAYS.frontLines.name,
      OVERLAYS.supplyRoutes.name,
    ]);
  });

  it("? shows the help overlay and Esc closes it", async () => {
    recordFetch();
    renderShell();
    fireEvent.keyDown(window, { key: "?" });
    const dialog = await screen.findByRole("dialog", {
      name: "Keyboard shortcuts",
    });
    expect(dialog).toHaveTextContent("Ctrl+S");
    expect(dialog).toHaveTextContent(OVERLAYS.frontLines.name);
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("ignores shortcuts typed in a text field", () => {
    const calls = recordFetch();
    renderShell();
    const input = document.createElement("input");
    document.body.appendChild(input);
    fireEvent.keyDown(input, { key: "s", ctrlKey: true });
    fireEvent.keyDown(input, { key: "n" });
    fireEvent.keyDown(input, { key: "?" });
    input.remove();
    expect(calls).toHaveLength(0);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("app bar", () => {
  it("opens a Qt dialog from a menu", async () => {
    const calls = recordFetch();
    renderShell();
    await userEvent.click(screen.getByRole("button", { name: "File" }));
    await userEvent.click(
      await screen.findByRole("menuitem", { name: "Save as…" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe("/qt/dialogs/save-game-as");
  });

  it("passes the turn with the API command", async () => {
    const calls = recordFetch(200, { turn: 2, campaign_state: "continue" });
    renderShell();
    await userEvent.click(screen.getByRole("button", { name: "Pass turn" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe("/game/turn/pass");
  });

  it("reaches every Qt menu, toolbar and top panel action", () => {
    const dialogs: string[] = [];
    const links: string[] = [];
    const paths: string[] = [];
    let help = 0;
    let newPackage = 0;
    const menus = appMenus({
      qt: {
        openDialog: (d) => dialogs.push(d),
        openLink: (l) => links.push(l),
        openBase: () => {},
        editPackageOfFlight: () => {},
      },
      navigate: (p) => paths.push(p),
      onNewPackage: () => newPackage++,
      onShowHelp: () => help++,
    });
    for (const menu of menus) {
      for (const item of menu.items) {
        if (item !== "separator") {
          (item as MenuAction).onSelect();
        }
      }
    }
    // Qt File / Developer tools / Help menus, toolbars and QTopPanel buttons.
    expect(new Set(dialogs)).toEqual(
      new Set([
        "open-game",
        "save-game",
        "save-game-as",
        "preferences",
        "quit",
        "transfers",
        "air-tasking-order",
        "stats",
        "notes",
        "pretense-campaign",
        "import-layouts",
        "logs",
        "about",
      ]),
    );
    expect(new Set(links)).toEqual(
      new Set([
        "manual",
        "releases",
        "forum-thread",
        "issues",
        "discord",
        "github",
        "ukraine",
        "pretense-discord",
      ]),
    );
    expect(new Set(paths)).toEqual(
      new Set([
        "/new-game",
        "/air-wing",
        "/settings",
        "/reports",
        "/debrief",
      ]),
    );
    expect(help).toBe(1);
    expect(newPackage).toBe(1);
  });
});

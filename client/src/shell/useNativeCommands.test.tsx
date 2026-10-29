import { setupStore } from "../app/store";
import { ToastProvider } from "../ui";
import { recordFetch, restoreFetch } from "./testing";
import {
  FileAction,
  fileResultToast,
  isFileAction,
  useNativeCommands,
} from "./useNativeCommands";
import { useQtCommands } from "./useQtCommands";
import { act, renderHook, screen, waitFor } from "@testing-library/react";
import { ReactNode } from "react";
import { Provider } from "react-redux";

afterEach(restoreFetch);

function wrapper({ children }: { children: ReactNode }) {
  return (
    <Provider store={setupStore()}>
      <ToastProvider>{children}</ToastProvider>
    </Provider>
  );
}

function renderNative() {
  return renderHook(() => useNativeCommands(), { wrapper }).result;
}

describe("native file actions", () => {
  it.each<[FileAction, string]>([
    ["save-game", "/native/save"],
    ["save-game-as", "/native/save-as"],
    ["open-game", "/native/open"],
    ["new-game", "/native/new-game"],
    ["quit", "/native/quit"],
  ])("%s posts %s", async (action, path) => {
    const calls = recordFetch(200, { outcome: "cancelled" });
    const native = renderNative();
    act(() => native.current.runFileAction(action));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({ method: "POST", path });
  });

  it("tells the player where the campaign was opened from", async () => {
    recordFetch(200, { outcome: "opened", path: "C:/saves/b.retribution" });
    const native = renderNative();
    act(() => native.current.runFileAction("open-game"));
    expect(await screen.findByText("Campaign opened")).toBeInTheDocument();
    expect(screen.getByText("C:/saves/b.retribution")).toBeInTheDocument();
  });

  it("shows the server's reason when a save fails", async () => {
    recordFetch(500, { detail: "Could not save the campaign to Z:/a." });
    const native = renderNative();
    act(() => native.current.runFileAction("save-game"));
    expect(
      await screen.findByText("Could not save the campaign"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Could not save the campaign to Z:/a."),
    ).toBeInTheDocument();
  });

  it("opens links and folders through the bridge", async () => {
    const calls = recordFetch();
    const native = renderNative();
    act(() => {
      native.current.openLink("discord");
      native.current.openFolder("saves");
    });
    await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls.map((c) => c.path).sort()).toEqual([
      "/native/open-folder/saves",
      "/native/open-link/discord",
    ]);
  });
});

describe("useQtCommands", () => {
  it("routes the File menu entries to the bridge and the rest to Qt", async () => {
    const calls = recordFetch(200, { outcome: "cancelled" });
    const qt = renderHook(() => useQtCommands(), { wrapper }).result;
    act(() => {
      qt.current.openDialog("open-game");
      qt.current.openDialog("stats");
      qt.current.openLink("github");
    });
    await waitFor(() => expect(calls).toHaveLength(3));
    expect(calls.map((c) => c.path).sort()).toEqual([
      "/native/open",
      "/native/open-link/github",
      "/qt/dialogs/stats",
    ]);
  });
});

describe("helpers", () => {
  it("knows the file actions", () => {
    expect(isFileAction("save-game")).toBe(true);
    expect(isFileAction("stats")).toBe(false);
  });

  it("words the outcome of a file action", () => {
    expect(fileResultToast("save", { outcome: "cancelled" })).toEqual({
      title: "Save cancelled",
      tone: "info",
    });
    expect(
      fileResultToast("save", { outcome: "saved", path: "C:/a.retribution" }),
    ).toEqual({
      title: "Campaign saved",
      description: "C:/a.retribution",
      tone: "success",
    });
  });
});

import type { Saves } from "../api/liberationApi";
import { setupStore } from "../app/store";
import { recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { LoadScreen } from "./LoadScreen";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

const SAVES: Saves = {
  saves: [
    {
      id: "takeoff-0012",
      kind: "takeoff",
      turn: 12,
      game_date: "1999-06-14",
      saved_at: "2026-11-08T21:04:00",
      file_name: "takeoff-0012.retribution",
    },
    {
      id: "turn-0012",
      kind: "turn",
      turn: 12,
      game_date: "1999-06-14",
      saved_at: "2026-11-08T20:30:00",
      file_name: "turn-0012.retribution",
    },
    {
      id: "manual-0123456789ab",
      kind: "manual",
      turn: 11,
      game_date: "1999-06-13",
      saved_at: "2026-11-07T22:00:00",
      file_name: "Quasar.retribution",
    },
  ],
  previous_turn_id: "takeoff-0012",
};

function renderLoad(saves: Saves | null = SAVES) {
  const calls = recordFetch(
    200,
    { outcome: "opened", path: "C:/x.retribution" },
    { "/saves/": saves },
  );
  const router = createMemoryRouter(
    [
      { path: "/load", element: <LoadScreen /> },
      { path: "/", element: <p>Command view</p> },
    ],
    { initialEntries: ["/load"] },
  );
  render(
    <Provider store={setupStore()}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </Provider>,
  );
  return { calls, router };
}

describe("LoadScreen (#190)", () => {
  it("lists the saves with their turn, date and kind", async () => {
    renderLoad();
    const table = await screen.findByRole("table", { name: "Saves" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent("Before take off");
    expect(rows[0]).toHaveTextContent("12");
    expect(rows[0]).toHaveTextContent("1999-06-14");
    expect(rows[1]).toHaveTextContent("Start of turn");
    expect(rows[2]).toHaveTextContent("Saved by you");
    expect(rows[2]).toHaveTextContent("Quasar.retribution");
  });

  it("loads a save only once the player confirms", async () => {
    const { calls } = renderLoad();
    const table = await screen.findByRole("table", { name: "Saves" });
    const row = within(table).getAllByRole("row")[2];
    await userEvent.click(within(row).getByRole("button", { name: "Load" }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Progress since your last save is lost");
    expect(calls).toHaveLength(0);
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Load this save" }),
    );

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/saves/turn-0012/load",
    });
    expect(await screen.findByText("Campaign loaded")).toBeInTheDocument();
  });

  it("goes back a turn from the previous turn's save", async () => {
    const { calls } = renderLoad();
    await userEvent.click(
      await screen.findByRole("button", { name: "Restore the previous turn" }),
    );
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Load this save" }),
    );
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe("/saves/takeoff-0012/load");
  });

  it("has nothing to restore without a previous turn", async () => {
    renderLoad({ saves: [] });
    expect(await screen.findByText(/No saves yet/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Restore the previous turn" }),
    ).toBeDisabled();
  });
});

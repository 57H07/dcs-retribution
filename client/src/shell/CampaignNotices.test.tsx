import { setupStore } from "../app/store";
import { topBar } from "../command/testdata";
import { recordFetch, restoreFetch } from "./testing";
import { CampaignNotices } from "./CampaignNotices";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

function renderNotices(bar: ReturnType<typeof topBar>) {
  recordFetch(204, undefined, { "/game/top-bar": bar });
  const router = createMemoryRouter([
    { path: "/", element: <CampaignNotices /> },
    { path: "/new-game", element: <p>Wizard</p> },
  ]);
  render(
    <Provider store={setupStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
}

test("nothing to say during a campaign", async () => {
  renderNotices(topBar());
  await new Promise((resolve) => setTimeout(resolve, 50));
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("a won campaign offers a new one", async () => {
  renderNotices(topBar({ campaign_state: "win" }));
  expect(await screen.findByText("Victory!")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "New campaign" }));
  expect(await screen.findByText("Wizard")).toBeInTheDocument();
});

test("a lost campaign can stay on screen", async () => {
  renderNotices(topBar({ campaign_state: "loss" }));
  expect(await screen.findByText("Defeat!")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Not now" }));
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("campaign problems are shown once", async () => {
  renderNotices(topBar({ warnings: ["Motorpool at Batumi"] }));
  expect(await screen.findByText("Motorpool at Batumi")).toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByText("Motorpool at Batumi")).toBeNull();
});

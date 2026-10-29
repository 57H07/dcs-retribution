import App from "./App";
import { setupStore } from "./app/store";
import { isWebShell } from "./shell/shellMode";
import { recordFetch, restoreFetch } from "./shell/testing";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";

afterEach(restoreFetch);

function renderApp(search: string) {
  return render(
    <Provider store={setupStore()}>
      <App search={search} />
    </Provider>,
  );
}

test("app renders the bare map embedded in the Qt window by default", () => {
  const { container } = renderApp("?server=[::1]:16880&apiKey=k");
  expect(container.querySelector(".leaflet-container")).not.toBeNull();
  expect(screen.queryByRole("banner")).toBeNull();
});

test("shell=web selects the full web shell", () => {
  expect(isWebShell("?server=x&shell=web")).toBe(true);
  expect(isWebShell("?server=x")).toBe(false);
  expect(isWebShell("?shell=qt")).toBe(false);
});

test("the web shell routes in the hash and keeps the query intact", async () => {
  recordFetch();
  const query = "?server=[::1]:16880&apiKey=k&shell=web";
  window.history.replaceState(null, "", `/index.html${query}`);
  renderApp(query);
  expect(screen.getByRole("banner")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Air Wing" }));
  // The route opened the Qt screen and came back to the command view.
  await waitFor(() => expect(window.location.hash).toBe("#/"));
  expect(window.location.search).toBe(query);
  expect(window.location.pathname).toBe("/index.html");
});

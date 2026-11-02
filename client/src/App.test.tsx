import App from "./App";
import { setupStore } from "./app/store";
import { recordFetch, restoreFetch } from "./shell/testing";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";

afterEach(restoreFetch);

test("the app routes in the hash and keeps the query intact", async () => {
  recordFetch();
  const query = "?server=[::1]:16880&apiKey=k";
  window.history.replaceState(null, "", `/index.html${query}`);
  render(
    <Provider store={setupStore()}>
      <App />
    </Provider>,
  );
  expect(screen.getByRole("banner")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Air Wing" }));
  await waitFor(() => expect(window.location.hash).toBe("#/air-wing"));
  expect(window.location.search).toBe(query);
  expect(window.location.pathname).toBe("/index.html");
});

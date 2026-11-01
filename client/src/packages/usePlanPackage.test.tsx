import { setupStore } from "../app/store";
import { recordFetch, restoreFetch } from "../shell/testing";
import { ToastProvider } from "../ui";
import { usePlanPackage } from "./usePlanPackage";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

afterEach(restoreFetch);

function Picker() {
  const plan = usePlanPackage();
  return (
    <button onClick={() => plan({ target_kind: "tgo", target_id: "sam-1" })}>
      Plan
    </button>
  );
}

function renderPicker() {
  const router = createMemoryRouter(
    [
      {
        path: "*",
        element: (
          <ToastProvider>
            <Picker />
          </ToastProvider>
        ),
      },
    ],
    { initialEntries: ["/"] },
  );
  render(
    <Provider store={setupStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
  return router;
}

describe("planning a package from a map target", () => {
  it("creates the package and opens its editor", async () => {
    const calls = recordFetch(201, { id: "pkg-9" });
    const router = renderPicker();
    await userEvent.click(screen.getByRole("button", { name: "Plan" }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/packages/pkg-9"),
    );
    expect(calls[0]).toMatchObject({
      method: "POST",
      path: "/packages/",
      body: { target_kind: "tgo", target_id: "sam-1" },
    });
  });

  it("stays on the map and tells why when refused", async () => {
    recordFetch(409, { detail: "This target no longer exists." });
    const router = renderPicker();
    await userEvent.click(screen.getByRole("button", { name: "Plan" }));
    expect(
      await screen.findByText("This target no longer exists."),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
  });
});

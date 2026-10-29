// Test helpers of the web shell: a recorded fetch and the shell on a memory router.
import { setupStore } from "../app/store";
import { ROUTES } from "./routes";
import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

export type Call = { method: string; path: string; apiKey: string | null };

const realFetch = globalThis.fetch;

/** Records every API request and answers 204 (or `status` with `body`). */
export function recordFetch(status = 204, body?: unknown): Call[] {
  const calls: Call[] = [];
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    calls.push({
      method: request.method,
      path: new URL(request.url).pathname,
      apiKey: request.headers.get("X-API-Key"),
    });
    return body === undefined
      ? new Response(null, { status })
      : new Response(JSON.stringify(body), {
          status,
          headers: { "Content-Type": "application/json" },
        });
  };
  return calls;
}

export function restoreFetch() {
  globalThis.fetch = realFetch;
}

export function renderShell(path = "/") {
  const router = createMemoryRouter(ROUTES, { initialEntries: [path] });
  const result = render(
    <Provider store={setupStore()}>
      <RouterProvider router={router} />
    </Provider>,
  );
  return { router, ...result };
}

// Test helpers of the web shell: a recorded fetch and the shell on a memory router.
import { setupStore } from "../app/store";
import { ROUTES } from "./routes";
import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

export type Call = {
  method: string;
  path: string;
  apiKey: string | null;
  body: unknown;
};

const realFetch = globalThis.fetch;

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export type Answer = { status?: number; body?: unknown };

/**
 * Records every API command (non-GET request) and answers 204, or `status`
 * with `body`, or `answers[path]` for that path. Reads (GET) are not recorded:
 * they answer `gets[path]`, or null (e.g. no campaign for /game/top-bar).
 */
export function recordFetch(
  status = 204,
  body?: unknown,
  gets: Record<string, unknown> = {},
  answers: Record<string, Answer> = {},
): Call[] {
  const calls: Call[] = [];
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    const path = new URL(request.url).pathname;
    if (request.method === "GET") {
      return json(gets[path] ?? null);
    }
    const text = await request.text();
    calls.push({
      method: request.method,
      path,
      apiKey: request.headers.get("X-API-Key"),
      body: text === "" ? undefined : JSON.parse(text),
    });
    const answer = answers[path] ?? { status, body };
    return answer.body === undefined
      ? new Response(null, { status: answer.status ?? 204 })
      : json(answer.body, answer.status ?? 200);
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

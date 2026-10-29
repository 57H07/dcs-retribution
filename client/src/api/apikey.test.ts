// WEB-00.6: the client reads the server's key once from its URL (or
// VITE_API_KEY) and sends it with every command and on the event stream.
import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios";
import { vi } from "vitest";

type Call = { method: string; url: string; apiKey: string | null };

const realFetch = globalThis.fetch;
let calls: Call[] = [];

function stubFetch(body: unknown) {
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    calls.push({
      method: request.method,
      url: request.url,
      apiKey: request.headers.get("X-API-Key"),
    });
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
}

/** Loads the API modules fresh, as if the page had been opened at `search`. */
async function loadClient(search: string) {
  window.history.replaceState(null, "", `/${search}`);
  vi.resetModules();
  const backend = await import("./backend");
  const { setupStore } = await import("../app/store");
  const { _liberationApi } = await import("./_liberationApi");
  return { ...backend, store: setupStore(), api: _liberationApi };
}

/** Sends one axios request and returns the config it would go out with. */
async function sentConfig(
  send: (adapter: AxiosAdapter) => Promise<unknown>,
): Promise<InternalAxiosRequestConfig> {
  let seen: InternalAxiosRequestConfig | undefined;
  await send(async (config) => {
    seen = config;
    return { data: {}, status: 200, statusText: "OK", headers: {}, config };
  });
  return seen!;
}

beforeEach(() => {
  calls = [];
});

afterEach(() => {
  globalThis.fetch = realFetch;
  vi.unstubAllEnvs();
  window.history.replaceState(null, "", "/");
});

describe("with the key in the URL", () => {
  const search = "?server=[::1]:16880&apiKey=s3cr%2Bt";

  it("reads it once from the apiKey query parameter", async () => {
    const { API_KEY } = await loadClient(search);
    expect(API_KEY).toBe("s3cr+t");
  });

  it("sends it as X-API-Key with generated command hooks", async () => {
    stubFetch({ turn: 2, campaign_state: "continue" });
    const { store, api } = await loadClient(search);

    await store.dispatch(api.endpoints.passTurn.initiate()).unwrap();

    expect(calls).toEqual([
      expect.objectContaining({ method: "POST", apiKey: "s3cr+t" }),
    ]);
  });

  it("does not send it with reads", async () => {
    stubFetch([]);
    const { store, api } = await loadClient(search);

    await store.dispatch(api.endpoints.listControlPoints.initiate()).unwrap();

    expect(calls).toEqual([
      expect.objectContaining({ method: "GET", apiKey: null }),
    ]);
  });

  it("sends it with axios commands only", async () => {
    const { backend } = await loadClient(search);

    const post = await sentConfig((adapter) =>
      backend.post("/qt/info/control-point/1", undefined, { adapter }),
    );
    const get = await sentConfig((adapter) =>
      backend.get("/game/", { adapter }),
    );

    expect(post.headers.get("X-API-Key")).toBe("s3cr+t");
    expect(get.headers.has("X-API-Key")).toBe(false);
  });

  it("opens the event stream with it", async () => {
    const { WEBSOCKET_URL } = await loadClient(search);
    expect(WEBSOCKET_URL).toBe("ws://[::1]:16880/eventstream?apiKey=s3cr%2Bt");
  });
});

describe("started on its own (dev server)", () => {
  it("falls back to VITE_API_KEY", async () => {
    vi.stubEnv("VITE_API_KEY", "dev-key");
    stubFetch({ turn: 2, campaign_state: "continue" });
    const { store, api, WEBSOCKET_URL } = await loadClient("");

    await store.dispatch(api.endpoints.passTurn.initiate()).unwrap();

    expect(calls[0].apiKey).toBe("dev-key");
    expect(WEBSOCKET_URL).toBe("ws://[::1]:16880/eventstream?apiKey=dev-key");
  });

  it("sends no key when none is configured", async () => {
    vi.stubEnv("VITE_API_KEY", undefined);
    stubFetch({ turn: 2, campaign_state: "continue" });
    const { store, api, WEBSOCKET_URL } = await loadClient("");

    await store.dispatch(api.endpoints.passTurn.initiate()).unwrap();

    expect(calls[0].apiKey).toBeNull();
    expect(WEBSOCKET_URL).toBe("ws://[::1]:16880/eventstream");
  });
});

describe("isCommandMethod", () => {
  it("treats POST, PUT, PATCH and DELETE as commands", async () => {
    const { isCommandMethod } = await loadClient("");
    for (const method of ["post", "PUT", "patch", "DELETE"]) {
      expect(isCommandMethod(method)).toBe(true);
    }
    for (const method of ["GET", "head", undefined]) {
      expect(isCommandMethod(method)).toBe(false);
    }
  });
});

import { setupStore } from "../app/store";
import { _liberationApi } from "./_liberationApi";
import { commandErrorMessage } from "./commands";

type Call = { method: string; url: string };

const realFetch = globalThis.fetch;
let calls: Call[] = [];

function stubFetch(status: number, body: unknown) {
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    calls.push({ method: request.method, url: request.url });
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  };
}

beforeEach(() => {
  calls = [];
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("passTurn command", () => {
  it("posts to /game/turn/pass and returns the new turn", async () => {
    stubFetch(200, { turn: 3, campaign_state: "continue" });
    const store = setupStore();

    const result = await store
      .dispatch(_liberationApi.endpoints.passTurn.initiate())
      .unwrap();

    expect(result).toEqual({ turn: 3, campaign_state: "continue" });
    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe("POST");
    expect(new URL(calls[0].url).pathname).toBe("/game/turn/pass");
  });

  it("exposes the server's message when the command is refused", async () => {
    stubFetch(409, { detail: "The campaign is over." });
    const store = setupStore();

    const result = await store.dispatch(
      _liberationApi.endpoints.passTurn.initiate(),
    );

    expect("error" in result).toBe(true);
    if ("error" in result) {
      expect(commandErrorMessage(result.error)).toBe("The campaign is over.");
    }
  });
});

describe("commandErrorMessage", () => {
  it("is undefined without an error", () => {
    expect(commandErrorMessage(undefined)).toBeUndefined();
  });

  it("falls back to a generic message without a detail", () => {
    expect(commandErrorMessage({ status: 500, data: "boom" })).toBe(
      "The server could not run the command (500).",
    );
    expect(
      commandErrorMessage({ status: "FETCH_ERROR", error: "offline" }),
    ).toBe("The server could not run the command (FETCH_ERROR).");
  });
});

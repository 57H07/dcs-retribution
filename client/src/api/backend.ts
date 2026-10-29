import axios from "axios";

const params = new URL(window.location.toString()).searchParams;

const backendAddr = params.get("server") ?? "[::1]:16880";

// WEB-00.6: the server's key for this launch. The Qt map passes it in the URL;
// a client started on its own (Vite dev server, Electron) reads VITE_API_KEY,
// matching SERVER_API_KEY in the server's serverconfig.env.
export const API_KEY: string | undefined =
  params.get("apiKey") ?? import.meta.env.VITE_API_KEY ?? undefined;

export const API_KEY_HEADER = "X-API-Key";

const COMMAND_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/**
 * True when a request with this method is a command, which needs the API key.
 * Reads go without it: the server does not ask for it, and a custom header
 * would add a CORS preflight to each of them.
 */
export function isCommandMethod(method: string | undefined): boolean {
  return COMMAND_METHODS.has((method ?? "GET").toUpperCase());
}

export const HTTP_URL = `http://${backendAddr}/`;

export const backend = axios.create({
  baseURL: HTTP_URL,
});

backend.interceptors.request.use((config) => {
  if (API_KEY !== undefined && isCommandMethod(config.method)) {
    config.headers.set(API_KEY_HEADER, API_KEY);
  }
  return config;
});

const websocketQuery =
  API_KEY === undefined ? "" : `?apiKey=${encodeURIComponent(API_KEY)}`;

export const WEBSOCKET_URL = `ws://${backendAddr}/eventstream${websocketQuery}`;

export default backend;

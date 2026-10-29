/**
 * True when the page runs as the full-window web UI (WEB-00.3).
 *
 * QLiberationMap adds `shell=web` to the page URL when the web UI option is on
 * (preference or RETRIBUTION_WEB_UI). Without it the page is the bare map
 * embedded in the Qt window, which keeps its own menus and panels.
 */
export function isWebShell(search: string): boolean {
  return new URLSearchParams(search).get("shell") === "web";
}

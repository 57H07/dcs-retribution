/** Tabs of the reports screen (WEB-08.1), in display order. */
export const REPORT_TABS = ["intel", "stats", "finances"] as const;
export type ReportTab = (typeof REPORT_TABS)[number];

// Paths of the web UI screens (WEB-00.3). They are hash-routed: Qt loads the
// page from file://, and the ?server=&apiKey= query stays untouched before "#".
export const PATHS = {
  command: "/",
  airWing: "/air-wing",
  base: (id: string) => `/bases/${id}`,
  package: (flightId: string) => `/packages/${flightId}`,
  newGame: "/new-game",
  settings: "/settings",
  preferences: "/preferences",
  debrief: "/debrief",
  reports: "/reports",
  reportTab: (tab: ReportTab) => `/reports/${tab}`,
};

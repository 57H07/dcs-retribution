import type { BaseTab, UnitInfo } from "../api/liberationApi";

export type UnitKind = UnitInfo["kind"];

/** Tabs of the base screen (WEB-02.1); the server says which a base has. */
export type BaseTabId = BaseTab["id"];

/** Tabs of the reports screen (WEB-08.1), in display order. */
export const REPORT_TABS = ["intel", "stats", "finances"] as const;
export type ReportTab = (typeof REPORT_TABS)[number];

/** Views of the air wing screen (WEB-03), in display order. */
export const AIR_WING_VIEWS = ["squadrons", "aircraft", "pilots"] as const;
export type AirWingView = (typeof AIR_WING_VIEWS)[number];

// Paths of the web UI screens (WEB-00.3). They are hash-routed: Qt loads the
// page from file://, and the ?server=&apiKey= query stays untouched before "#".
export const PATHS = {
  command: "/",
  airWing: "/air-wing",
  airWingView: (view: AirWingView) => `/air-wing/${view}`,
  airWingConfig: "/air-wing-config",
  base: (id: string) => `/bases/${id}`,
  baseTab: (id: string, tab: BaseTabId) => `/bases/${id}/${tab}`,
  package: (id: string) => `/packages/${id}`,
  newGame: "/new-game",
  settings: "/settings",
  waiting: "/waiting",
  preferences: "/preferences",
  debrief: "/debrief",
  reports: "/reports",
  reportTab: (tab: ReportTab) => `/reports/${tab}`,
  // WEB-08.2
  transfers: "/transfers",
  production: "/production",
  notes: "/notes",
  info: "/info",
  career: "/career",
  logs: "/logs",
  about: "/about",
  // #190
  load: "/load",
  // WEB-08.3
  tgo: (id: string) => `/tgos/${id}`,
  /** Unit info sheet; names hold spaces and sometimes slashes. */
  unit: (kind: UnitKind, name: string) =>
    `/units/${kind}/${encodeURIComponent(name)}`,
};

// Paths of the web UI screens (WEB-00.3). They are hash-routed: Qt loads the
// page from file://, and the ?server=&apiKey= query stays untouched before "#".
export const PATHS = {
  command: "/",
  airWing: "/air-wing",
  base: (id: string) => `/bases/${id}`,
  package: (flightId: string) => `/packages/${flightId}`,
  newGame: "/new-game",
  settings: "/settings",
  waiting: "/waiting",
  debrief: "/debrief",
  reports: "/reports",
};

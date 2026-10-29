// Screens of the web UI (WEB-00.3). Until a screen is migrated, its route opens
// the Qt dialog through /qt/* and comes back to the command view; a migrated
// screen replaces its QtScreen element here (and deletes the Qt dialog, W9).
import { SettingsScreen } from "../settings/SettingsScreen";
import { QtScreen } from "./QtScreen";
import { Shell } from "./Shell";
import { Navigate, RouteObject } from "react-router-dom";

export const ROUTES: RouteObject[] = [
  {
    path: "/",
    element: <Shell />,
    children: [
      // The command view is the map itself, always mounted by the shell.
      { index: true, element: null },
      {
        path: "air-wing",
        element: <QtScreen open={(qt) => qt.openDialog("air-wing")} />,
      },
      {
        path: "bases/:id",
        element: <QtScreen open={(qt, { id }) => id && qt.openBase(id)} />,
      },
      {
        // Packages have no API ID yet (WEB-03): a flight stands for its package.
        path: "packages/:id",
        element: (
          <QtScreen open={(qt, { id }) => id && qt.editPackageOfFlight(id)} />
        ),
      },
      {
        path: "new-game",
        element: <QtScreen open={(qt) => qt.openDialog("new-game")} />,
      },
      {
        path: "settings",
        element: <SettingsScreen />,
      },
      {
        path: "debrief",
        element: <QtScreen open={(qt) => qt.openDialog("debriefing")} />,
      },
      {
        path: "reports",
        element: <QtScreen open={(qt) => qt.openDialog("reports")} />,
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
];

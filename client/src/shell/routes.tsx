// Screens of the web UI (WEB-00.3). Until a screen is migrated, its route opens
// the Qt dialog through /qt/* and comes back to the command view; a migrated
// screen replaces its QtScreen element here (and deletes the Qt dialog, W9).
import { BaseScreen } from "../bases/BaseScreen";
import { DebriefScreen } from "../missionresult/DebriefScreen";
import { WaitingScreen } from "../missionresult/WaitingScreen";
import { PackageEditor } from "../packages/PackageEditor";
import { PreferencesScreen } from "../preferences/PreferencesScreen";
import { ReportsScreen } from "../reports/ReportsScreen";
import { AboutScreen } from "../secondary/AboutScreen";
import { CareerScreen } from "../secondary/CareerScreen";
import { InfoPanelScreen } from "../secondary/InfoPanelScreen";
import { LogsScreen } from "../secondary/LogsScreen";
import { NotesScreen } from "../secondary/NotesScreen";
import { TransfersScreen } from "../secondary/TransfersScreen";
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
        // Base screen (WEB-02.1); purchases and transfers still open the Qt
        // base menu from their tabs until WEB-02.2 and WEB-02.3.
        path: "bases/:id",
        element: <BaseScreen />,
      },
      {
        path: "bases/:id/:tab",
        element: <BaseScreen />,
      },
      {
        // Package editor (WEB-04.1), by Package.id.
        path: "packages/:id",
        element: <PackageEditor />,
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
        // WEB-05.1: after Take off, until the results are accepted or aborted.
        path: "waiting",
        element: <WaitingScreen />,
      },
      {
        path: "preferences",
        element: <PreferencesScreen />,
      },
      {
        // WEB-05.2: the after-action report, before and after acceptance.
        path: "debrief",
        element: <DebriefScreen />,
      },
      {
        // Intel, Stats and Finances (WEB-08.1, W11).
        path: "reports",
        element: <ReportsScreen />,
      },
      {
        path: "reports/:tab",
        element: <ReportsScreen />,
      },
      // Secondary screens (WEB-08.2).
      { path: "transfers", element: <TransfersScreen /> },
      { path: "notes", element: <NotesScreen /> },
      { path: "info", element: <InfoPanelScreen /> },
      { path: "career", element: <CareerScreen /> },
      { path: "logs", element: <LogsScreen /> },
      { path: "about", element: <AboutScreen /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
];

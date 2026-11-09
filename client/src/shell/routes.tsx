// Screens of the web UI (WEB-00.3).
import { AirWingScreen } from "../airwing/AirWingScreen";
import { AirWingConfigScreen } from "../airwingconfig/AirWingConfigScreen";
import { BaseScreen } from "../bases/BaseScreen";
import { DebriefScreen } from "../missionresult/DebriefScreen";
import { WaitingScreen } from "../missionresult/WaitingScreen";
import { NewGameScreen } from "../newgame/NewGameScreen";
import { PackageEditor } from "../packages/PackageEditor";
import { PreferencesScreen } from "../preferences/PreferencesScreen";
import { ReportsScreen } from "../reports/ReportsScreen";
import { AboutScreen } from "../secondary/AboutScreen";
import { CareerScreen } from "../secondary/CareerScreen";
import { InfoPanelScreen } from "../secondary/InfoPanelScreen";
import { LogsScreen } from "../secondary/LogsScreen";
import { LoadScreen } from "../secondary/LoadScreen";
import { NotesScreen } from "../secondary/NotesScreen";
import { ProductionScreen } from "../production/ProductionScreen";
import { TransfersScreen } from "../secondary/TransfersScreen";
import { ObjectivesScreen } from "../secondary/ObjectivesScreen";
import { WarDiaryScreen } from "../secondary/WarDiaryScreen";
import { SettingsScreen } from "../settings/SettingsScreen";
import { TgoScreen } from "../tgos/TgoScreen";
import { UnitInfoScreen } from "../tgos/UnitInfoScreen";
import { Shell } from "./Shell";
import { Navigate, RouteObject } from "react-router-dom";

export const ROUTES: RouteObject[] = [
  {
    path: "/",
    element: <Shell />,
    children: [
      // The command view is the map itself, always mounted by the shell.
      { index: true, element: null },
      // Squadrons, aircraft and pilots (WEB-03).
      { path: "air-wing", element: <AirWingScreen /> },
      { path: "air-wing/:view", element: <AirWingScreen /> },
      // Air wing and factions of the campaign in play, behind a cheat (WEB-06).
      { path: "air-wing-config", element: <AirWingConfigScreen /> },
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
        // New campaign wizard (WEB-06).
        path: "new-game",
        element: <NewGameScreen />,
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
      { path: "production", element: <ProductionScreen /> },
      { path: "notes", element: <NotesScreen /> },
      { path: "load", element: <LoadScreen /> },
      { path: "info", element: <InfoPanelScreen /> },
      { path: "career", element: <CareerScreen /> },
      { path: "diary", element: <WarDiaryScreen /> },
      { path: "objectives", element: <ObjectivesScreen /> },
      { path: "logs", element: <LogsScreen /> },
      { path: "about", element: <AboutScreen /> },
      // Ground object and unit info sheets (WEB-08.3).
      { path: "tgos/:id", element: <TgoScreen /> },
      { path: "units/:kind/:name", element: <UnitInfoScreen /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
];

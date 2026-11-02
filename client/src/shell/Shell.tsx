import { CommandView } from "../command/CommandView";
import { MapInspector } from "../command/inspector/MapInspector";
import LiberationMap from "../components/liberationmap";
import { toggleOverlay } from "../maplayers/layerToggle";
import { MapSelection, packageTarget } from "../maplayers/mapSelection";
import { usePlanPackage } from "../packages/usePlanPackage";
import { FirstStart } from "../preferences/FirstStart";
import { ToastProvider, useToast } from "../ui";
import { AppBar } from "./AppBar";
import { CampaignNotices } from "./CampaignNotices";
import { HelpOverlay } from "./HelpOverlay";
import styles from "./Shell.module.css";
import { ShortcutAction, useShortcuts } from "./shortcuts";
import { useShellCommands } from "./useShellCommands";
import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

/** True while a dialog or menu is open: Escape belongs to it. */
function overlayIsOpen(): boolean {
  return document.querySelector('[role="dialog"], [role="menu"]') !== null;
}

function ShellLayout() {
  const [helpOpen, setHelpOpen] = useState(false);
  const [selection, setSelection] = useState<MapSelection | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const qt = useShellCommands();
  const toast = useToast();
  const planPackage = usePlanPackage();

  const newPackage = () => {
    // The selection only counts while the map is what the player is looking at.
    const target = location.pathname === "/" ? packageTarget(selection) : null;
    if (target) {
      planPackage(target);
      return;
    }
    // A package needs a target: explain how to plan one.
    toast({
      title: "New package",
      description:
        "Select a target on the map and press N, or right-click the target.",
    });
  };

  useShortcuts((action: ShortcutAction) => {
    switch (action.kind) {
      case "close":
        if (!overlayIsOpen() && location.pathname !== "/") {
          navigate("/");
        } else if (!overlayIsOpen()) {
          // On the command view, Escape closes the map inspector.
          setSelection(null);
        }
        break;
      case "layer":
        toggleOverlay(action.overlay);
        break;
      case "newPackage":
        newPackage();
        break;
      case "save":
        qt.openDialog("save-game");
        break;
      case "help":
        setHelpOpen(true);
        break;
    }
  });

  return (
    <div className={styles.shell}>
      <AppBar onNewPackage={newPackage} onShowHelp={() => setHelpOpen(true)} />
      <main className={styles.content}>
        <CommandView
          map={
            <LiberationMap
              onSelect={setSelection}
              onNewPackage={planPackage}
              selection={selection}
              layerToolbar
            />
          }
          inspector={
            <MapInspector
              selection={selection}
              onClose={() => setSelection(null)}
              onPlanPackage={newPackage}
            />
          }
          onNewPackage={newPackage}
        />
        <Outlet />
      </main>
      <HelpOverlay open={helpOpen} onOpenChange={setHelpOpen} />
      <FirstStart />
      <CampaignNotices />
    </div>
  );
}

/** Full-window web UI (WEB-00.3): top bar over the command view (WEB-01.1). */
export function Shell() {
  return (
    <ToastProvider>
      <ShellLayout />
    </ToastProvider>
  );
}

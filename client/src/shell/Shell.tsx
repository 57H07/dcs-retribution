import { CommandView } from "../command/CommandView";
import LiberationMap from "../components/liberationmap";
import { toggleOverlay } from "../maplayers/layerToggle";
import { FirstStart } from "../preferences/FirstStart";
import { ToastProvider, useToast } from "../ui";
import { AppBar } from "./AppBar";
import { HelpOverlay } from "./HelpOverlay";
import styles from "./Shell.module.css";
import { ShortcutAction, useShortcuts } from "./shortcuts";
import { useQtCommands } from "./useQtCommands";
import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

/** True while a dialog or menu is open: Escape belongs to it. */
function overlayIsOpen(): boolean {
  return document.querySelector('[role="dialog"], [role="menu"]') !== null;
}

function ShellLayout() {
  const [helpOpen, setHelpOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const qt = useQtCommands();
  const toast = useToast();

  const newPackage = () => {
    // No target-less package dialog in Qt: explain how to plan one.
    toast({
      title: "New package",
      description: "Right-click a target on the map to plan a package.",
    });
  };

  useShortcuts((action: ShortcutAction) => {
    switch (action.kind) {
      case "close":
        if (!overlayIsOpen() && location.pathname !== "/") {
          navigate("/");
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
        <CommandView map={<LiberationMap />} onNewPackage={newPackage} />
        <Outlet />
      </main>
      <HelpOverlay open={helpOpen} onOpenChange={setHelpOpen} />
      <FirstStart />
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

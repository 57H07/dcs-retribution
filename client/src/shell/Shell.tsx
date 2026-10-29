import LiberationMap from "../components/liberationmap";
import { toggleOverlay } from "../maplayers/layerToggle";
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
    // No target-less package dialog in Qt: show the packages and how to plan.
    qt.openDialog("air-tasking-order");
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
        <div className={styles.map}>
          <LiberationMap />
        </div>
        <Outlet />
      </main>
      <HelpOverlay open={helpOpen} onOpenChange={setHelpOpen} />
    </div>
  );
}

/** Full-window web UI (WEB-00.3): app bar over the command view. */
export function Shell() {
  return (
    <ToastProvider>
      <ShellLayout />
    </ToastProvider>
  );
}

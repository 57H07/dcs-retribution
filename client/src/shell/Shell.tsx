import { CommandView } from "../command/CommandView";
import { MapInspector } from "../command/inspector/MapInspector";
import LiberationMap from "../components/liberationmap";
import { toggleOverlay } from "../maplayers/layerToggle";
import { MapSelection } from "../maplayers/mapSelection";
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
  const [selection, setSelection] = useState<MapSelection | null>(null);
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
          map={<LiberationMap onSelect={setSelection} layerToolbar />}
          inspector={
            <MapInspector
              selection={selection}
              onClose={() => setSelection(null)}
            />
          }
          onOpenPackages={() => qt.openDialog("air-tasking-order")}
        />
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

// What a click on a base or a ground object of the map does (WEB-01.3).
//
// In the web shell, the command view provides a selection handler and the
// click opens the map inspector, whose actions lead to the base (/bases/:id) and
// ground object (/tgos/:id, WEB-08.3) screens. Without it (the bare map embedded in
// the Qt window, Qt mode only), the click opens the Qt dialogs through /qt/info/*.
import backend from "../api/backend";
import { useOpenTgoInfoDialogMutation } from "../api/liberationApi";
import { createContext, useCallback, useContext } from "react";

export type MapSelection =
  | { kind: "controlPoint"; id: string }
  | { kind: "tgo"; id: string };

export type MapSelectHandler = (selection: MapSelection) => void;

export const MapSelectionContext = createContext<MapSelectHandler | null>(null);

/** What the map inspector shows now, if anything. */
export const MapInspectedContext = createContext<MapSelection | null>(null);

/** True while the map inspector shows this ground object. */
export function useIsInspectedTgo(id: string): boolean {
  const inspected = useContext(MapInspectedContext);
  return inspected?.kind === "tgo" && inspected.id === id;
}

/** Opens what a click on a base shows: the inspector, or the Qt dialog. */
export function useInspectControlPoint(): (id: string) => void {
  const select = useContext(MapSelectionContext);
  return useCallback(
    (id: string) => {
      if (select) {
        select({ kind: "controlPoint", id });
      } else {
        backend.post(`/qt/info/control-point/${id}`);
      }
    },
    [select],
  );
}

/** Opens what a click on a ground object shows: the inspector, or Qt. */
export function useInspectTgo(): (id: string) => void {
  const select = useContext(MapSelectionContext);
  const [openInfoDialog] = useOpenTgoInfoDialogMutation();
  return useCallback(
    (id: string) => {
      if (select) {
        select({ kind: "tgo", id });
      } else {
        openInfoDialog({ tgoId: id });
      }
    },
    [select, openInfoDialog],
  );
}

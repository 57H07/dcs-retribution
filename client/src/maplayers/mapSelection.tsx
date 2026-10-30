// What a click on a base or a ground object of the map does (WEB-01.3).
//
// In the web shell, the command view provides a selection handler and the
// click opens the map inspector. Without it (the bare map embedded in the Qt
// window), the click keeps opening the Qt info dialogs through /qt/info/*.
import backend from "../api/backend";
import { useOpenTgoInfoDialogMutation } from "../api/liberationApi";
import { createContext, useCallback, useContext } from "react";

export type MapSelection =
  | { kind: "controlPoint"; id: string }
  | { kind: "tgo"; id: string };

export type MapSelectHandler = (selection: MapSelection) => void;

export const MapSelectionContext = createContext<MapSelectHandler | null>(null);

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

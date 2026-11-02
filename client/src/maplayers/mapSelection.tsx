// What a click on a target of the map does (WEB-01.3).
//
// The command view provides a selection handler and the click opens the map
// inspector, whose actions lead to the base (/bases/:id) and ground object
// (/tgos/:id, WEB-08.3) screens. A package can then be planned on the selection.
import { NewPackage, PackageTargetKind } from "../api/liberationApi";
import { createContext, useCallback, useContext } from "react";

export type MapSelection =
  | { kind: "controlPoint"; id: string }
  | { kind: "tgo"; id: string }
  | { kind: "frontLine"; id: string }
  | { kind: "downedPilot"; id: string };

const PACKAGE_TARGET_KINDS: Record<MapSelection["kind"], PackageTargetKind> = {
  controlPoint: "control-point",
  tgo: "tgo",
  frontLine: "front-line",
  downedPilot: "downed-pilot",
};

/** The package target of what is selected on the map, if anything. */
export function packageTarget(selection: MapSelection | null): NewPackage | null {
  return (
    selection && {
      target_kind: PACKAGE_TARGET_KINDS[selection.kind],
      target_id: selection.id,
    }
  );
}

export type MapSelectHandler = (selection: MapSelection) => void;

export const MapSelectionContext = createContext<MapSelectHandler | null>(null);

export type NewPackageHandler = (target: NewPackage) => void;

/** How the web shell plans a package on a right-clicked target (WEB-04.1). */
export const NewPackageContext = createContext<NewPackageHandler | null>(null);

/** Plans a package on a target, in the web package editor. */
export function useNewPackage(): (kind: PackageTargetKind, id: string) => void {
  const plan = useContext(NewPackageContext);
  return useCallback(
    (kind: PackageTargetKind, id: string) => {
      plan?.({ target_kind: kind, target_id: id });
    },
    [plan],
  );
}

/** What the map inspector shows now, if anything. */
export const MapInspectedContext = createContext<MapSelection | null>(null);

/** True while the map inspector shows this ground object. */
export function useIsInspectedTgo(id: string): boolean {
  const inspected = useContext(MapInspectedContext);
  return inspected?.kind === "tgo" && inspected.id === id;
}

/** True while the map inspector shows this target. */
export function useIsInspected(kind: MapSelection["kind"], id: string): boolean {
  const inspected = useContext(MapInspectedContext);
  return inspected?.kind === kind && inspected.id === id;
}

/** Opens what a click on a target shows: the inspector. */
export function useInspect(kind: MapSelection["kind"]): (id: string) => void {
  const select = useContext(MapSelectionContext);
  return useCallback(
    (id: string) => {
      select?.({ kind, id });
    },
    [kind, select],
  );
}

/** Opens what a click on a base shows: the inspector. */
export function useInspectControlPoint(): (id: string) => void {
  const select = useContext(MapSelectionContext);
  return useCallback(
    (id: string) => {
      select?.({ kind: "controlPoint", id });
    },
    [select],
  );
}

/** Opens what a click on a ground object shows: the inspector. */
export function useInspectTgo(): (id: string) => void {
  const select = useContext(MapSelectionContext);
  return useCallback(
    (id: string) => {
      select?.({ kind: "tgo", id });
    },
    [select],
  );
}

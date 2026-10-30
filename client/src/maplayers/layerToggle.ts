// Programmatic toggling of the map overlays (WEB-00.3), used by the 1-5
// shortcuts and by the layer toolbar of the command view (WEB-01.3).
//
// The overlays live in Leaflet layer controls. Adding or removing the overlay's
// layer on the map is what a click on its checkbox does: the control keeps its
// checkbox in sync and the map fires overlayadd/overlayremove (the legend
// listens to those).
import { OVERLAYS, OverlayId } from "./overlays";
import type { Control, Layer, Map } from "leaflet";

/**
 * Map layer shortcuts 1-5 (W13), in the order of the command view buttons;
 * `label` is the text of the button.
 */
export const LAYER_SHORTCUTS: {
  key: string;
  overlay: OverlayId;
  label: string;
}[] = [
  { key: "1", overlay: "frontLines", label: "Front lines" },
  { key: "2", overlay: "redThreatZonesFull", label: "Threat zones" },
  { key: "3", overlay: "blueFlightPlans", label: "Flight plans" },
  { key: "4", overlay: "supplyRoutes", label: "Supply routes" },
  { key: "5", overlay: "enemySamThreatRange", label: "Ranges" },
];

interface ControlLayerEntry {
  layer: Layer;
  name: string;
  overlay?: boolean;
}

/** Toggles the overlay named `name` in one of `controls`; false if absent. */
export function toggleOverlayInControls(
  map: Pick<Map, "hasLayer" | "addLayer" | "removeLayer">,
  controls: (Control.Layers | null | undefined)[],
  name: string,
): boolean {
  for (const control of controls) {
    const entry = entriesOf(control)?.find((e) => e.overlay && e.name === name);
    if (entry) {
      if (map.hasLayer(entry.layer)) {
        map.removeLayer(entry.layer);
      } else {
        map.addLayer(entry.layer);
      }
      return true;
    }
  }
  return false;
}

/** A layer of a layer control, as the layer toolbar lists it. */
export interface ControlLayerState {
  name: string;
  overlay: boolean;
  active: boolean;
  /** Index of its control in `controls`: 0 = map layers, 1 = debug layers. */
  control: number;
}

// Leaflet keeps the control's entries in the private `_layers` array.
function entriesOf(control: Control.Layers | null | undefined) {
  return (control as unknown as { _layers?: ControlLayerEntry[] })?._layers;
}

/** Every base layer and overlay of `controls`, with whether it is shown. */
export function listLayersInControls(
  map: Pick<Map, "hasLayer">,
  controls: (Control.Layers | null | undefined)[],
): ControlLayerState[] {
  return controls.flatMap((control, index) =>
    (entriesOf(control) ?? []).map((entry) => ({
      name: entry.name,
      overlay: entry.overlay === true,
      active: map.hasLayer(entry.layer),
      control: index,
    })),
  );
}

/** Shows the base layer `name` in place of the current one; false if absent. */
export function selectBaseLayerInControls(
  map: Pick<Map, "hasLayer" | "addLayer" | "removeLayer">,
  controls: (Control.Layers | null | undefined)[],
  name: string,
): boolean {
  for (const control of controls) {
    const bases = (entriesOf(control) ?? []).filter((e) => !e.overlay);
    const chosen = bases.find((e) => e.name === name);
    if (chosen) {
      bases
        .filter((e) => e !== chosen && map.hasLayer(e.layer))
        .forEach((e) => map.removeLayer(e.layer));
      if (!map.hasLayer(chosen.layer)) {
        map.addLayer(chosen.layer);
      }
      return true;
    }
  }
  return false;
}

type OverlayToggler = (name: string) => boolean;

let toggler: OverlayToggler | null = null;

/** The mounted map registers how to toggle its overlays; returns the cleanup. */
export function registerOverlayToggler(fn: OverlayToggler): () => void {
  toggler = fn;
  return () => {
    if (toggler === fn) {
      toggler = null;
    }
  };
}

/** Toggles an overlay of the mounted map; false when no map or no overlay. */
export function toggleOverlay(id: OverlayId): boolean {
  return toggler?.(OVERLAYS[id].name) ?? false;
}

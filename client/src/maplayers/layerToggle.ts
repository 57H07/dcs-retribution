// Programmatic toggling of the map overlays (WEB-00.3), used by the 1-5
// shortcuts and, later, by the layer buttons of the command view (WEB-01.3).
//
// The overlays live in Leaflet layer controls. Adding or removing the overlay's
// layer on the map is what a click on its checkbox does: the control keeps its
// checkbox in sync and the map fires overlayadd/overlayremove (the legend
// listens to those).
import { OVERLAYS, OverlayId } from "./overlays";
import type { Control, Layer, Map } from "leaflet";

/** Map layer shortcuts 1-5 (W13), in the order of the command view buttons. */
export const LAYER_SHORTCUTS: { key: string; overlay: OverlayId }[] = [
  { key: "1", overlay: "frontLines" },
  { key: "2", overlay: "redThreatZonesFull" },
  { key: "3", overlay: "blueFlightPlans" },
  { key: "4", overlay: "supplyRoutes" },
  { key: "5", overlay: "enemySamThreatRange" },
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
    // Leaflet keeps the control's entries in the private `_layers` array.
    const entries = (control as unknown as { _layers?: ControlLayerEntry[] })
      ?._layers;
    const entry = entries?.find((e) => e.overlay && e.name === name);
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

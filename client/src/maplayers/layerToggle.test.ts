import {
  LAYER_SHORTCUTS,
  registerOverlayToggler,
  toggleOverlay,
  toggleOverlayInControls,
} from "./layerToggle";
import { OVERLAYS } from "./overlays";
import type { Control, Layer } from "leaflet";

function fakeMap() {
  const layers = new Set<Layer>();
  return {
    layers,
    hasLayer: (l: Layer) => layers.has(l),
    addLayer(l: Layer) {
      layers.add(l);
      return this as never;
    },
    removeLayer(l: Layer) {
      layers.delete(l);
      return this as never;
    },
  };
}

function control(entries: { name: string; overlay: boolean }[]) {
  const withLayers = entries.map((e) => ({ ...e, layer: {} as Layer }));
  return {
    entries: withLayers,
    control: { _layers: withLayers } as unknown as Control.Layers,
  };
}

describe("toggleOverlayInControls", () => {
  it("adds then removes the named overlay's layer", () => {
    const map = fakeMap();
    const base = control([{ name: "Front lines", overlay: false }]);
    const overlays = control([{ name: "Front lines", overlay: true }]);
    const controls = [null, base.control, overlays.control];

    expect(toggleOverlayInControls(map, controls, "Front lines")).toBe(true);
    // A base layer with the same name is not an overlay: left alone.
    expect(map.layers.has(base.entries[0].layer)).toBe(false);
    expect(map.layers.has(overlays.entries[0].layer)).toBe(true);

    toggleOverlayInControls(map, controls, "Front lines");
    expect(map.layers.size).toBe(0);
  });

  it("reports an unknown overlay", () => {
    expect(toggleOverlayInControls(fakeMap(), [], "Nope")).toBe(false);
  });
});

describe("toggleOverlay", () => {
  it("goes through the registered map toggler", () => {
    const names: string[] = [];
    expect(toggleOverlay("frontLines")).toBe(false);
    const unregister = registerOverlayToggler((name) => {
      names.push(name);
      return true;
    });
    expect(toggleOverlay("supplyRoutes")).toBe(true);
    expect(names).toEqual([OVERLAYS.supplyRoutes.name]);
    unregister();
    expect(toggleOverlay("frontLines")).toBe(false);
  });

  it("binds keys 1 to 5", () => {
    expect(LAYER_SHORTCUTS.map((s) => s.key)).toEqual(["1", "2", "3", "4", "5"]);
  });
});

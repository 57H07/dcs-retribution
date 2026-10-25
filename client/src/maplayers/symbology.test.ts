import {
  DEFAULT_MAP_ZOOM,
  MAX_SYMBOL_SCALE,
  MIN_SYMBOL_SCALE,
  SYMBOL_STYLES,
  StandardIdentity,
  SymbolSet,
  sidc,
  symbolIcon,
  symbolScaleForZoom,
  symbolSizeForZoom,
} from "./symbology";
import { Point } from "leaflet";

const AIRBASE = sidc(
  StandardIdentity.FRIEND,
  SymbolSet.LAND_INSTALLATIONS,
  "airportAirBase",
);

describe("zoom-dependent symbol size", () => {
  it("keeps the configured size at the default zoom", () => {
    expect(symbolScaleForZoom(DEFAULT_MAP_ZOOM)).toBe(1);
    expect(symbolSizeForZoom("tgo", DEFAULT_MAP_ZOOM)).toBe(
      SYMBOL_STYLES.tgo.size,
    );
  });

  it("grows with the zoom within bounds", () => {
    const zooms = [0, 4, 6, 7, 8, 9, 10, 12, 14, 18];
    const scales = zooms.map(symbolScaleForZoom);
    scales.slice(1).forEach((scale, i) => {
      expect(scale).toBeGreaterThanOrEqual(scales[i]);
    });
    expect(Math.min(...scales)).toBe(MIN_SYMBOL_SCALE);
    expect(Math.max(...scales)).toBe(MAX_SYMBOL_SCALE);
  });

  it("is smaller at theatre view than at airfield view", () => {
    expect(symbolSizeForZoom("controlPoint", 6)).toBeLessThan(
      symbolSizeForZoom("controlPoint", 12),
    );
  });
});

describe("symbolIcon", () => {
  it("reuses the same icon for the same symbol and zoom", () => {
    expect(symbolIcon(AIRBASE, "controlPoint", 10)).toBe(
      symbolIcon(AIRBASE, "controlPoint", 10),
    );
  });

  it("builds a larger icon when zoomed in", () => {
    const anchorX = (zoom: number) =>
      (symbolIcon(AIRBASE, "controlPoint", zoom).options.iconAnchor as Point).x;
    expect(anchorX(12)).toBeGreaterThan(anchorX(5));
  });

  it("anchors tooltips beside the symbol", () => {
    const options = symbolIcon(AIRBASE, "tgo").options;
    const iconAnchor = options.iconAnchor as Point;
    const tooltipAnchor = options.tooltipAnchor as Point;
    expect(tooltipAnchor.x).toBeGreaterThanOrEqual(iconAnchor.x);
  });
});

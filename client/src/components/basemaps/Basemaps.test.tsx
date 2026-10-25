// Must come before leaflet: lets Leaflet draw the offline basemap polygons.
import "../../testutils/leafletSvg";
import { renderWithProviders } from "../../testutils";
import Basemaps, {
  OFFLINE_BASEMAP_NAME,
  OnlineLayerRenderer,
} from "./Basemaps";
import { TILE_ERROR_THRESHOLD, TileHealth } from "./tileHealth";
import { act, screen } from "@testing-library/react";
import { Layer, Map, TileLayer as LeafletTileLayer } from "leaflet";
import { createRef } from "react";
import { LayersControl, MapContainer, TileLayer } from "react-leaflet";

// Plain tile layers stand in for the Esri basemaps: no network in tests.
const renderTiles: OnlineLayerRenderer = (basemap, ref) => (
  <TileLayer
    url={`https://tiles.invalid/${basemap.esriName}/{z}/{x}/{y}.png`}
    ref={ref}
  />
);

const SQUARE = [
  [
    { lat: 41, lng: 41 },
    { lat: 41, lng: 43 },
    { lat: 43, lng: 43 },
    { lat: 43, lng: 41 },
  ],
];

function renderMap() {
  const map = createRef<Map>();
  renderWithProviders(
    <MapContainer center={[42, 42]} zoom={8} ref={map}>
      <LayersControl>
        <Basemaps renderOnline={renderTiles} />
      </LayersControl>
    </MapContainer>,
    {
      preloadedState: {
        mapZones: { mapZones: { inclusion: [SQUARE], exclusion: [], sea: [] } },
      },
    },
  );
  return map.current!;
}

function tileLayersOn(map: Map): LeafletTileLayer[] {
  const layers: LeafletTileLayer[] = [];
  map.eachLayer((layer: Layer) => {
    if (layer instanceof LeafletTileLayer) {
      layers.push(layer);
    }
  });
  return layers;
}

function fireTileErrors(layer: LeafletTileLayer, count: number) {
  act(() => {
    for (let i = 0; i < count; i++) {
      layer.fire("tileerror", { tile: document.createElement("img") });
    }
  });
}

describe("TileHealth", () => {
  it("falls back after consecutive errors only", () => {
    const health = new TileHealth(3);
    expect(health.recordError()).toBe(false);
    expect(health.recordError()).toBe(false);
    health.recordLoad();
    expect(health.recordError()).toBe(false);
    expect(health.recordError()).toBe(false);
    expect(health.recordError()).toBe(true);
  });
});

describe("Basemaps", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("starts on the first online basemap", () => {
    const map = renderMap();
    expect(tileLayersOn(map)).toHaveLength(1);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("lists the offline basemap in the layer control", () => {
    renderMap();
    expect(
      screen.getByText(OFFLINE_BASEMAP_NAME, { exact: false }),
    ).toBeTruthy();
  });

  it("switches to the offline basemap when tiles fail", () => {
    const map = renderMap();
    const [online] = tileLayersOn(map);

    fireTileErrors(online, TILE_ERROR_THRESHOLD);

    expect(map.hasLayer(online)).toBe(false);
    expect(tileLayersOn(map)).toHaveLength(0);
    expect(screen.getByRole("status").textContent).toMatch(/offline/i);
    const pane = map.getPane("offlineBasemap");
    expect(pane?.querySelector("path")).not.toBeNull();
  });

  it("ignores isolated tile errors", () => {
    const map = renderMap();
    const [online] = tileLayersOn(map);

    fireTileErrors(online, TILE_ERROR_THRESHOLD - 1);
    act(() => {
      online.fire("tileload", { tile: document.createElement("img") });
    });
    fireTileErrors(online, TILE_ERROR_THRESHOLD - 1);

    expect(map.hasLayer(online)).toBe(true);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("starts on the offline basemap without network", () => {
    jest.spyOn(window.navigator, "onLine", "get").mockReturnValue(false);
    const map = renderMap();
    expect(tileLayersOn(map)).toHaveLength(0);
    expect(screen.getByRole("status")).toBeTruthy();
  });
});

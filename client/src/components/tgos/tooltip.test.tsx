import { Tgo as TgoModel } from "../../api/liberationApi";
import {
  MapInspectedContext,
  MapSelection,
} from "../../maplayers/mapSelection";
import { renderWithProviders } from "../../testutils";
import Tgo from "./Tgo";
import { Layer, Map, Marker } from "leaflet";
import { createRef } from "react";
import { MapContainer } from "react-leaflet";

function tgo(overrides: Partial<TgoModel> = {}): TgoModel {
  return {
    id: "tgo-1",
    name: "SA-10",
    control_point_name: "Krymsk",
    category: "aa",
    blue: true,
    position: { lat: 42, lng: 42 },
    units: ["Launcher"],
    threat_ranges: [],
    detection_ranges: [],
    dead: false,
    sidc: "10031500001301000000",
    mobile: false,
    ...overrides,
  };
}

function App(props: {
  mapRef: React.Ref<Map>;
  model: TgoModel;
  inspected: MapSelection | null;
}) {
  return (
    <MapInspectedContext.Provider value={props.inspected}>
      <MapContainer center={[42, 42]} zoom={8} ref={props.mapRef}>
        <Tgo tgo={props.model} />
      </MapContainer>
    </MapInspectedContext.Provider>
  );
}

function marker(map: Map): Marker {
  const markers: Marker[] = [];
  map.eachLayer((layer: Layer) => {
    if (layer instanceof Marker) {
      markers.push(layer);
    }
  });
  return markers[0];
}

describe("hover tooltip of a ground object", () => {
  const self: MapSelection = { kind: "tgo", id: "tgo-1" };
  const other: MapSelection = { kind: "tgo", id: "tgo-2" };

  function renderTgo(model: TgoModel, inspected: MapSelection | null) {
    const map = createRef<Map>();
    const view = renderWithProviders(
      <App mapRef={map} model={model} inspected={inspected} />,
    );
    return {
      map: map.current!,
      inspect: (next: MapSelection | null) =>
        view.rerender(<App mapRef={map} model={model} inspected={next} />),
    };
  }

  it("goes away while the inspector shows this site, and comes back", () => {
    const { map, inspect } = renderTgo(tgo(), null);
    expect(marker(map).getTooltip()).toBeTruthy();
    inspect(self);
    expect(marker(map).getTooltip()).toBeFalsy();
    inspect(null);
    expect(marker(map).getTooltip()).toBeTruthy();
  });

  it("stays while the inspector shows another site", () => {
    const { map } = renderTgo(tgo(), other);
    expect(marker(map).getTooltip()).toBeTruthy();
  });

  it("is transparent on a ship, which needs it to drag", () => {
    const { map, inspect } = renderTgo(tgo({ mobile: true }), self);
    const opacity = () => marker(map).getTooltip()?.options.opacity;
    expect(opacity()).toBe(0);
    inspect(other);
    expect(opacity()).toBe(0.9);
  });
});

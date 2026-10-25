// Current map zoom, shared with the symbol layers so that their symbols scale
// with it (GFX-04.5). One zoom listener for the whole map instead of one per
// marker.
import { SymbolStyleKey, DEFAULT_MAP_ZOOM, symbolIcon } from "./symbology";
import { Icon } from "leaflet";
import { PropsWithChildren, createContext, useContext, useState } from "react";
import { useMap, useMapEvents } from "react-leaflet";

const MapZoomContext = createContext<number>(DEFAULT_MAP_ZOOM);

// Must be rendered inside a <MapContainer>.
export function MapZoomProvider(props: PropsWithChildren<{}>) {
  const map = useMap();
  const [zoom, setZoom] = useState(() => Math.round(map.getZoom()));
  useMapEvents({ zoomend: () => setZoom(Math.round(map.getZoom())) });
  return (
    <MapZoomContext.Provider value={zoom}>
      {props.children}
    </MapZoomContext.Provider>
  );
}

export function useMapZoom(): number {
  return useContext(MapZoomContext);
}

// Symbol icon sized for the current zoom.
export function useSymbolIcon(sidc: string, style: SymbolStyleKey): Icon {
  return symbolIcon(sidc, style, useMapZoom());
}

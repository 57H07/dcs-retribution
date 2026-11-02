import { LatLngLiteral, Map } from "leaflet";
import { useEffect } from "react";

/**
 * Centres the map when a campaign gives it a new center, keeping the zoom. Any
 * other render leaves the map where the player moved it.
 */
export function useRecenterOnGame(map: Map | null, center: LatLngLiteral) {
  useEffect(() => {
    map?.setView(center, map.getZoom() ?? 8, {
      animate: true,
      duration: 1,
    });
  }, [map, center]);
}

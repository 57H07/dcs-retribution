// Map of the Route tab (WEB-04.4, mockups/Package.dc.html): the path of the flight over
// the enemy threat zones. A waypoint the engine lets move is dragged to its new place.
import { FlightRoute, FlightRouteWaypoint } from "../../api/liberationApi";
import Basemaps from "../../components/basemaps";
import {
  ThreatZoneFilter,
  ThreatZonesLayer,
} from "../../components/threatzones/ThreatZonesLayer";
import { color } from "../../ui";
import styles from "./RouteTab.module.css";
import { divIcon, latLngBounds, LatLngLiteral, Marker as LMarker } from "leaflet";
import "leaflet/dist/leaflet.css";
import { useState } from "react";
import { LayersControl, MapContainer, Marker, Polyline } from "react-leaflet";

export interface RouteMapProps {
  route: FlightRoute;
  selectedIndex?: number;
  onSelect: (index: number) => void;
  /** Resolves to false when the engine refused the move. */
  onMove: (index: number, position: LatLngLiteral) => Promise<boolean>;
}

function markerIcon(waypoint: FlightRouteWaypoint, selected: boolean) {
  const classes = [styles.marker];
  if (selected) {
    classes.push(styles.markerSelected);
  }
  if (!waypoint.is_movable) {
    classes.push(styles.markerFixed);
  }
  return divIcon({
    className: classes.join(" "),
    html: String(waypoint.index),
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

export function RouteMap({
  route,
  selectedIndex,
  onSelect,
  onMove,
}: RouteMapProps) {
  const flown = route.waypoints.filter((waypoint) => waypoint.include_in_path);
  const path = flown.map((waypoint) => waypoint.position);
  // A map's view is only read once: moving a waypoint must not move the map.
  const [bounds] = useState(() => latLngBounds(path));

  return (
    <MapContainer
      className={styles.map}
      bounds={bounds}
      boundsOptions={{ padding: [24, 24] }}
      zoomControl={false}
      aria-label="Route map"
    >
      <LayersControl position="topright">
        <Basemaps />
      </LayersControl>
      <ThreatZonesLayer blue={!route.blue} filter={ThreatZoneFilter.FULL} />
      <Polyline
        positions={path}
        pathOptions={{ color: color.accent, weight: 2.5 }}
        interactive={false}
      />
      {flown.map((waypoint) => (
        <Marker
          key={waypoint.index}
          position={waypoint.position}
          icon={markerIcon(waypoint, waypoint.index === selectedIndex)}
          title={waypoint.name}
          draggable={waypoint.is_movable}
          eventHandlers={{
            click: () => onSelect(waypoint.index),
            dragend: async (event) => {
              const marker: LMarker = event.target;
              const { lat, lng } = marker.getLatLng();
              if (!(await onMove(waypoint.index, { lat, lng }))) {
                marker.setLatLng(waypoint.position);
              }
            },
          }}
        />
      ))}
    </MapContainer>
  );
}

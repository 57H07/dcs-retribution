import { overlayProps } from "../../maplayers/overlays";
import { ThreatZoneFilter, ThreatZonesLayer } from "./ThreatZonesLayer";
import { LayersControl } from "react-leaflet";

interface CoalitionThreatZonesProps {
  blue: boolean;
}

export function CoalitionThreatZones(props: CoalitionThreatZonesProps) {
  const overlays = props.blue
    ? {
        full: overlayProps("blueThreatZonesFull"),
        aircraft: overlayProps("blueThreatZonesAircraft"),
        airDefenses: overlayProps("blueThreatZonesAirDefenses"),
        radarSams: overlayProps("blueThreatZonesRadarSams"),
      }
    : {
        full: overlayProps("redThreatZonesFull"),
        aircraft: overlayProps("redThreatZonesAircraft"),
        airDefenses: overlayProps("redThreatZonesAirDefenses"),
        radarSams: overlayProps("redThreatZonesRadarSams"),
      };
  return (
    <>
      <LayersControl.Overlay {...overlays.full}>
        <ThreatZonesLayer blue={props.blue} filter={ThreatZoneFilter.FULL} />
      </LayersControl.Overlay>
      <LayersControl.Overlay {...overlays.aircraft}>
        <ThreatZonesLayer
          blue={props.blue}
          filter={ThreatZoneFilter.AIRCRAFT}
        />
      </LayersControl.Overlay>
      <LayersControl.Overlay {...overlays.airDefenses}>
        <ThreatZonesLayer
          blue={props.blue}
          filter={ThreatZoneFilter.AIR_DEFENSES}
        />
      </LayersControl.Overlay>
      <LayersControl.Overlay {...overlays.radarSams}>
        <ThreatZonesLayer
          blue={props.blue}
          filter={ThreatZoneFilter.RADAR_SAMS}
        />
      </LayersControl.Overlay>
    </>
  );
}

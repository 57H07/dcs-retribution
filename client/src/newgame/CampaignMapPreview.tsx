// Theater step map (issue #181): the bases and links of the selected campaign on the
// basemap of the running campaign, read only. The engine gives the positions of a
// campaign that is not loaded yet. Offline, the bases stay on a plain background: the
// landmap of the main map needs a loaded campaign.
import { CampaignPreview } from "../api/liberationApi";
import { browserIsOffline } from "../components/basemaps/tileHealth";
import { LAYER_COLORS } from "../maplayers/colors";
import styles from "./NewGame.module.css";
import { useEffect, useState } from "react";
import { BasemapLayer } from "react-esri-leaflet";
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Tooltip,
  useMap,
} from "react-leaflet";

const SIDE_COLORS: Record<string, string> = {
  blue: "#7FB8EE",
  red: "#F08A5D",
  neutral: "#9AA6B0",
};

/** Keeps the whole campaign in view: when another is selected, and when resized. */
function FitCampaign({ preview }: { preview: CampaignPreview }) {
  const map = useMap();
  useEffect(() => {
    const fit = () => {
      map.invalidateSize();
      if (preview.south_west && preview.north_east) {
        map.fitBounds(
          [
            [preview.south_west.lat, preview.south_west.lng],
            [preview.north_east.lat, preview.north_east.lng],
          ],
          { padding: [48, 48], maxZoom: 10 },
        );
      }
    };
    fit();
    if (typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver(fit);
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map, preview]);
  return null;
}

function useOffline(): boolean {
  const [offline, setOffline] = useState(browserIsOffline);
  useEffect(() => {
    const update = () => setOffline(browserIsOffline());
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  return offline;
}

export function CampaignMapPreview({ preview }: { preview: CampaignPreview }) {
  const offline = useOffline();
  return (
    <div
      className={styles.previewMap}
      role="img"
      aria-label={`Campaign map preview: ${preview.blue_bases} friendly bases, ${preview.red_bases} enemy bases, ${preview.front_lines} front lines`}
    >
      <MapContainer center={[0, 0]} zoom={8} zoomControl={false}>
        <FitCampaign preview={preview} />
        {!offline && <BasemapLayer name="DarkGray" />}
        {preview.links.map((link) => {
          const from = preview.bases[link.from_index];
          const to = preview.bases[link.to_index];
          return (
            <Polyline
              key={`${from.name}-${to.name}`}
              positions={[from.position, to.position]}
              interactive={false}
              pathOptions={
                link.front_line
                  ? { color: LAYER_COLORS.frontLine, weight: 6 }
                  : { color: "#9AA6B0", weight: 2, dashArray: "6 5" }
              }
            />
          );
        })}
        {preview.bases.map((base) => (
          <CircleMarker
            key={base.name}
            center={base.position}
            radius={8}
            pathOptions={{
              color: "#0B0F12",
              weight: 2,
              fillColor: SIDE_COLORS[base.side] ?? SIDE_COLORS.neutral,
              fillOpacity: 1,
            }}
          >
            <Tooltip permanent direction="right" offset={[8, 0]}>
              {base.name}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
      {offline && (
        <p className={styles.previewOffline} role="status">
          Offline: no terrain on this preview.
        </p>
      )}
    </div>
  );
}

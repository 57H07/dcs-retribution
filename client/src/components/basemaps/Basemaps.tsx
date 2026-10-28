// Base layers of the campaign map: the online Esri basemaps plus an offline
// basemap drawn from the theatre landmap (GFX-04.1). Theatres whose landmap is
// too heavy to draw as polygons (Falklands) get a precomputed image of it
// instead (GFX-04.2).
//
// The map falls back to the offline basemap on its own when the browser is
// offline or the online tiles keep failing, and shows a discreet banner while
// the offline basemap is displayed. It can also be selected by hand in the
// layer control.
import { OfflineBasemapImage } from "../../api/_liberationApi";
import { HTTP_URL } from "../../api/backend";
import { selectMapZones } from "../../api/mapZonesSlice";
import { useAppSelector } from "../../app/hooks";
import { OFFLINE_BASEMAP_COLORS } from "../../maplayers/colors";
import "./Basemaps.css";
import { TileHealth, browserIsOffline } from "./tileHealth";
import {
  Layer,
  LayerGroup as LeafletLayerGroup,
  LayersControlEvent,
} from "leaflet";
import {
  ComponentProps,
  ReactNode,
  forwardRef,
  useEffect,
  useRef,
  useState,
} from "react";
import { BasemapLayer } from "react-esri-leaflet";
import {
  ImageOverlay,
  LayerGroup,
  LayersControl,
  Pane,
  Polygon,
  useMap,
} from "react-leaflet";

type EsriBasemapName = ComponentProps<typeof BasemapLayer>["name"];

export interface OnlineBasemap {
  label: string;
  esriName: EsriBasemapName;
}

export const ONLINE_BASEMAPS: OnlineBasemap[] = [
  { label: "Imagery Clarity", esriName: "ImageryClarity" },
  { label: "Imagery Firefly", esriName: "ImageryFirefly" },
  { label: "Topographic", esriName: "Topographic" },
];

export const OFFLINE_BASEMAP_NAME = "Offline (theatre landmap)";
const OFFLINE_PANE = "offlineBasemap";

export type OnlineLayerRenderer = (
  basemap: OnlineBasemap,
  ref: (layer: Layer | null) => void,
) => ReactNode;

const renderEsriBasemap: OnlineLayerRenderer = (basemap, ref) => (
  <BasemapLayer name={basemap.esriName} ref={ref} />
);

// "#abc" or "#aabbcc" -> "aabbcc"; anything else is left to the server's
// default colour.
function hexParam(color: string): string | undefined {
  const short = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/i.exec(color);
  if (short) {
    return short
      .slice(1)
      .map((c) => c + c)
      .join("");
  }
  return /^#[0-9a-f]{6}$/i.test(color) ? color.slice(1) : undefined;
}

// URL of the precomputed basemap image, in the offline basemap colours.
export function offlineBasemapImageUrl(): string {
  const params = new URLSearchParams();
  const colors: [string, string][] = [
    ["sea", OFFLINE_BASEMAP_COLORS.sea],
    ["land", OFFLINE_BASEMAP_COLORS.land],
    ["land_excluded", OFFLINE_BASEMAP_COLORS.landExcluded],
    ["coastline", OFFLINE_BASEMAP_COLORS.coastline],
  ];
  colors.forEach(([name, color]) => {
    const value = hexParam(color);
    if (value !== undefined) {
      params.set(name, value);
    }
  });
  return `${HTTP_URL}map-zones/offline-basemap?${params}`;
}

function PrecomputedBasemap(props: { image: OfflineBasemapImage }) {
  const { south_west, north_east } = props.image;
  return (
    <ImageOverlay
      url={offlineBasemapImageUrl()}
      bounds={[
        [south_west.lat, south_west.lng],
        [north_east.lat, north_east.lng],
      ]}
      interactive={false}
    />
  );
}

// Land and sea of the theatre, styled as a plain basemap. Drawn in its own
// pane, below the game layers.
export const OfflineBasemapLayer = forwardRef<LeafletLayerGroup>(
  function OfflineBasemapLayer(_props, ref) {
    const zones = useAppSelector(selectMapZones).mapZones;
    const fill = (fillColor: string) => ({
      fillColor,
      fillOpacity: 1,
      interactive: false,
    });
    if (zones.offline_image) {
      return (
        <LayerGroup ref={ref}>
          <Pane name={OFFLINE_PANE} style={{ zIndex: 150 }}>
            <PrecomputedBasemap image={zones.offline_image} />
          </Pane>
        </LayerGroup>
      );
    }
    return (
      <LayerGroup ref={ref}>
        <Pane name={OFFLINE_PANE} style={{ zIndex: 150 }}>
          <Polygon
            positions={zones.sea}
            pathOptions={{ ...fill(OFFLINE_BASEMAP_COLORS.sea), stroke: false }}
          />
          <Polygon
            positions={zones.inclusion}
            pathOptions={{
              ...fill(OFFLINE_BASEMAP_COLORS.land),
              color: OFFLINE_BASEMAP_COLORS.coastline,
              weight: 1,
            }}
          />
          <Polygon
            positions={zones.exclusion}
            pathOptions={{
              ...fill(OFFLINE_BASEMAP_COLORS.landExcluded),
              stroke: false,
            }}
          />
        </Pane>
      </LayerGroup>
    );
  },
);

export function OfflineBanner(props: { automatic: boolean }) {
  return (
    <div className="offline-banner" role="status">
      {props.automatic
        ? "Offline: online map tiles are unavailable, showing the theatre landmap."
        : "Offline basemap: theatre landmap."}
    </div>
  );
}

interface BasemapsProps {
  // Renders the layer of an online basemap. Injected by tests.
  renderOnline?: OnlineLayerRenderer;
}

// Must be rendered inside a <LayersControl>.
export default function Basemaps({
  renderOnline = renderEsriBasemap,
}: BasemapsProps) {
  const map = useMap();
  const online = useRef<(Layer | null)[]>([]);
  const offline = useRef<LeafletLayerGroup>(null);
  const [offlineShown, setOfflineShown] = useState(false);
  const [automatic, setAutomatic] = useState(false);

  useEffect(() => {
    const offlineLayer = offline.current;
    if (offlineLayer === null) {
      return;
    }
    const onlineLayers = online.current.filter(
      (layer): layer is Layer => layer !== null,
    );
    const health = new TileHealth();

    const fallBack = () => {
      if (map.hasLayer(offlineLayer)) {
        return;
      }
      onlineLayers.forEach((layer) => {
        if (map.hasLayer(layer)) {
          map.removeLayer(layer);
        }
      });
      setAutomatic(true);
      map.addLayer(offlineLayer);
    };
    const onTileError = () => {
      if (health.recordError()) {
        fallBack();
      }
    };
    const onTileLoad = () => health.recordLoad();
    const onOfflineAdd = () => {
      map.getContainer().style.background = OFFLINE_BASEMAP_COLORS.sea;
      setOfflineShown(true);
    };
    const onOfflineRemove = () => {
      map.getContainer().style.background = "";
      setOfflineShown(false);
    };
    const onBaseLayerChange = (e: LayersControlEvent) => {
      if (e.layer !== offlineLayer) {
        // Back on an online basemap: give it a fresh chance.
        health.reset();
        setAutomatic(false);
      }
    };

    onlineLayers.forEach((layer) =>
      layer.on({ tileerror: onTileError, tileload: onTileLoad }),
    );
    offlineLayer.on({ add: onOfflineAdd, remove: onOfflineRemove });
    map.on("baselayerchange", onBaseLayerChange);
    window.addEventListener("offline", fallBack);
    if (map.hasLayer(offlineLayer)) {
      onOfflineAdd();
    } else if (browserIsOffline()) {
      fallBack();
    }

    return () => {
      onlineLayers.forEach((layer) =>
        layer.off({ tileerror: onTileError, tileload: onTileLoad }),
      );
      offlineLayer.off({ add: onOfflineAdd, remove: onOfflineRemove });
      map.off("baselayerchange", onBaseLayerChange);
      window.removeEventListener("offline", fallBack);
    };
  }, [map]);

  return (
    <>
      {ONLINE_BASEMAPS.map((basemap, index) => (
        <LayersControl.BaseLayer
          key={basemap.label}
          name={basemap.label}
          checked={index === 0}
        >
          {renderOnline(basemap, (layer) => {
            online.current[index] = layer;
          })}
        </LayersControl.BaseLayer>
      ))}
      <LayersControl.BaseLayer name={OFFLINE_BASEMAP_NAME}>
        <OfflineBasemapLayer ref={offline} />
      </LayersControl.BaseLayer>
      {offlineShown && <OfflineBanner automatic={automatic} />}
    </>
  );
}

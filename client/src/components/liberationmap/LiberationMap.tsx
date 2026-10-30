import { selectMapCenter } from "../../api/mapSlice";
import { useAppSelector } from "../../app/hooks";
import AircraftLayer from "../aircraftlayer";
import AirDefenseRangeLayer from "../airdefenserangelayer";
import Basemaps from "../basemaps";
import EmitterHighlightToggle from "../airdefenserangelayer/EmitterHighlightToggle";
import CombatLayer from "../combatlayer";
import ControlPointsLayer from "../controlpointslayer";
import CullingExclusionZones from "../cullingexclusionzones/CullingExclusionZones";
import DownedPilotsLayer from "../downedpilotslayer";
import FlightPlansLayer from "../flightplanslayer";
import FrontLinesLayer from "../frontlineslayer";
import Iadsnetworklayer from "../iadsnetworklayer";
import NavMeshLayer from "../navmesh/NavMeshLayer";
import LeafletRuler from "../ruler/Ruler";
import SupplyRoutesLayer from "../supplyrouteslayer";
import TerrainZonesLayers from "../terrainzones/TerrainZonesLayers";
import TgosLayer from "../tgoslayer/TgosLayer";
import {
  registerOverlayToggler,
  toggleOverlayInControls,
} from "../../maplayers/layerToggle";
import {
  MapSelectHandler,
  MapSelectionContext,
} from "../../maplayers/mapSelection";
import { overlayProps } from "../../maplayers/overlays";
import { MapZoomProvider } from "../../maplayers/zoom";
import { LayerToolbar } from "../layertoolbar/LayerToolbar";
import Legend from "../legend";
import { CoalitionThreatZones } from "../threatzones";
import { WaypointDebugZonesControls } from "../waypointdebugzones/WaypointDebugZonesControls";
import "./LiberationMap.css";
import { Control, Map } from "leaflet";
import { useCallback, useEffect, useRef, useState } from "react";
import { LayersControl, MapContainer, ScaleControl } from "react-leaflet";

export interface LiberationMapProps {
  /**
   * Web shell (WEB-01.3): a click on a base or a ground object selects it for
   * the inspector instead of opening the Qt info dialog.
   */
  onSelect?: MapSelectHandler;
  /**
   * Web shell (WEB-01.3): compact layer toolbar in place of the expanded
   * Leaflet layer controls, which stay mounted but hidden.
   */
  layerToolbar?: boolean;
}

export default function LiberationMap({
  onSelect,
  layerToolbar = false,
}: LiberationMapProps = {}) {
  const map = useRef<Map | null>(null);
  // The layer toolbar sits beside the map container and needs the map.
  const [leafletMap, setLeafletMap] = useState<Map | null>(null);
  const mapRef = useCallback((instance: Map | null) => {
    map.current = instance;
    setLeafletMap(instance);
  }, []);
  const overlayControl = useRef<Control.Layers>(null);
  const debugControl = useRef<Control.Layers>(null);
  const mapCenter = useAppSelector(selectMapCenter);
  useEffect(() => {
    map.current?.setView(mapCenter, map.current?.getZoom() ?? 8, {
      animate: true,
      duration: 1,
    });
  });
  // Lets the shortcuts (and WEB-01.3's layer buttons) toggle the overlays.
  useEffect(
    () =>
      registerOverlayToggler(
        (name) =>
          map.current !== null &&
          toggleOverlayInControls(
            map.current,
            [overlayControl.current, debugControl.current],
            name,
          ),
      ),
    [],
  );
  const controls = useCallback(
    () => [overlayControl.current, debugControl.current],
    [],
  );
  return (
    <MapSelectionContext.Provider value={onSelect ?? null}>
      <MapContainer
        zoom={map.current?.getZoom() ?? 8}
        zoomControl={false}
        ref={mapRef}
        className={layerToolbar ? "liberation-map--toolbar" : undefined}
      >
        <MapZoomProvider>
          <ScaleControl />
          <LeafletRuler />
          <LayersControl collapsed={false} ref={overlayControl}>
            <Basemaps />
            <LayersControl.Overlay {...overlayProps("controlPoints")}>
              <ControlPointsLayer />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("aircraft")}>
              <AircraftLayer />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("activeCombat")}>
              <CombatLayer />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("blueDownedPilots")}>
              <DownedPilotsLayer blue={true} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("redDownedPilots")}>
              <DownedPilotsLayer blue={false} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("airDefenses")}>
              <TgosLayer categories={["aa"]} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("lorad")}>
              <TgosLayer categories={["aa"]} task={"LORAD"} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("merad")}>
              <TgosLayer categories={["aa"]} task={"MERAD"} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("shorad")}>
              <TgosLayer categories={["aa"]} task={"SHORAD"} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("aaa")}>
              <TgosLayer categories={["aa"]} task={"AAA"} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("factories")}>
              <TgosLayer categories={["factory"]} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("ships")}>
              <TgosLayer categories={["ship"]} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("otherGroundObjects")}>
              <TgosLayer categories={["aa", "factory", "ship"]} exclude />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("supplyRoutes")}>
              <SupplyRoutesLayer />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("frontLines")}>
              <FrontLinesLayer />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("enemySamThreatRange")}>
              <AirDefenseRangeLayer blue={false} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("enemySamDetectionRange")}>
              <AirDefenseRangeLayer blue={false} detection />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("enemyIadsNetwork")}>
              <Iadsnetworklayer blue={false} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("alliedSamThreatRange")}>
              <AirDefenseRangeLayer blue={true} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("alliedSamDetectionRange")}>
              <AirDefenseRangeLayer blue={true} detection />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("emitterHighlight")}>
              <EmitterHighlightToggle />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("alliedIadsNetwork")}>
              <Iadsnetworklayer blue={true} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("selectedFlightPlan")}>
              <FlightPlansLayer selectedOnly />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("blueFlightPlans")}>
              <FlightPlansLayer blue={true} />
            </LayersControl.Overlay>
            <LayersControl.Overlay {...overlayProps("redFlightPlans")}>
              <FlightPlansLayer blue={false} />
            </LayersControl.Overlay>
          </LayersControl>
          <LayersControl position="topleft" ref={debugControl}>
            <CoalitionThreatZones blue={true} />
            <CoalitionThreatZones blue={false} />
            <LayersControl.Overlay name="Blue navmesh">
              <NavMeshLayer blue={true} />
            </LayersControl.Overlay>
            <LayersControl.Overlay name="Red navmesh">
              <NavMeshLayer blue={false} />
            </LayersControl.Overlay>
            <TerrainZonesLayers />
            <CullingExclusionZones />
            <WaypointDebugZonesControls />
          </LayersControl>
          <Legend />
        </MapZoomProvider>
      </MapContainer>
      {layerToolbar && leafletMap && (
        <LayerToolbar map={leafletMap} controls={controls} />
      )}
    </MapSelectionContext.Provider>
  );
}

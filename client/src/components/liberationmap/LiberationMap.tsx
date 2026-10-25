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
import { overlayProps } from "../../maplayers/overlays";
import { MapZoomProvider } from "../../maplayers/zoom";
import Legend from "../legend";
import { CoalitionThreatZones } from "../threatzones";
import { WaypointDebugZonesControls } from "../waypointdebugzones/WaypointDebugZonesControls";
import "./LiberationMap.css";
import { Map } from "leaflet";
import { useEffect, useRef } from "react";
import { LayersControl, MapContainer, ScaleControl } from "react-leaflet";

export default function LiberationMap() {
  const map = useRef<Map>(null);
  const mapCenter = useAppSelector(selectMapCenter);
  useEffect(() => {
    map.current?.setView(mapCenter, map.current?.getZoom() ?? 8, {
      animate: true,
      duration: 1,
    });
  });
  return (
    <MapContainer
      zoom={map.current?.getZoom() ?? 8}
      zoomControl={false}
      ref={map}
    >
      <MapZoomProvider>
        <ScaleControl />
        <LeafletRuler />
        <LayersControl collapsed={false}>
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
        <LayersControl position="topleft">
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
  );
}

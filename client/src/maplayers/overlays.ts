// Overlays of the campaign map layer controls: display name and whether the
// overlay is enabled by default. LiberationMap builds the layer controls from
// these, and the legend uses them to know which layers are active.

interface OverlayDefinition {
  name: string;
  checked: boolean;
}

function defineOverlays<T extends Record<string, OverlayDefinition>>(o: T): T {
  return o;
}

export const OVERLAYS = defineOverlays({
  controlPoints: { name: "Control points", checked: true },
  aircraft: { name: "Aircraft", checked: true },
  activeCombat: { name: "Active combat", checked: true },
  airDefenses: { name: "Air defenses", checked: true },
  lorad: { name: "LORAD", checked: false },
  merad: { name: "MERAD", checked: false },
  shorad: { name: "SHORAD", checked: false },
  aaa: { name: "AAA", checked: false },
  factories: { name: "Factories", checked: true },
  ships: { name: "Ships", checked: true },
  otherGroundObjects: { name: "Other ground objects", checked: true },
  supplyRoutes: { name: "Supply routes", checked: true },
  frontLines: { name: "Front lines", checked: true },
  enemySamThreatRange: { name: "Enemy SAM threat range", checked: true },
  enemySamDetectionRange: { name: "Enemy SAM detection range", checked: false },
  enemyIadsNetwork: { name: "Enemy IADS Network", checked: false },
  alliedSamThreatRange: { name: "Allied SAM threat range", checked: false },
  alliedSamDetectionRange: {
    name: "Allied SAM detection range",
    checked: false,
  },
  emitterHighlight: { name: "Highlight radar emitter on hover", checked: true },
  alliedIadsNetwork: { name: "Allied IADS Network", checked: false },
  selectedFlightPlan: { name: "Selected flight plan", checked: false },
  blueFlightPlans: { name: "All blue flight plans", checked: true },
  redFlightPlans: { name: "All red flight plans", checked: false },
  blueThreatZonesFull: { name: "Blue threat zones: full", checked: false },
  blueThreatZonesAircraft: {
    name: "Blue threat zones: aircraft",
    checked: false,
  },
  blueThreatZonesAirDefenses: {
    name: "Blue threat zones: air defenses",
    checked: false,
  },
  blueThreatZonesRadarSams: {
    name: "Blue threat zones: radar SAMs",
    checked: false,
  },
  redThreatZonesFull: { name: "Red threat zones: full", checked: false },
  redThreatZonesAircraft: {
    name: "Red threat zones: aircraft",
    checked: false,
  },
  redThreatZonesAirDefenses: {
    name: "Red threat zones: air defenses",
    checked: false,
  },
  redThreatZonesRadarSams: {
    name: "Red threat zones: radar SAMs",
    checked: false,
  },
});

export type OverlayId = keyof typeof OVERLAYS;

export const OVERLAY_IDS = Object.keys(OVERLAYS) as OverlayId[];

export function overlayIdForName(name: string): OverlayId | undefined {
  return OVERLAY_IDS.find((id) => OVERLAYS[id].name === name);
}

export function defaultActiveOverlays(): Set<OverlayId> {
  return new Set(OVERLAY_IDS.filter((id) => OVERLAYS[id].checked));
}

// Props for a LayersControl.Overlay: <LayersControl.Overlay {...overlayProps(id)}>
export function overlayProps(id: OverlayId): OverlayDefinition {
  return { name: OVERLAYS[id].name, checked: OVERLAYS[id].checked };
}

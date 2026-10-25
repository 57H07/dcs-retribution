// Single source of truth for the colours drawn by the campaign map layers.
//
// Every layer component reads its colours from LAYER_COLORS, and the map legend
// (components/legend) builds its swatches from the same keys, so the two cannot
// drift apart. A unit test checks that every key below has a legend entry.
//
// Theming (UI-01.2 / GFX-01) is expected to swap these values for design tokens:
// keep layer code referring to the semantic keys, never to the hex values.

// Base palette. Several semantic colours share a value today.
const PALETTE = {
  blue: "#0084ff",
  red: "#c85050",
  violet: "#bb89ff",
  sand: "#eee17b",
  orange: "#fe7d0a",
  yellow: "#ffff00",
  white: "#ffffff",
  navy: "#2d3e50",
  darkRed: "#8c1414",
  lightOrange: "#FFD580",
  skyBlue: "#87CEEB",
  green: "#80BA80",
};

export const LAYER_COLORS = {
  // Threat zones (ThreatZone.tsx) and SAM threat rings (AirDefenseRangeLayer).
  threatBlue: PALETTE.blue,
  threatRed: PALETTE.red,
  // SAM detection rings (AirDefenseRangeLayer).
  detectionBlue: PALETTE.violet,
  detectionRed: PALETTE.sand,
  // Ring and emitter highlighted on hover (AirDefenseRangeLayer).
  emitterHighlight: PALETTE.yellow,
  // Supply routes (SupplyRoute.tsx).
  supplyRouteBlue: PALETTE.navy,
  supplyRouteRed: PALETTE.darkRed,
  supplyRouteFrontActive: PALETTE.red,
  supplyRouteActiveTransport: PALETTE.white,
  // Front lines (FrontLine.tsx).
  frontLine: PALETTE.orange,
  // IADS network links (IadsNetwork.tsx).
  iadsPower: PALETTE.lightOrange,
  iadsCommunication: PALETTE.skyBlue,
  // Flight plans (FlightPlan.tsx).
  flightPlanBlue: PALETTE.blue,
  flightPlanRed: PALETTE.red,
  flightPlanSelected: PALETTE.yellow,
  commitBoundary: PALETTE.yellow,
  // Ongoing combats (Combat.tsx).
  combat: PALETTE.red,
  // Movement orders of mobile control points (MovementPath.tsx).
  movementPath: PALETTE.green,
};

export type LayerColorKey = keyof typeof LAYER_COLORS;

// Line weights and dash patterns that distinguish legend entries.
export const SUPPLY_ROUTE_WEIGHT = { land: 6, sea: 4 };
export const SUPPLY_ROUTE_ACTIVE_WEIGHT = 2;
export const FRONT_LINE_WEIGHT = 16;
export const IADS_INACTIVE_STYLE = { opacity: 0.5, dashArray: "20" };

// Offline basemap drawn from the theatre landmap (GFX-04.1). Kept apart from
// LAYER_COLORS: it is a basemap, not a game layer, and has no legend entry.
export const OFFLINE_BASEMAP_COLORS = {
  sea: "#9db4c8",
  land: "#e4dfd1",
  // Landmap exclusion zones (impassable terrain inside the land mass).
  landExcluded: "#cdc5ae",
  coastline: "#6f8496",
};

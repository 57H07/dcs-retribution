// Content of the map legend, built only from the shared layer constants
// (maplayers/*). Each entry lists the overlays that draw it: the legend shows an
// entry only while at least one of those overlays is active.
import {
  FRONT_LINE_WEIGHT,
  IADS_INACTIVE_STYLE,
  LayerColorKey,
  SUPPLY_ROUTE_ACTIVE_WEIGHT,
  SUPPLY_ROUTE_WEIGHT,
} from "../../maplayers/colors";
import { OverlayId } from "../../maplayers/overlays";
import {
  EntityKey,
  StandardIdentity,
  Status,
  SymbolSet,
  SymbolStyleKey,
  sidc,
} from "../../maplayers/symbology";

export type LegendSwatch =
  | { kind: "symbol"; sidc: string; style: SymbolStyleKey }
  | {
      kind: "line";
      color: LayerColorKey;
      weight: number;
      opacity?: number;
      dashArray?: string;
      // Thin highlight drawn over the line (active supply route).
      overlay?: { color: LayerColorKey; weight: number };
    }
  | { kind: "ring"; color: LayerColorKey; weight: number }
  | { kind: "area"; color: LayerColorKey; fillOpacity: number };

export interface LegendEntry {
  label: string;
  swatch: LegendSwatch;
  overlays: OverlayId[];
}

export interface LegendSection {
  title: string;
  entries: LegendEntry[];
}

const { FRIEND, HOSTILE_FAKER, UNKNOWN } = StandardIdentity;

function symbol(
  label: string,
  overlays: OverlayId[],
  style: SymbolStyleKey,
  identity: StandardIdentity,
  symbolSet: SymbolSet,
  entity: EntityKey,
  status: Status = Status.PRESENT,
): LegendEntry {
  return {
    label,
    overlays,
    swatch: {
      kind: "symbol",
      style,
      sidc: sidc(identity, symbolSet, entity, status),
    },
  };
}

const BASES: OverlayId[] = ["controlPoints"];
const AIR_DEFENSES: OverlayId[] = [
  "airDefenses",
  "lorad",
  "merad",
  "shorad",
  "aaa",
];
// EWRs have their own "ewr" category, so they are drawn by "Other ground
// objects", and by the task-filtered layers.
const EWRS: OverlayId[] = [...AIR_DEFENSES, "otherGroundObjects"];
const OTHER: OverlayId[] = ["otherGroundObjects"];
const ALL_GROUND_OBJECTS: OverlayId[] = [
  ...AIR_DEFENSES,
  "factories",
  "ships",
  "otherGroundObjects",
];
const ALL_FLIGHT_PLANS: OverlayId[] = [
  "selectedFlightPlan",
  "blueFlightPlans",
  "redFlightPlans",
];

const cp = (
  label: string,
  identity: StandardIdentity,
  symbolSet: SymbolSet,
  entity: EntityKey,
  status?: Status,
) => symbol(label, BASES, "controlPoint", identity, symbolSet, entity, status);

const tgo = (
  label: string,
  overlays: OverlayId[],
  identity: StandardIdentity,
  symbolSet: SymbolSet,
  entity: EntityKey,
  status?: Status,
) => symbol(label, overlays, "tgo", identity, symbolSet, entity, status);

const flight = (label: string, identity: StandardIdentity, entity: EntityKey) =>
  symbol(label, ["aircraft"], "flight", identity, SymbolSet.AIR, entity);

const { LAND_INSTALLATIONS, LAND_UNIT, LAND_EQUIPMENT, SEA_SURFACE } =
  SymbolSet;

export const LEGEND_SECTIONS: LegendSection[] = [
  {
    title: "Bases",
    entries: [
      cp("Airfield", FRIEND, LAND_INSTALLATIONS, "airportAirBase"),
      cp("FOB / FARP", FRIEND, LAND_INSTALLATIONS, "militaryBase"),
      cp("Carrier", FRIEND, SEA_SURFACE, "carrier"),
      cp("LHA", FRIEND, SEA_SURFACE, "amphibiousAssaultShip"),
      cp("Friendly", FRIEND, LAND_INSTALLATIONS, "airportAirBase"),
      cp("Enemy", HOSTILE_FAKER, LAND_INSTALLATIONS, "airportAirBase"),
      cp("Neutral (unowned)", UNKNOWN, LAND_INSTALLATIONS, "airportAirBase"),
      cp(
        "Damaged",
        FRIEND,
        LAND_INSTALLATIONS,
        "airportAirBase",
        Status.PRESENT_DAMAGED,
      ),
      cp(
        "Destroyed",
        FRIEND,
        LAND_INSTALLATIONS,
        "airportAirBase",
        Status.PRESENT_DESTROYED,
      ),
      {
        label: "Carrier / LHA movement order",
        overlays: BASES,
        swatch: { kind: "line", color: "movementPath", weight: 1 },
      },
    ],
  },
  {
    title: "Ground objectives",
    entries: [
      tgo("SAM / AAA site", AIR_DEFENSES, FRIEND, LAND_UNIT, "airDefense"),
      tgo(
        "Enemy SAM / AAA site",
        AIR_DEFENSES,
        HOSTILE_FAKER,
        LAND_UNIT,
        "airDefense",
      ),
      tgo("Early warning radar", EWRS, FRIEND, LAND_EQUIPMENT, "radar"),
      tgo(
        "Factory / motor pool",
        ["factories", "otherGroundObjects"],
        FRIEND,
        LAND_INSTALLATIONS,
        "maintenanceFacility",
      ),
      tgo("Ship", ["ships"], FRIEND, SEA_SURFACE, "surfaceCombatant"),
      tgo(
        "Ammunition depot",
        OTHER,
        FRIEND,
        LAND_INSTALLATIONS,
        "ammunitionCache",
      ),
      tgo(
        "Fuel depot / warehouse",
        OTHER,
        FRIEND,
        LAND_INSTALLATIONS,
        "warehouse",
      ),
      tgo(
        "Command center",
        OTHER,
        FRIEND,
        LAND_INSTALLATIONS,
        "militaryInfrastructure",
      ),
      tgo(
        "Communications",
        OTHER,
        FRIEND,
        LAND_INSTALLATIONS,
        "telecommunicationsTower",
      ),
      tgo(
        "Power plant",
        OTHER,
        FRIEND,
        LAND_INSTALLATIONS,
        "generationStation",
      ),
      tgo(
        "Oil facility",
        OTHER,
        FRIEND,
        LAND_INSTALLATIONS,
        "petroleumFacility",
      ),
      tgo("Village", OTHER, FRIEND, LAND_INSTALLATIONS, "publicVenues"),
      tgo("Allied camp", OTHER, FRIEND, LAND_INSTALLATIONS, "tentedCamp"),
      tgo(
        "FARP pad",
        OTHER,
        FRIEND,
        LAND_INSTALLATIONS,
        "helicopterLandingSite",
      ),
      tgo("Missile / coastal site", OTHER, FRIEND, LAND_UNIT, "missile"),
      tgo("Armor group", OTHER, FRIEND, LAND_UNIT, "armor"),
      tgo(
        "Intact (air defense)",
        ALL_GROUND_OBJECTS,
        FRIEND,
        LAND_UNIT,
        "airDefense",
        Status.PRESENT_FULLY_CAPABLE,
      ),
      tgo(
        "Damaged, still a threat",
        ALL_GROUND_OBJECTS,
        FRIEND,
        LAND_UNIT,
        "airDefense",
        Status.PRESENT,
      ),
      tgo(
        "Damaged",
        ALL_GROUND_OBJECTS,
        FRIEND,
        LAND_UNIT,
        "airDefense",
        Status.PRESENT_DAMAGED,
      ),
      tgo(
        "Destroyed",
        ALL_GROUND_OBJECTS,
        FRIEND,
        LAND_UNIT,
        "airDefense",
        Status.PRESENT_DESTROYED,
      ),
    ],
  },
  {
    title: "Flights",
    entries: [
      flight("Fighter", FRIEND, "fighter"),
      flight("Attack / strike", FRIEND, "attackStrike"),
      flight("Helicopter", FRIEND, "rotaryWing"),
      flight("Enemy flight", HOSTILE_FAKER, "fighter"),
    ],
  },
  {
    title: "Flight plans",
    entries: [
      {
        label: "Blue flight plan",
        overlays: ["blueFlightPlans", "selectedFlightPlan"],
        swatch: { kind: "line", color: "flightPlanBlue", weight: 3 },
      },
      {
        label: "Red flight plan",
        overlays: ["redFlightPlans", "selectedFlightPlan"],
        swatch: { kind: "line", color: "flightPlanRed", weight: 3 },
      },
      {
        label: "Selected / hovered flight plan",
        overlays: ALL_FLIGHT_PLANS,
        swatch: { kind: "line", color: "flightPlanSelected", weight: 3 },
      },
      {
        label: "Commit boundary (selected flight)",
        overlays: ALL_FLIGHT_PLANS,
        swatch: { kind: "line", color: "commitBoundary", weight: 1 },
      },
    ],
  },
  {
    title: "Ongoing combats",
    entries: [
      {
        label: "Combat area",
        overlays: ["activeCombat"],
        swatch: { kind: "area", color: "combat", fillOpacity: 0.2 },
      },
      {
        label: "Engagement",
        overlays: ["activeCombat"],
        swatch: { kind: "line", color: "combat", weight: 3 },
      },
    ],
  },
  {
    title: "Front lines and supply routes",
    entries: [
      {
        label: "Front line",
        overlays: ["frontLines"],
        swatch: {
          kind: "line",
          color: "frontLine",
          // Scaled down to fit the swatch.
          weight: FRONT_LINE_WEIGHT / 2,
        },
      },
      {
        label: "Blue supply route (land)",
        overlays: ["supplyRoutes"],
        swatch: {
          kind: "line",
          color: "supplyRouteBlue",
          weight: SUPPLY_ROUTE_WEIGHT.land,
        },
      },
      {
        label: "Blue supply route (sea)",
        overlays: ["supplyRoutes"],
        swatch: {
          kind: "line",
          color: "supplyRouteBlue",
          weight: SUPPLY_ROUTE_WEIGHT.sea,
        },
      },
      {
        label: "Red supply route",
        overlays: ["supplyRoutes"],
        swatch: {
          kind: "line",
          color: "supplyRouteRed",
          weight: SUPPLY_ROUTE_WEIGHT.land,
        },
      },
      {
        label: "Supply route at an active front",
        overlays: ["supplyRoutes"],
        swatch: {
          kind: "line",
          color: "supplyRouteFrontActive",
          weight: SUPPLY_ROUTE_WEIGHT.land,
        },
      },
      {
        label: "Supply route with transfers in progress",
        overlays: ["supplyRoutes"],
        swatch: {
          kind: "line",
          color: "supplyRouteBlue",
          weight: SUPPLY_ROUTE_WEIGHT.land,
          overlay: {
            color: "supplyRouteActiveTransport",
            weight: SUPPLY_ROUTE_ACTIVE_WEIGHT,
          },
        },
      },
    ],
  },
  {
    title: "Air defense ranges",
    entries: [
      {
        label: "Allied SAM threat range",
        overlays: ["alliedSamThreatRange"],
        swatch: { kind: "ring", color: "threatBlue", weight: 2 },
      },
      {
        label: "Enemy SAM threat range",
        overlays: ["enemySamThreatRange"],
        swatch: { kind: "ring", color: "threatRed", weight: 2 },
      },
      {
        label: "Allied SAM detection range",
        overlays: ["alliedSamDetectionRange"],
        swatch: { kind: "ring", color: "detectionBlue", weight: 1 },
      },
      {
        label: "Enemy SAM detection range",
        overlays: ["enemySamDetectionRange"],
        swatch: { kind: "ring", color: "detectionRed", weight: 1 },
      },
      {
        label: "Hovered range and its emitter",
        overlays: ["emitterHighlight"],
        swatch: { kind: "ring", color: "emitterHighlight", weight: 3 },
      },
    ],
  },
  {
    title: "IADS network",
    entries: [
      {
        label: "Power link",
        overlays: ["alliedIadsNetwork", "enemyIadsNetwork"],
        swatch: { kind: "line", color: "iadsPower", weight: 2 },
      },
      {
        label: "Communication link",
        overlays: ["alliedIadsNetwork", "enemyIadsNetwork"],
        swatch: { kind: "line", color: "iadsCommunication", weight: 2 },
      },
      {
        label: "Inactive link",
        overlays: ["alliedIadsNetwork", "enemyIadsNetwork"],
        swatch: {
          kind: "line",
          color: "iadsCommunication",
          weight: 2,
          opacity: IADS_INACTIVE_STYLE.opacity,
          // The map dash is sized for long links; shorten it for the swatch.
          dashArray: "6",
        },
      },
    ],
  },
  {
    title: "Threat zones",
    entries: [
      {
        label: "Blue threat zone",
        overlays: [
          "blueThreatZonesFull",
          "blueThreatZonesAircraft",
          "blueThreatZonesAirDefenses",
          "blueThreatZonesRadarSams",
        ],
        swatch: { kind: "area", color: "threatBlue", fillOpacity: 0.4 },
      },
      {
        label: "Red threat zone",
        overlays: [
          "redThreatZonesFull",
          "redThreatZonesAircraft",
          "redThreatZonesAirDefenses",
          "redThreatZonesRadarSams",
        ],
        swatch: { kind: "area", color: "threatRed", fillOpacity: 0.4 },
      },
    ],
  },
];

export function visibleSections(active: Set<OverlayId>): LegendSection[] {
  return LEGEND_SECTIONS.map((section) => ({
    ...section,
    entries: section.entries.filter((entry) =>
      entry.overlays.some((overlay) => active.has(overlay)),
    ),
  })).filter((section) => section.entries.length > 0);
}

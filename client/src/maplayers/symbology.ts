// Single source of truth for how map objects are drawn as APP-6(D) symbols.
//
// The SIDCs of real objects come from the backend (game/sidc.py). This module
// holds the milsymbol rendering options shared by the layers and the legend,
// plus the SIDC building blocks (mirroring game/sidc.py) used by the legend to
// draw representative symbols.
import { Icon, Point } from "leaflet";
import ms, { SymbolOptions } from "milsymbol";

export const SYMBOL_STYLES = {
  controlPoint: { size: 24, colorMode: "Dark" },
  tgo: { size: 24 },
  flight: { size: 20 },
};

export type SymbolStyleKey = keyof typeof SYMBOL_STYLES;

// Symbols scale with the map zoom (GFX-04.5): smaller at theatre view so a
// dense front stays legible, larger at airfield view. SYMBOL_STYLES sizes are
// the sizes at the default zoom.
export const DEFAULT_MAP_ZOOM = 8;
const SYMBOL_SCALE_PER_ZOOM_LEVEL = 0.15;
export const MIN_SYMBOL_SCALE = 0.6;
export const MAX_SYMBOL_SCALE = 1.6;

export function symbolScaleForZoom(zoom: number): number {
  const scale = 1 + (zoom - DEFAULT_MAP_ZOOM) * SYMBOL_SCALE_PER_ZOOM_LEVEL;
  return Math.min(MAX_SYMBOL_SCALE, Math.max(MIN_SYMBOL_SCALE, scale));
}

export function symbolSizeForZoom(style: SymbolStyleKey, zoom: number): number {
  return Math.round(SYMBOL_STYLES[style].size * symbolScaleForZoom(zoom));
}

function buildSymbol(sidc: string, style: SymbolStyleKey, size?: number) {
  const options = { ...SYMBOL_STYLES[style] } as SymbolOptions;
  if (size !== undefined) {
    options.size = size;
  }
  return new ms.Symbol(sidc, options);
}

export function symbolDataUrl(sidc: string, style: SymbolStyleKey): string {
  return buildSymbol(sidc, style).toDataURL();
}

// Icons are cached: a marker re-rendered at the same zoom keeps the same Icon
// reference, so react-leaflet does not swap it (which would abort a drag).
const iconCache = new Map<string, Icon>();

export function symbolIcon(
  sidc: string,
  style: SymbolStyleKey,
  zoom: number = DEFAULT_MAP_ZOOM,
): Icon {
  const size = symbolSizeForZoom(style, zoom);
  const key = `${style}|${size}|${sidc}`;
  const cached = iconCache.get(key);
  if (cached) {
    return cached;
  }
  const symbol = buildSymbol(sidc, style, size);
  const anchor = symbol.getAnchor();
  const width = symbol.getSize().width;
  const icon = new Icon({
    iconUrl: symbol.toDataURL(),
    iconAnchor: new Point(anchor.x, anchor.y),
    // Tooltips open beside the symbol instead of covering it.
    tooltipAnchor: new Point(Math.max(anchor.x, width - anchor.x), 0),
  });
  iconCache.set(key, icon);
  return icon;
}

// Values below mirror the enums of game/sidc.py (only those used by the game).
export enum StandardIdentity {
  UNKNOWN = 1,
  FRIEND = 3,
  HOSTILE_FAKER = 6,
}

export enum SymbolSet {
  AIR = 1,
  LAND_UNIT = 10,
  LAND_EQUIPMENT = 15,
  LAND_INSTALLATIONS = 20,
  SEA_SURFACE = 30,
}

export enum Status {
  PRESENT = 0,
  PRESENT_FULLY_CAPABLE = 2,
  PRESENT_DAMAGED = 3,
  PRESENT_DESTROYED = 4,
}

export const ENTITIES = {
  // AirEntity
  fighter: 110104,
  attackStrike: 110102,
  rotaryWing: 110200,
  // LandUnitEntity
  armor: 120500,
  airDefense: 130100,
  missile: 130700,
  // LandEquipmentEntity
  radar: 220300,
  // LandInstallationEntity
  ammunitionCache: 110300,
  warehouse: 112000,
  tentedCamp: 111900,
  generationStation: 120502,
  petroleumFacility: 120504,
  militaryBase: 120802,
  militaryInfrastructure: 120800,
  publicVenues: 121000,
  telecommunicationsTower: 121203,
  airportAirBase: 121301,
  helicopterLandingSite: 121305,
  maintenanceFacility: 121306,
  // SeaSurfaceEntity
  carrier: 120100,
  surfaceCombatant: 120200,
  amphibiousAssaultShip: 120303,
};

export type EntityKey = keyof typeof ENTITIES;

const VERSION = "10";
const CONTEXT_REALITY = "0";

// Assembles a 20-digit SIDC exactly as SymbolIdentificationCode.__str__ does.
export function sidc(
  identity: StandardIdentity,
  symbolSet: SymbolSet,
  entity: EntityKey,
  status: Status = Status.PRESENT,
): string {
  return [
    VERSION,
    CONTEXT_REALITY,
    String(identity),
    String(symbolSet).padStart(2, "0"),
    String(status),
    "0", // headquarters / task force / dummy: not applicable
    "00", // amplifier: unknown
    String(ENTITIES[entity]).padStart(6, "0"),
    "00", // sector one modifier
    "00", // sector two modifier
  ].join("");
}

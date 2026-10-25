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

function buildSymbol(sidc: string, style: SymbolStyleKey) {
  return new ms.Symbol(sidc, SYMBOL_STYLES[style] as SymbolOptions);
}

export function symbolDataUrl(sidc: string, style: SymbolStyleKey): string {
  return buildSymbol(sidc, style).toDataURL();
}

export function symbolIcon(sidc: string, style: SymbolStyleKey): Icon {
  const symbol = buildSymbol(sidc, style);
  return new Icon({
    iconUrl: symbol.toDataURL(),
    iconAnchor: new Point(symbol.getAnchor().x, symbol.getAnchor().y),
  });
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

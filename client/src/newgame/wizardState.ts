// What the player chose in the new campaign wizard (WEB-06), until the request. The
// engine proposes the defaults and checks the request: no game rule here.
import type {
  CampaignDefaults,
  NewGameCampaign,
  NewGameFactionChoice,
  NewGameOptions,
  NewGameRequest,
  Setting,
} from "../api/liberationApi";

export type SettingValue = Setting["value"];

export const GENERATOR_FLAGS = [
  ["no_carrier", "No aircraft carriers"],
  ["no_lha", "No LHA"],
  ["no_player_navy", "No player navy"],
  ["no_enemy_navy", "No enemy navy"],
] as const;

export type GeneratorFlag = (typeof GENERATOR_FLAGS)[number][0];

export interface FactionDraft {
  name: string;
  removed: Record<string, string[]>;
  added: Record<string, string[]>;
  hasJtac?: boolean;
  doctrine?: string;
}

export interface WizardState {
  campaignId: string;
  blue: FactionDraft;
  red: FactionDraft;
  /** The name of a time period, or null to use `customDate`. */
  timePeriod: string | null;
  customDate: string;
  inverted: boolean;
  advancedIads: boolean;
  flags: Record<GeneratorFlag, boolean>;
  squadronsStartFull: boolean;
  playerBudget: number;
  enemyBudget: number;
  mods: string[];
  /** Only what differs from the campaign's defaults. */
  settings: Record<string, SettingValue>;
  seed: string;
}

export function factionDraft(name: string): FactionDraft {
  return { name, removed: {}, added: {} };
}

export function stateFromDefaults(
  campaignId: string,
  defaults: CampaignDefaults,
  options: NewGameOptions,
): WizardState {
  return {
    campaignId,
    blue: factionDraft(defaults.blue_faction),
    red: factionDraft(defaults.red_faction),
    timePeriod:
      defaults.start_date != null
        ? null
        : (defaults.time_period ?? options.default_time_period),
    customDate: defaults.start_date ?? "",
    inverted: false,
    advancedIads: defaults.advanced_iads_available,
    flags: {
      no_carrier: defaults.no_carrier,
      no_lha: defaults.no_lha,
      no_player_navy: defaults.no_player_navy,
      no_enemy_navy: defaults.no_enemy_navy,
    },
    squadronsStartFull: defaults.squadrons_start_full,
    playerBudget: defaults.player_budget,
    enemyBudget: defaults.enemy_budget,
    mods: defaults.mods,
    settings: {},
    seed: "",
  };
}

export function startDate(
  state: WizardState,
  options: NewGameOptions,
): string | undefined {
  if (state.timePeriod === null) {
    return state.customDate || undefined;
  }
  return options.time_periods.find((p) => p.name === state.timePeriod)
    ?.start_date;
}

function factionChoice(draft: FactionDraft): NewGameFactionChoice {
  return {
    name: draft.name,
    removed: draft.removed,
    added: draft.added,
    has_jtac: draft.hasJtac,
    doctrine: draft.doctrine,
  };
}

export { factionChoice };

export function toRequest(
  state: WizardState,
  options: NewGameOptions,
): NewGameRequest | undefined {
  const start_date = startDate(state, options);
  if (start_date === undefined) {
    return undefined;
  }
  return {
    campaign_id: state.campaignId,
    blue: factionChoice(state.blue),
    red: factionChoice(state.red),
    start_date,
    player_budget: state.playerBudget,
    enemy_budget: state.enemyBudget,
    inverted: state.inverted,
    advanced_iads: state.advancedIads,
    ...state.flags,
    squadrons_start_full: state.squadronsStartFull,
    mods: state.mods,
    settings: state.settings,
    seed: state.seed.trim() === "" ? undefined : Number(state.seed),
  };
}

export interface CampaignFilter {
  query: string;
  theater: string | null;
  era: string | null;
  showIncompatible: boolean;
}

export function filterCampaigns(
  campaigns: NewGameCampaign[],
  filter: CampaignFilter,
): NewGameCampaign[] {
  const query = filter.query.trim().toLowerCase();
  return campaigns.filter(
    (campaign) =>
      (filter.showIncompatible || campaign.compatible) &&
      (filter.theater === null || campaign.theater === filter.theater) &&
      (filter.era === null || campaign.era === filter.era) &&
      (query === "" ||
        campaign.name.toLowerCase().includes(query) ||
        campaign.theater.toLowerCase().includes(query)),
  );
}

/** Takes a unit out of the faction, or brings it back. */
export function toggleUnit(
  draft: FactionDraft,
  group: string,
  unit: string,
): FactionDraft {
  const added = draft.added[group] ?? [];
  if (added.includes(unit)) {
    return {
      ...draft,
      added: { ...draft.added, [group]: added.filter((u) => u !== unit) },
    };
  }
  const removed = draft.removed[group] ?? [];
  return {
    ...draft,
    removed: {
      ...draft.removed,
      [group]: removed.includes(unit)
        ? removed.filter((u) => u !== unit)
        : [...removed, unit],
    },
  };
}

export function addUnit(
  draft: FactionDraft,
  group: string,
  unit: string,
): FactionDraft {
  return {
    ...draft,
    added: {
      ...draft.added,
      [group]: [...(draft.added[group] ?? []), unit],
    },
  };
}

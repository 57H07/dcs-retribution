// Search across every settings page (WEB-07.1). Pure functions over the schema
// sent by GET /settings/, so they know nothing about any particular setting.
import type { Setting, SettingsPage } from "../api/liberationApi";

export interface SettingMatch {
  page: SettingsPage;
  section: string;
  setting: Setting;
}

function terms(query: string): string[] {
  return query.toLowerCase().split(/\s+/).filter(Boolean);
}

/**
 * Settings whose label, help, section or page contain every word of `query`
 * (case-insensitive), in page order. An empty query matches nothing.
 */
export function searchSettings(
  pages: SettingsPage[],
  query: string,
): SettingMatch[] {
  const words = terms(query);
  if (words.length === 0) {
    return [];
  }
  const matches: SettingMatch[] = [];
  for (const page of pages) {
    for (const section of page.sections) {
      for (const setting of section.settings) {
        const text = [
          setting.label,
          setting.detail,
          setting.tooltip,
          section.name,
          page.name,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (words.every((word) => text.includes(word))) {
          matches.push({ page, section: section.name, setting });
        }
      }
    }
  }
  return matches;
}

export interface SettingGroup {
  /** `Page › Section`. */
  title: string;
  settings: Setting[];
}

/** The matches grouped by page and section, as they stand on the pages. */
export function groupMatches(matches: SettingMatch[]): SettingGroup[] {
  const groups: SettingGroup[] = [];
  for (const match of matches) {
    const title = `${match.page.name} › ${match.section}`;
    const last = groups[groups.length - 1];
    if (last?.title === title) {
      last.settings.push(match.setting);
    } else {
      groups.push({ title, settings: [match.setting] });
    }
  }
  return groups;
}

/** Values not yet sent to the engine, by setting key (the new game wizard). */
export type SettingValues = Record<string, Setting["value"]>;

/**
 * Whether the setting differs from its default: as the engine says, or, when
 * `values` holds a value of its own, that value against the default.
 */
export function isModified(setting: Setting, values?: SettingValues): boolean {
  const value = values?.[setting.key];
  return value === undefined ? setting.modified : value !== setting.default;
}

/** Number of settings of a page that differ from their default. */
export function modifiedCount(
  page: SettingsPage,
  values?: SettingValues,
): number {
  return page.sections.reduce(
    (count, section) =>
      count +
      section.settings.filter((setting) => isModified(setting, values)).length,
    0,
  );
}

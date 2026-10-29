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

/** Number of settings of a page that differ from their default. */
export function modifiedCount(page: SettingsPage): number {
  return page.sections.reduce(
    (count, section) =>
      count + section.settings.filter((setting) => setting.modified).length,
    0,
  );
}

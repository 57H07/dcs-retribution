// The basemap chosen by this viewer, remembered in the browser (WEB-01.3).
// Storage may be unavailable (private window, blocked site data): the map
// then simply starts on the default basemap.

const STORAGE_KEY = "retribution.map.basemap";

export function readBasemapPreference(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function writeBasemapPreference(name: string) {
  try {
    window.localStorage.setItem(STORAGE_KEY, name);
  } catch {
    // Not remembered: the default basemap comes back next time.
  }
}

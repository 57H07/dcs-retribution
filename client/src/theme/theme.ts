// Theme variant of the map (GFX-01). The design tokens (tokens.css, generated
// from resources/design/tokens.json) are CSS variables declared per variant on
// :root[data-theme="..."]; the default variant applies when data-theme is unset.
//
// The Qt app passes its variant in the page URL (?theme=dark). To switch theme
// without reloading, set document.documentElement.dataset.theme (for instance
// through QWebEnginePage.runJavaScript), or call applyTheme().

export const THEME_VARIANTS = ["dark", "light"] as const;
export type ThemeVariant = (typeof THEME_VARIANTS)[number];

export function themeFromQuery(search: string): ThemeVariant | undefined {
  const theme = new URLSearchParams(search).get("theme");
  return THEME_VARIANTS.find((variant) => variant === theme);
}

export function applyTheme(
  variant: ThemeVariant | undefined,
  root: HTMLElement = document.documentElement
): void {
  if (variant) {
    root.dataset.theme = variant;
  } else {
    delete root.dataset.theme;
  }
}

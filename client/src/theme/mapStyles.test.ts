// Map styles use the design tokens (GFX-04.4, UI-01.2): the map stylesheets
// hold no colour of their own, only token variables, and the token pairs they
// use keep a sufficient contrast (WCAG AA) in every theme variant.
import { readFileSync } from "fs";
import path from "path";

const SRC = path.resolve(__dirname, "..");
const TOKENS_JSON = path.resolve(SRC, "../../resources/design/tokens.json");

// Stylesheets of the map chrome: controls, tooltips, legend, offline banner.
const MAP_STYLESHEETS = [
  "theme/map.css",
  "components/legend/Legend.css",
  "components/basemaps/Basemaps.css",
  "components/ruler/Ruler.css",
];

function read(relative: string): string {
  return readFileSync(path.join(SRC, relative), "utf-8");
}

function withoutComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, "");
}

function declaredVariables(css: string): Set<string> {
  return new Set(
    Array.from(
      withoutComments(css).matchAll(/(--[a-z0-9-]+)\s*:/g),
      (m) => m[1],
    ),
  );
}

function usedVariables(css: string): string[] {
  return Array.from(
    withoutComments(css).matchAll(/var\(\s*(--[a-z0-9-]+)/g),
    (m) => m[1],
  );
}

describe("map stylesheets", () => {
  const tokenVariables = declaredVariables(read("theme/tokens.css"));

  it.each(MAP_STYLESHEETS)("%s hardcodes no colour", (file) => {
    const css = withoutComments(read(file));
    expect(css.match(/#[0-9a-f]{3,8}\b/gi) ?? []).toEqual([]);
    expect(css.match(/\b(rgba?|hsla?)\(/gi) ?? []).toEqual([]);
    expect(css.match(/\b(white|black|red|yellow|grey|gray)\b/gi) ?? []).toEqual(
      [],
    );
  });

  it.each(MAP_STYLESHEETS)("%s only uses known tokens", (file) => {
    const css = read(file);
    const local = declaredVariables(css);
    const unknown = usedVariables(css).filter(
      (name) => !tokenVariables.has(name) && !local.has(name),
    );
    expect(unknown).toEqual([]);
  });

  it("is loaded by the app", () => {
    expect(read("index.tsx")).toContain('import "./theme/map.css";');
  });
});

// --- Contrast -------------------------------------------------------------

type Rgba = [number, number, number, number];

function parseColor(value: string): Rgba {
  const hex = /^#([0-9a-f]{6})$/i.exec(value);
  if (hex) {
    const n = parseInt(hex[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 1];
  }
  const rgba = /^rgba?\(([^)]*)\)$/.exec(value);
  if (rgba) {
    const [r, g, b, a = 1] = rgba[1].split(",").map(Number);
    return [r, g, b, a];
  }
  throw new Error(`Unsupported colour ${value}`);
}

// Alpha-composites a colour over an opaque backdrop.
function over(color: Rgba, backdrop: Rgba): Rgba {
  const a = color[3];
  return [0, 1, 2].map(
    (i) => color[i] * a + backdrop[i] * (1 - a),
  ) as unknown as Rgba;
}

function luminance([r, g, b]: Rgba): number {
  const channel = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function contrast(a: Rgba, b: Rgba): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

type Tree = { [key: string]: string | Tree };

function variantColors(variant: string): (name: string) => Rgba {
  const tokens = JSON.parse(readFileSync(TOKENS_JSON, "utf-8"));
  const lookup = (tree: Tree, keys: string[]): string | undefined => {
    let node: string | Tree | undefined = tree;
    for (const key of keys) {
      node = typeof node === "object" ? node[key] : undefined;
    }
    return typeof node === "string" ? node : undefined;
  };
  return (name) => {
    const keys = name.split(".");
    const value =
      lookup(tokens.variants[variant], keys) ?? lookup(tokens.base, keys);
    if (value === undefined) {
      throw new Error(`Unknown token ${name}`);
    }
    return parseColor(value);
  };
}

// Text / background pairs drawn by the map stylesheets.
const TEXT_PAIRS: [string, string][] = [
  ["color.text.primary", "color.bg.surface"],
  ["color.text.secondary", "color.bg.surface"],
  ["color.text.accent", "color.bg.surface"],
  ["color.text.primary", "color.button.hover"],
  ["color.overlay.text", "color.overlay.background"],
];

const BLACK: Rgba = [0, 0, 0, 1];
const WHITE: Rgba = [255, 255, 255, 1];

describe.each(["dark", "light"])("%s theme contrast", (variant) => {
  const color = variantColors(variant);

  it.each(TEXT_PAIRS)("%s on %s meets WCAG AA", (text, background) => {
    // A translucent background is checked over both extremes of the map.
    [BLACK, WHITE].forEach((backdrop) => {
      const bg = over(color(background), backdrop);
      expect(contrast(over(color(text), bg), bg)).toBeGreaterThanOrEqual(4.5);
    });
  });
});

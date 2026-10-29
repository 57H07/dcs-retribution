// Single source of the web design tokens (WEB-00.2, mockups direction A).
//
// The values live here only. installTokens() writes them as CSS custom
// properties (--ui-*) for the CSS modules, and `vars` gives the same
// properties as var(--ui-...) strings for TS code (inline styles, milsymbol).
// Dark theme only (W5): a light theme would be a second value set here.
//
// The --ui- prefix keeps these apart from the Qt-shared tokens of
// theme/tokens.css (generated from resources/design/tokens.json), which the
// map still uses until the shell moves it onto this system (WEB-00.3).

export const color = {
  // Grounds, darkest first.
  bgCanvas: "#0B0F12",
  bgPanel: "#12181D",
  bgCard: "#161D23",
  bgRaised: "#1A2229",
  bgControl: "#1B232A",
  bgHover: "#1F2830",
  bgSelected: "#16304A",
  // Lines.
  line: "#263039",
  lineStrong: "#33404B",
  // Text (each passes 4.5:1 on every ground, see tokens.test.ts).
  textPrimary: "#E6EAED",
  textStrong: "#C9D2D9",
  textSecondary: "#9AA6B0",
  // Disabled controls only: exempt from the contrast rule (WCAG 1.4.3).
  textDisabled: "#5D6A75",
  // Accent.
  accent: "#E8A33D",
  accentHover: "#F2BE6B",
  accentSoft: "#3A2A12",
  onAccent: "#14100A",
  // Coalitions and states.
  friendly: "#7FB8EE",
  friendlyHover: "#A9D0F5",
  friendlySoft: "#12293D",
  hostile: "#F08A5D",
  hostileSoft: "#2E1A14",
  success: "#6FCB8F",
  successSoft: "#1C2A1F",
  danger: "#F3A07C",
  dangerLine: "#5A2A20",
  // Overlays.
  scrim: "rgba(5, 8, 10, 0.72)",
  shadow: "rgba(0, 0, 0, 0.55)",
} as const;

// Mission task families: text colour on a tinted ground, from the mockups.
export const task = {
  air: { fg: "#8CC3F2", bg: "#12293D" },
  suppression: { fg: "#F2BE6B", bg: "#3A2A12" },
  groundAttack: { fg: "#F3A07C", bg: "#2E1A14" },
  strike: { fg: "#C7B3E6", bg: "#2A2333" },
  rescue: { fg: "#8FD6A6", bg: "#1C2A1F" },
  support: { fg: "#7FD1C7", bg: "#13282A" },
  logistics: { fg: "#C9D2D9", bg: "#1F2830" },
} as const;

export type TaskFamily = keyof typeof task;

// One colour per mission task: every FlightType value (game/ato/flighttype.py,
// as the API sends it) maps to the family whose colour its tag uses.
export const TASK_FAMILY_BY_FLIGHT_TYPE: Record<string, TaskFamily> = {
  BARCAP: "air",
  TARCAP: "air",
  Intercept: "air",
  "Fighter sweep": "air",
  Escort: "air",
  "AEW&C": "air",
  SEAD: "suppression",
  DEAD: "suppression",
  "SEAD Escort": "suppression",
  "SEAD Sweep": "suppression",
  CAS: "groundAttack",
  BAI: "groundAttack",
  "Armed Recon": "groundAttack",
  Strike: "strike",
  "Anti-ship": "strike",
  "OCA/Runway": "strike",
  "OCA/Aircraft": "strike",
  CSAR: "rescue",
  Refueling: "support",
  Recovery: "support",
  Transport: "logistics",
  "Air Assault": "logistics",
  Ferry: "logistics",
  "Cargo Transport": "logistics",
};

export function taskFamily(flightType: string): TaskFamily {
  return TASK_FAMILY_BY_FLIGHT_TYPE[flightType] ?? "logistics";
}

export const font = {
  display: '"Barlow Condensed", "Arial Narrow", sans-serif',
  body: '"Inter Variable", Inter, "Segoe UI", Arial, sans-serif',
  mono: '"JetBrains Mono Variable", "JetBrains Mono", Consolas, monospace',
} as const;

export const fontSize = {
  xs: "11px",
  sm: "12px",
  md: "13px",
  lg: "15px",
  xl: "18px",
  xxl: "22px",
  display: "30px",
} as const;

export const fontWeight = {
  regular: "400",
  medium: "500",
  semibold: "600",
  bold: "700",
} as const;

export const letterSpacing = {
  display: "0.08em",
  wide: "0.18em",
} as const;

export const space = {
  xxs: "2px",
  xs: "4px",
  sm: "6px",
  md: "8px",
  lg: "12px",
  xl: "16px",
  xxl: "24px",
} as const;

export const radius = {
  sm: "3px",
  md: "4px",
  lg: "6px",
  pill: "999px",
} as const;

export const size = {
  control: "36px",
  controlLg: "44px",
  rail: "44px",
  panel: "320px",
} as const;

export const shadow = {
  overlay: `0 12px 32px ${color.shadow}`,
  focus: `0 0 0 2px ${color.bgCanvas}, 0 0 0 4px ${color.accent}`,
} as const;

export const zIndex = {
  panel: "10",
  overlay: "100",
  toast: "200",
  tooltip: "300",
} as const;

export const tokens = {
  color,
  task,
  font,
  fontSize,
  fontWeight,
  letterSpacing,
  space,
  radius,
  size,
  shadow,
  zIndex,
} as const;

type Tree = { readonly [key: string]: string | Tree };
type VarTree<T> = {
  readonly [K in keyof T]: T[K] extends string ? string : VarTree<T[K]>;
};

const PREFIX = "--ui";

function kebab(name: string): string {
  return name.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
}

function flatten(tree: Tree, path: string, out: [string, string][]): void {
  for (const [key, value] of Object.entries(tree)) {
    const name = `${path}-${kebab(key)}`;
    if (typeof value === "string") {
      out.push([name, value]);
    } else {
      flatten(value, name, out);
    }
  }
}

function toVars<T extends Tree>(tree: T, path: string): VarTree<T> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(tree)) {
    const name = `${path}-${kebab(key)}`;
    result[key] =
      typeof value === "string" ? `var(${name})` : toVars(value, name);
  }
  return result as VarTree<T>;
}

/** Every token as [custom property name, value], e.g. ["--ui-color-accent", "#E8A33D"]. */
export function tokenEntries(): [string, string][] {
  const out: [string, string][] = [];
  flatten(tokens, PREFIX, out);
  return out;
}

/** The tokens as var(--ui-...) references, shaped like `tokens`. */
export const vars = toVars(tokens, PREFIX);

export function tokensCss(): string {
  const lines = tokenEntries().map(([name, value]) => `  ${name}: ${value};`);
  return `:root {\n  color-scheme: dark;\n${lines.join("\n")}\n}\n`;
}

const STYLE_ID = "ui-tokens";

/** Writes the tokens as CSS custom properties on :root (idempotent). */
export function installTokens(doc: Document = document): void {
  let style = doc.getElementById(STYLE_ID);
  if (!style) {
    style = doc.createElement("style");
    style.id = STYLE_ID;
    doc.head.prepend(style);
  }
  style.textContent = tokensCss();
}

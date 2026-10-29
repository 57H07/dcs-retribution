import {
  TASK_FAMILY_BY_FLIGHT_TYPE,
  color,
  installTokens,
  task,
  taskFamily,
  tokenEntries,
  tokensCss,
  vars,
} from "./tokens";

// WCAG 2.x relative luminance and contrast ratio.
function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const GROUNDS = [
  color.bgCanvas,
  color.bgPanel,
  color.bgCard,
  color.bgRaised,
  color.bgControl,
  color.bgHover,
  color.bgSelected,
];

// Every colour used for text (disabled text is exempt, WCAG 1.4.3).
const TEXT = {
  textPrimary: color.textPrimary,
  textStrong: color.textStrong,
  textSecondary: color.textSecondary,
  accent: color.accent,
  friendly: color.friendly,
  hostile: color.hostile,
  success: color.success,
  danger: color.danger,
};

describe("design tokens", () => {
  it("holds the colours set by the spec", () => {
    expect(color).toMatchObject({
      bgCanvas: "#0B0F12",
      bgPanel: "#12181D",
      bgRaised: "#1A2229",
      line: "#263039",
      textPrimary: "#E6EAED",
      textSecondary: "#9AA6B0",
      accent: "#E8A33D",
      friendly: "#7FB8EE",
      hostile: "#F08A5D",
      success: "#6FCB8F",
    });
  });

  it.each(Object.entries(TEXT))(
    "%s reaches 4.5:1 on every ground",
    (_name, value) => {
      for (const ground of GROUNDS) {
        expect(contrast(value, ground)).toBeGreaterThanOrEqual(4.5);
      }
    },
  );

  it("keeps text on the accent readable", () => {
    expect(contrast(color.onAccent, color.accent)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(color.onAccent, color.accentHover)).toBeGreaterThanOrEqual(
      4.5,
    );
  });

  it.each(Object.entries(task))(
    "task colour %s reaches 4.5:1 on its ground",
    (_name, { fg, bg }) => {
      expect(contrast(fg, bg)).toBeGreaterThanOrEqual(4.5);
    },
  );

  it("maps every FlightType of the engine to a task colour", () => {
    // game/ato/flighttype.py values, as the API sends them.
    const flightTypes = [
      "TARCAP",
      "BARCAP",
      "CAS",
      "Intercept",
      "Strike",
      "Anti-ship",
      "SEAD",
      "DEAD",
      "Escort",
      "BAI",
      "Fighter sweep",
      "OCA/Runway",
      "OCA/Aircraft",
      "AEW&C",
      "Transport",
      "SEAD Escort",
      "Refueling",
      "Ferry",
      "Air Assault",
      "SEAD Sweep",
      "Cargo Transport",
      "Armed Recon",
      "Recovery",
      "CSAR",
    ];
    expect(Object.keys(TASK_FAMILY_BY_FLIGHT_TYPE).sort()).toEqual(
      [...flightTypes].sort(),
    );
    expect(taskFamily("BARCAP")).toBe("air");
    expect(taskFamily("DEAD")).toBe("suppression");
    expect(taskFamily("Not a task")).toBe("logistics");
  });

  it("exposes each token as a custom property and a var() reference", () => {
    const entries = Object.fromEntries(tokenEntries());
    expect(entries["--ui-color-accent"]).toBe("#E8A33D");
    expect(entries["--ui-task-air-fg"]).toBe(task.air.fg);
    expect(entries["--ui-font-size-md"]).toBe("13px");
    expect(vars.color.bgCanvas).toBe("var(--ui-color-bg-canvas)");
    expect(vars.task.groundAttack.bg).toBe("var(--ui-task-ground-attack-bg)");
    for (const [name] of tokenEntries()) {
      expect(name).toMatch(/^--ui(-[a-z0-9]+)+$/);
    }
  });

  it("installs the tokens once on the document", () => {
    installTokens();
    installTokens();
    const styles = document.querySelectorAll("style#ui-tokens");
    expect(styles).toHaveLength(1);
    expect(styles[0].textContent).toBe(tokensCss());
    expect(tokensCss()).toContain("--ui-color-bg-canvas: #0B0F12;");
  });
});

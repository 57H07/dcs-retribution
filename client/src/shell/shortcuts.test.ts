import { SHORTCUT_HELP, isTypingTarget, shortcutFor } from "./shortcuts";

function key(
  k: string,
  extra: Partial<{
    ctrlKey: boolean;
    metaKey: boolean;
    altKey: boolean;
    target: EventTarget | null;
  }> = {},
) {
  return {
    key: k,
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    target: document.body,
    ...extra,
  };
}

describe("shortcutFor", () => {
  it("maps the W13 shortcuts", () => {
    expect(shortcutFor(key("Escape"))).toEqual({ kind: "close" });
    expect(shortcutFor(key("?"))).toEqual({ kind: "help" });
    expect(shortcutFor(key("n"))).toEqual({ kind: "newPackage" });
    expect(shortcutFor(key("N"))).toEqual({ kind: "newPackage" });
    expect(shortcutFor(key("s", { ctrlKey: true }))).toEqual({ kind: "save" });
    expect(shortcutFor(key("S", { metaKey: true }))).toEqual({ kind: "save" });
  });

  it("maps 1-5 to five distinct map layers", () => {
    const layers = ["1", "2", "3", "4", "5"].map((k) => shortcutFor(key(k)));
    for (const layer of layers) {
      expect(layer?.kind).toBe("layer");
    }
    const overlays = layers.map((l) => (l?.kind === "layer" ? l.overlay : ""));
    expect(new Set(overlays).size).toBe(5);
    expect(shortcutFor(key("6"))).toBeNull();
  });

  it("has no shortcut for passing the turn or taking off", () => {
    for (const k of ["Enter", " ", "p", "t", "e", "Space"]) {
      expect(shortcutFor(key(k))).toBeNull();
    }
    expect(SHORTCUT_HELP.map((s) => s.description).join(" ")).not.toMatch(
      /turn|take off/i,
    );
  });

  it("leaves modified keys alone", () => {
    expect(shortcutFor(key("1", { ctrlKey: true }))).toBeNull();
    expect(shortcutFor(key("n", { altKey: true }))).toBeNull();
    expect(shortcutFor(key("s"))).toBeNull();
  });

  it("is ignored while typing in a field", () => {
    const input = document.createElement("input");
    const textarea = document.createElement("textarea");
    for (const target of [input, textarea]) {
      expect(shortcutFor(key("n", { target }))).toBeNull();
      expect(shortcutFor(key("1", { target }))).toBeNull();
      expect(shortcutFor(key("s", { target, ctrlKey: true }))).toBeNull();
    }
  });
});

describe("isTypingTarget", () => {
  it("knows text fields from other controls", () => {
    const text = document.createElement("input");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    const editable = document.createElement("div");
    editable.contentEditable = "true";
    // jsdom does not implement isContentEditable.
    Object.defineProperty(editable, "isContentEditable", { value: true });
    expect(isTypingTarget(text)).toBe(true);
    expect(isTypingTarget(editable)).toBe(true);
    expect(isTypingTarget(document.createElement("select"))).toBe(true);
    expect(isTypingTarget(checkbox)).toBe(false);
    expect(isTypingTarget(document.createElement("button"))).toBe(false);
    expect(isTypingTarget(null)).toBe(false);
  });
});

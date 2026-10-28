import { applyTheme, themeFromQuery } from "./theme";

describe("themeFromQuery", () => {
  it("reads a known variant", () => {
    expect(themeFromQuery("?server=[::1]:16880&theme=light")).toBe("light");
    expect(themeFromQuery("?theme=dark")).toBe("dark");
  });

  it("ignores a missing or unknown variant", () => {
    expect(themeFromQuery("?server=localhost:16880")).toBeUndefined();
    expect(themeFromQuery("?theme=solarized")).toBeUndefined();
  });
});

describe("applyTheme", () => {
  it("sets and clears data-theme", () => {
    const root = document.createElement("div");
    applyTheme("light", root);
    expect(root.dataset.theme).toBe("light");
    applyTheme(undefined, root);
    expect(root.dataset.theme).toBeUndefined();
  });
});

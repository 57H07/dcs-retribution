import { SymbolSet, StandardIdentity, sidc } from "../maplayers/symbology";
import { MilSymbol, sidcFor } from "./MilSymbol";
import { render, screen } from "@testing-library/react";

function svgOf(img: HTMLElement): string {
  const src = img.getAttribute("src") ?? "";
  const [, payload] = src.split(",");
  return src.includes(";base64,") ? atob(payload) : decodeURIComponent(payload);
}

describe("MilSymbol", () => {
  it("renders an image named by its label", () => {
    render(
      <MilSymbol
        label="Friendly fighter"
        affiliation="friend"
        symbolSet={SymbolSet.AIR}
        entity="fighter"
      />,
    );
    const img = screen.getByRole("img", { name: "Friendly fighter" });
    expect(img.getAttribute("src")).toMatch(/^data:image\/svg\+xml/);
  });

  it("builds the SIDC of the engine from the affiliation", () => {
    expect(
      sidcFor({
        label: "x",
        affiliation: "hostile",
        symbolSet: SymbolSet.LAND_UNIT,
        entity: "armor",
      }),
    ).toBe(sidc(StandardIdentity.HOSTILE_FAKER, SymbolSet.LAND_UNIT, "armor"));
    expect(sidcFor({ label: "x", sidc: "10031000001211000000" })).toBe(
      "10031000001211000000",
    );
  });

  it("draws friend and hostile with different frames and token colours", () => {
    render(
      <>
        <MilSymbol
          label="Friend"
          affiliation="friend"
          symbolSet={SymbolSet.LAND_UNIT}
          entity="armor"
        />
        <MilSymbol
          label="Hostile"
          affiliation="hostile"
          symbolSet={SymbolSet.LAND_UNIT}
          entity="armor"
        />
      </>,
    );
    const friend = svgOf(screen.getByRole("img", { name: "Friend" }));
    const hostile = svgOf(screen.getByRole("img", { name: "Hostile" }));
    expect(friend).toContain("#7FB8EE");
    expect(hostile).toContain("#F08A5D");
    // Shape, not only colour: strip colours and the frames still differ.
    const shape = (svg: string) => svg.replace(/#[0-9A-Fa-f]{6}/g, "");
    expect(shape(friend)).not.toBe(shape(hostile));
  });
});

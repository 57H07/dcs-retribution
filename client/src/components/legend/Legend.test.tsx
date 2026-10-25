import { LAYER_COLORS, LayerColorKey } from "../../maplayers/colors";
import {
  OVERLAY_IDS,
  OverlayId,
  defaultActiveOverlays,
} from "../../maplayers/overlays";
import {
  sidc,
  StandardIdentity,
  Status,
  SymbolSet,
} from "../../maplayers/symbology";
import { LEGEND_OPEN_STORAGE_KEY, LegendControl, LegendPanel } from "./Legend";
import { LEGEND_SECTIONS, visibleSections } from "./legendEntries";
import { fireEvent, render, screen } from "@testing-library/react";

jest.mock("react-leaflet", () => ({
  useMapEvents: jest.fn(),
}));

const allEntries = LEGEND_SECTIONS.flatMap((section) => section.entries);

function referencedColors(): Set<LayerColorKey> {
  const colors = new Set<LayerColorKey>();
  allEntries.forEach(({ swatch }) => {
    if (swatch.kind === "symbol") {
      return;
    }
    colors.add(swatch.color);
    if (swatch.kind === "line" && swatch.overlay) {
      colors.add(swatch.overlay.color);
    }
  });
  return colors;
}

describe("legend content", () => {
  it("references every layer colour constant", () => {
    const referenced = referencedColors();
    const missing = (Object.keys(LAYER_COLORS) as LayerColorKey[]).filter(
      (key) => !referenced.has(key),
    );
    expect(missing).toEqual([]);
  });

  it("has entries for every overlay of the layer controls", () => {
    const covered = new Set(allEntries.flatMap((entry) => entry.overlays));
    expect(OVERLAY_IDS.filter((id) => !covered.has(id))).toEqual([]);
  });

  it("only keeps entries of active overlays", () => {
    const sections = visibleSections(new Set<OverlayId>(["frontLines"]));
    expect(sections).toHaveLength(1);
    expect(sections[0].entries.map((entry) => entry.label)).toEqual([
      "Front line",
    ]);
    expect(visibleSections(new Set())).toEqual([]);
  });
});

describe("sidc", () => {
  it("assembles codes the same way as game/sidc.py", () => {
    // Hostile damaged airfield, as serialised by the backend.
    expect(
      sidc(
        StandardIdentity.HOSTILE_FAKER,
        SymbolSet.LAND_INSTALLATIONS,
        "airportAirBase",
        Status.PRESENT_DAMAGED,
      ),
    ).toEqual("10062030001213010000");
  });
});

describe("LegendPanel", () => {
  it("shows the entries of active layers only", () => {
    render(<LegendPanel active={new Set<OverlayId>(["supplyRoutes"])} />);
    expect(screen.getByText("Front lines and supply routes")).toBeTruthy();
    expect(screen.getByText("Red supply route")).toBeTruthy();
    expect(screen.queryByText("Front line")).toBeNull();
    expect(screen.queryByText("Bases")).toBeNull();
  });

  it("draws symbols for bases", () => {
    const { container } = render(
      <LegendPanel active={new Set<OverlayId>(["controlPoints"])} />,
    );
    expect(
      container.querySelectorAll("img.legend-symbol").length,
    ).toBeGreaterThan(0);
  });

  it("says when no layer is active", () => {
    render(<LegendPanel active={new Set()} />);
    expect(screen.getByText("No active layer.")).toBeTruthy();
  });
});

describe("LegendControl", () => {
  beforeEach(() => window.localStorage.clear());

  it("is closed by default and remembers when it is opened", () => {
    const { unmount } = render(
      <LegendControl active={defaultActiveOverlays()} />,
    );
    const button = screen.getByRole("button", { name: "Legend" });
    expect(button.getAttribute("aria-expanded")).toEqual("false");
    expect(screen.queryByText("Bases")).toBeNull();

    fireEvent.click(button);
    expect(screen.getByText("Bases")).toBeTruthy();
    expect(window.localStorage.getItem(LEGEND_OPEN_STORAGE_KEY)).toEqual(
      "true",
    );
    unmount();

    render(<LegendControl active={defaultActiveOverlays()} />);
    expect(
      screen
        .getByRole("button", { name: "Legend" })
        .getAttribute("aria-expanded"),
    ).toEqual("true");
  });

  it("remembers when it is closed", () => {
    window.localStorage.setItem(LEGEND_OPEN_STORAGE_KEY, "true");
    render(<LegendControl active={defaultActiveOverlays()} />);
    fireEvent.click(screen.getByRole("button", { name: "Legend" }));
    expect(screen.queryByText("Bases")).toBeNull();
    expect(window.localStorage.getItem(LEGEND_OPEN_STORAGE_KEY)).toEqual(
      "false",
    );
  });
});

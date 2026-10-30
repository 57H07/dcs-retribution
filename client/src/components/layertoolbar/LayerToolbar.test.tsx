// Must come before leaflet: lets Leaflet draw the vector layers.
import "../../testutils/leafletSvg";
import { renderWithProviders } from "../../testutils";
import { toggleOverlay } from "../../maplayers/layerToggle";
import LiberationMap from "../liberationmap";
import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

function renderMap(layerToolbar = true) {
  return renderWithProviders(<LiberationMap layerToolbar={layerToolbar} />);
}

function toggleButton(name: string) {
  const toolbar = screen.getByRole("toolbar", { name: "Map layers" });
  return within(toolbar).getByRole("button", { name });
}

beforeEach(() => {
  window.localStorage.clear();
});

describe("layer toolbar", () => {
  it("shows the five main layers with their default state", () => {
    renderMap();
    expect(toggleButton("Front lines")).toHaveAttribute("aria-pressed", "true");
    expect(toggleButton("Threat zones")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(toggleButton("Flight plans")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(toggleButton("Supply routes")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(toggleButton("Ranges")).toHaveAttribute("aria-pressed", "true");
    expect(toggleButton("Front lines")).toHaveAttribute(
      "aria-keyshortcuts",
      "1",
    );
  });

  it("toggles a layer on click", async () => {
    renderMap();
    await userEvent.click(toggleButton("Supply routes"));
    expect(toggleButton("Supply routes")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    await userEvent.click(toggleButton("Threat zones"));
    expect(toggleButton("Threat zones")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("follows the 1-5 shortcuts", () => {
    renderMap();
    act(() => {
      expect(toggleOverlay("frontLines")).toBe(true);
    });
    expect(toggleButton("Front lines")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("hides the expanded Leaflet layer controls", () => {
    const { container } = renderMap();
    expect(
      container.querySelector(
        ".liberation-map--toolbar .leaflet-control-layers",
      ),
    ).not.toBeNull();
  });

  it("keeps the Leaflet controls in the Qt map", () => {
    const { container } = renderMap(false);
    expect(screen.queryByRole("toolbar")).toBeNull();
    expect(container.querySelector(".liberation-map--toolbar")).toBeNull();
  });

  it("lists every overlay and basemap under More layers", async () => {
    renderMap();
    await userEvent.click(toggleButton("More layers"));
    const menu = await screen.findByRole("menu", { name: "More layers" });
    expect(
      within(menu).getByRole("menuitemradio", { name: /Dark gray/ }),
    ).toHaveAttribute("aria-checked", "true");
    const factories = within(menu).getByRole("menuitemcheckbox", {
      name: /Factories/,
    });
    expect(factories).toHaveAttribute("aria-checked", "true");
    // Debug layers stay reachable.
    expect(
      within(menu).getByRole("menuitemcheckbox", { name: /Blue navmesh/ }),
    ).toHaveAttribute("aria-checked", "false");

    await userEvent.click(factories);
    // The menu stays open to toggle several layers in a row.
    expect(
      within(menu).getByRole("menuitemcheckbox", { name: /Factories/ }),
    ).toHaveAttribute("aria-checked", "false");
  });

  it("switches and remembers the basemap", async () => {
    renderMap();
    await userEvent.click(toggleButton("More layers"));
    const menu = await screen.findByRole("menu", { name: "More layers" });
    await userEvent.click(
      within(menu).getByRole("menuitemradio", { name: /Topographic/ }),
    );
    expect(
      within(menu).getByRole("menuitemradio", { name: /Topographic/ }),
    ).toHaveAttribute("aria-checked", "true");
    expect(
      within(menu).getByRole("menuitemradio", { name: /Dark gray/ }),
    ).toHaveAttribute("aria-checked", "false");
    expect(window.localStorage.getItem("retribution.map.basemap")).toBe(
      "Topographic",
    );
  });
});

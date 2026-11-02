import { AircraftOption, AircraftOptions } from "./AircraftOptions";
import { render, screen, within } from "@testing-library/react";

const TOMCAT: AircraftOption = {
  id: "f14",
  name: "F-14B",
  playerModule: true,
  squadrons: 2,
};
const HORNET: AircraftOption = {
  id: "f18",
  name: "F/A-18C",
  playerModule: false,
  squadrons: 0,
};

function renderOptions(options: AircraftOption[], grouped?: boolean) {
  render(
    <select aria-label="Aircraft">
      <AircraftOptions options={options} grouped={grouped} />
    </select>,
  );
}

describe("AircraftOptions", () => {
  it("puts the player's modules first, marked, with their squadron count", () => {
    renderOptions([HORNET, TOMCAT]);
    const groups = screen.getAllByRole("group");
    expect(groups[0]).toHaveAccessibleName("Your modules");
    expect(within(groups[0]).getByRole("option").textContent).toBe(
      "★ F-14B · 2",
    );
    expect(groups[1]).toHaveAccessibleName("AI only");
  });

  it("shows no count for an aircraft without squadron", () => {
    renderOptions([HORNET]);
    expect(screen.getByRole("option").textContent).toBe("F/A-18C");
  });

  it("has no group while no module is declared, or on the enemy side", () => {
    renderOptions([HORNET]);
    expect(screen.queryByRole("group")).toBeNull();
  });

  it("keeps a flat list when not grouped", () => {
    renderOptions([TOMCAT, HORNET], false);
    expect(screen.queryByRole("group")).toBeNull();
    expect(screen.getAllByRole("option")).toHaveLength(2);
  });
});

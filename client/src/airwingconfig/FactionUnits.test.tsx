import { FactionSheet } from "../api/liberationApi";
import { compareNames } from "../preferences/AircraftOptions";
import { FactionUnits } from "./FactionUnits";
import { render, screen, within } from "@testing-library/react";

const SHEET: FactionSheet = {
  name: "USA 2005",
  description: "",
  authors: "",
  requirements: {},
  has_jtac: true,
  doctrine: "modern",
  doctrines: ["modern"],
  groups: [
    {
      key: "aircraft",
      label: "Aircraft",
      units: ["F-14B Tomcat", "F-100 Super Sabre", "A-10A", "A-4E"],
      addable: ["UH-1H", "Mi-8MTV2 Hip", "A-20G Havoc"],
      player_modules: ["F-14B Tomcat", "Mi-8MTV2 Hip"],
    },
  ],
};

function renderUnits(markModules: boolean) {
  render(
    <FactionUnits
      sheet={SHEET}
      hasJtac
      doctrine="modern"
      markModules={markModules}
      onAddUnit={() => {}}
      onJtacChange={() => {}}
      onDoctrineChange={() => {}}
    />,
  );
}

function texts(elements: HTMLElement[]) {
  return elements.map((element) => element.textContent);
}

describe("FactionUnits", () => {
  it("sorts the units with their numbers in order", () => {
    renderUnits(false);
    expect(texts(screen.getAllByRole("listitem"))).toEqual([
      "A-4E",
      "A-10A",
      "F-14B Tomcat",
      "F-100 Super Sabre",
    ]);
  });

  it("marks the player's modules, and offers them first to add", () => {
    renderUnits(true);
    expect(screen.getByText("★ F-14B Tomcat")).toBeInTheDocument();
    const own = screen.getByRole("group", { name: "Your modules" });
    expect(within(own).getByRole("option").textContent).toBe("★ Mi-8MTV2 Hip");
    expect(screen.getByLabelText("Unit to add to Aircraft")).toHaveValue(
      "Mi-8MTV2 Hip",
    );
    const others = screen.getByRole("group", { name: "AI only" });
    expect(texts(within(others).getAllByRole("option"))).toEqual([
      "A-20G Havoc",
      "UH-1H",
    ]);
  });

  it("marks nothing on the enemy side", () => {
    renderUnits(false);
    expect(screen.getByText("F-14B Tomcat")).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Your modules" })).toBeNull();
  });
});

describe("compareNames", () => {
  it("puts F-14 before F-100", () => {
    expect(["F-100", "F-14", "F-4"].sort(compareNames)).toEqual([
      "F-4",
      "F-14",
      "F-100",
    ]);
  });
});

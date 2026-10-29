import { Catalog } from "./Catalog";
import { render, screen } from "@testing-library/react";

describe("Catalog", () => {
  it("shows a section for every component", () => {
    render(<Catalog />);
    for (const name of [
      "Colours",
      "Typography",
      "Buttons",
      "Tabs",
      "Switch · Number field · Slider",
      "Task tags · Gauges",
      "List cards",
      "Table",
      "Modal · Toast · Tooltip",
      "Military symbols (APP-6)",
      "Side panel (right)",
    ]) {
      expect(screen.getByRole("region", { name })).toBeInTheDocument();
    }
    expect(screen.getAllByRole("complementary")).toHaveLength(2);
  });
});

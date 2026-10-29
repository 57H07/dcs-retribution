import { Slider } from "./Slider";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

function Example({ onCommit }: { onCommit?: (value: number) => void }) {
  const [value, setValue] = useState(40);
  return (
    <Slider
      label="Threat range"
      value={value}
      onValueChange={setValue}
      onValueCommit={onCommit}
      max={100}
      step={5}
      format={(v) => `${v} nm`}
    />
  );
}

describe("Slider", () => {
  it("is a slider named by its label with a readable value", () => {
    render(<Example />);
    const slider = screen.getByRole("slider", { name: "Threat range" });
    expect(slider).toHaveAttribute("aria-valuenow", "40");
    expect(slider).toHaveAttribute("aria-valuetext", "40 nm");
    expect(slider).toHaveAttribute("aria-valuemax", "100");
  });

  it("moves by one step with the arrow keys and to the ends with Home/End", async () => {
    const onCommit = vi.fn();
    render(<Example onCommit={onCommit} />);
    const slider = screen.getByRole("slider");
    await userEvent.tab();
    expect(slider).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}");
    expect(slider).toHaveAttribute("aria-valuenow", "45");
    expect(onCommit).toHaveBeenLastCalledWith(45);
    await userEvent.keyboard("{End}");
    expect(slider).toHaveAttribute("aria-valuenow", "100");
    await userEvent.keyboard("{Home}");
    expect(slider).toHaveAttribute("aria-valuenow", "0");
  });
});

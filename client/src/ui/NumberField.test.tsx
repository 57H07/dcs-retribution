import { NumberField } from "./NumberField";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

function Example({
  initial = 12,
  onChange,
  step,
}: {
  initial?: number;
  onChange?: (value: number) => void;
  step?: number;
}) {
  const [value, setValue] = useState(initial);
  return (
    <NumberField
      label="Pilots"
      value={value}
      min={1}
      max={24}
      step={step}
      onValueChange={(next) => {
        setValue(next);
        onChange?.(next);
      }}
    />
  );
}

describe("NumberField", () => {
  it("is a spinbutton with its value and bounds", () => {
    render(<Example />);
    const input = screen.getByRole("spinbutton", { name: "Pilots" });
    expect(input).toHaveValue("12");
    expect(input).toHaveAttribute("aria-valuenow", "12");
    expect(input).toHaveAttribute("aria-valuemin", "1");
    expect(input).toHaveAttribute("aria-valuemax", "24");
  });

  it("steps with the arrow, page and Home/End keys", async () => {
    render(<Example />);
    const input = screen.getByRole("spinbutton");
    await userEvent.click(input);
    await userEvent.keyboard("{ArrowUp}");
    expect(input).toHaveAttribute("aria-valuenow", "13");
    await userEvent.keyboard("{ArrowDown}{ArrowDown}");
    expect(input).toHaveAttribute("aria-valuenow", "11");
    await userEvent.keyboard("{PageUp}");
    expect(input).toHaveAttribute("aria-valuenow", "21");
    await userEvent.keyboard("{End}");
    expect(input).toHaveAttribute("aria-valuenow", "24");
    await userEvent.keyboard("{Home}");
    expect(input).toHaveAttribute("aria-valuenow", "1");
  });

  it("commits typed text on Enter, clamped to the bounds", async () => {
    const onChange = vi.fn();
    render(<Example onChange={onChange} />);
    const input = screen.getByRole("spinbutton");
    await userEvent.tripleClick(input);
    await userEvent.keyboard("99{Enter}");
    expect(onChange).toHaveBeenLastCalledWith(24);
    expect(input).toHaveValue("24");
  });

  it("restores the value when the text is not a number", async () => {
    const onChange = vi.fn();
    render(<Example onChange={onChange} />);
    const input = screen.getByRole("spinbutton");
    await userEvent.tripleClick(input);
    await userEvent.keyboard("abc");
    expect(input).toHaveAttribute("aria-invalid", "true");
    await userEvent.tab();
    expect(input).toHaveValue("12");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("steps with the − and + buttons and rounds to the step", async () => {
    render(<Example initial={1.1} step={0.1} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Increase Pilots" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Increase Pilots" }),
    );
    expect(screen.getByRole("spinbutton")).toHaveValue("1.3");
    expect(
      screen.getByRole("button", { name: "Decrease Pilots" }),
    ).toBeEnabled();
  });

  it("disables the − button at the minimum", () => {
    render(<Example initial={1} />);
    expect(
      screen.getByRole("button", { name: "Decrease Pilots" }),
    ).toBeDisabled();
  });
});

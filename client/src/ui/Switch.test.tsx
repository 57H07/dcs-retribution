import { Switch } from "./Switch";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

function Controlled() {
  const [on, setOn] = useState(false);
  return <Switch label="Enable CSAR" checked={on} onCheckedChange={setOn} />;
}

describe("Switch", () => {
  it("is a switch named by its visible label", () => {
    render(<Controlled />);
    expect(screen.getByRole("switch", { name: "Enable CSAR" })).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("toggles with Space and with a click on the label", async () => {
    render(<Controlled />);
    const toggle = screen.getByRole("switch");
    await userEvent.tab();
    expect(toggle).toHaveFocus();
    await userEvent.keyboard(" ");
    expect(toggle).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByText("Enable CSAR"));
    expect(toggle).toHaveAttribute("aria-checked", "false");
  });

  it("accepts an aria-label without visible label", () => {
    render(<Switch aria-label="Allow leveling" defaultChecked />);
    expect(
      screen.getByRole("switch", { name: "Allow leveling" }),
    ).toHaveAttribute("aria-checked", "true");
  });

  it("does not toggle when disabled", async () => {
    const onChange = vi.fn();
    render(<Switch label="Locked" disabled onCheckedChange={onChange} />);
    await userEvent.click(screen.getByRole("switch"));
    expect(onChange).not.toHaveBeenCalled();
  });
});

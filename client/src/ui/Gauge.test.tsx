import { Gauge } from "./Gauge";
import { render, screen } from "@testing-library/react";

describe("Gauge", () => {
  it("is a progress bar named by its label", () => {
    render(<Gauge label="Aircraft" value={10} max={12} />);
    const bar = screen.getByRole("progressbar", { name: "Aircraft" });
    expect(bar).toHaveAttribute("aria-valuenow", "10");
    expect(bar).toHaveAttribute("aria-valuemax", "12");
    expect(bar).toHaveAttribute("aria-valuetext", "10/12");
    expect(screen.getByText("10/12")).toBeInTheDocument();
  });

  it("clamps the value and fills the bar proportionally", () => {
    const { container } = render(
      <Gauge
        label="Runway"
        value={150}
        max={100}
        tone="success"
        valueText="OK"
      />,
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "100",
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuetext",
      "OK",
    );
    const indicator = container.querySelector<HTMLElement>(
      "[data-state] > [data-state]",
    );
    expect(indicator?.style.width).toBe("100%");
    expect(indicator?.style.background).toBe("var(--ui-color-success)");
  });

  it("can hide its label and value text", () => {
    render(<Gauge label="Readiness" hideLabel value={30} valueText={null} />);
    expect(
      screen.getByRole("progressbar", { name: "Readiness" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("30/100")).not.toBeInTheDocument();
  });
});

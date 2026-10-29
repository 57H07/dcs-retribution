import { Button } from "./Button";
import { Tooltip } from "./Tooltip";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

describe("Tooltip", () => {
  it("shows on keyboard focus and describes its trigger", async () => {
    render(
      <Tooltip content="Opens the settings" delayDuration={0}>
        <Button>Settings</Button>
      </Tooltip>,
    );
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    await userEvent.tab();
    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toHaveTextContent("Opens the settings");
    expect(
      screen.getByRole("button", { name: "Settings" }),
    ).toHaveAccessibleDescription("Opens the settings");
  });

  it("hides with Escape", async () => {
    render(
      <Tooltip content="Hint" delayDuration={0}>
        <Button>Help</Button>
      </Tooltip>,
    );
    await userEvent.tab();
    await screen.findByRole("tooltip");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});

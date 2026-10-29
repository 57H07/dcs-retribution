import { Button, IconButton } from "./Button";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

describe("Button", () => {
  it.each(["primary", "secondary", "danger", "ghost"] as const)(
    "renders the %s variant as a button",
    (variant) => {
      render(<Button variant={variant}>Go</Button>);
      const button = screen.getByRole("button", { name: "Go" });
      expect(button).toHaveAttribute("data-variant", variant);
      expect(button).toHaveAttribute("type", "button");
    },
  );

  it("activates with the keyboard", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    await userEvent.tab();
    expect(screen.getByRole("button")).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard(" ");
    expect(onClick).toHaveBeenCalledTimes(2);
  });

  it("does nothing when disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Go
      </Button>,
    );
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("styles a link with asChild", () => {
    render(
      <Button asChild variant="primary">
        <a href="#air-wing">Air wing</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "Air wing" });
    expect(link).toHaveAttribute("data-variant", "primary");
    expect(link).not.toHaveAttribute("type");
  });
});

describe("IconButton", () => {
  it("is named by its aria-label", () => {
    render(
      <IconButton aria-label="Settings">
        <svg aria-hidden="true" />
      </IconButton>,
    );
    expect(screen.getByRole("button", { name: "Settings" })).toHaveAttribute(
      "data-variant",
      "ghost",
    );
  });
});

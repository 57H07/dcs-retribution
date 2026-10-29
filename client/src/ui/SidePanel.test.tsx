import { SidePanel } from "./SidePanel";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

describe("SidePanel", () => {
  it("is a complementary landmark named by its title", () => {
    render(<SidePanel title="Packages">Content</SidePanel>);
    expect(
      screen.getByRole("complementary", { name: "Packages" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Content")).toBeVisible();
  });

  it("collapses to a rail and expands again with its toggle", async () => {
    const onOpenChange = vi.fn();
    render(
      <SidePanel title="Packages" onOpenChange={onOpenChange}>
        Content
      </SidePanel>,
    );
    const toggle = screen.getByRole("button", { name: "Collapse Packages" });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await userEvent.click(toggle);
    expect(onOpenChange).toHaveBeenLastCalledWith(false);
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
    const expand = screen.getByRole("button", { name: "Expand Packages" });
    expect(expand).toHaveAttribute("aria-expanded", "false");
    expand.focus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("follows a controlled open state", () => {
    render(
      <SidePanel title="Flight" side="right" open={false}>
        Content
      </SidePanel>,
    );
    expect(
      screen.getByRole("button", { name: "Expand Flight" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
  });
});

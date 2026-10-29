import { Tabs, TabsContent, TabsList, TabsTrigger } from "./Tabs";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

function Example() {
  return (
    <Tabs defaultValue="general">
      <TabsList aria-label="Settings">
        <TabsTrigger value="general">General</TabsTrigger>
        <TabsTrigger value="pilots">Pilots</TabsTrigger>
        <TabsTrigger value="off" disabled>
          Off
        </TabsTrigger>
      </TabsList>
      <TabsContent value="general">General panel</TabsContent>
      <TabsContent value="pilots">Pilots panel</TabsContent>
    </Tabs>
  );
}

describe("Tabs", () => {
  it("renders a tab list with the selected panel", () => {
    render(<Example />);
    expect(
      screen.getByRole("tablist", { name: "Settings" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "General" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tabpanel")).toHaveTextContent("General panel");
  });

  it("moves between tabs with the arrow keys", async () => {
    render(<Example />);
    await userEvent.tab();
    expect(screen.getByRole("tab", { name: "General" })).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Pilots" })).toHaveFocus();
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Pilots panel");
  });

  it("selects a tab on click", async () => {
    render(<Example />);
    await userEvent.click(screen.getByRole("tab", { name: "Pilots" }));
    expect(screen.getByRole("tab", { name: "Pilots" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});

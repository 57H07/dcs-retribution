import { ListCard } from "./ListCard";
import { TaskTag } from "./TaskTag";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

describe("ListCard", () => {
  it("renders a static card without a button", () => {
    render(<ListCard title="Krymsk" meta="06:40" subtitle="2 × MiG-29S" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText("Krymsk")).toBeInTheDocument();
    expect(screen.getByText("06:40")).toBeInTheDocument();
    expect(screen.getByText("2 × MiG-29S")).toBeInTheDocument();
  });

  it("is a toggle button when selectable", async () => {
    const onSelect = vi.fn();
    render(
      <ListCard
        leading={<TaskTag task="DEAD" />}
        title="SA-11 Krasnodar East"
        selected
        onSelect={onSelect}
      />,
    );
    const card = screen.getByRole("button", { name: /SA-11 Krasnodar East/ });
    expect(card).toHaveAttribute("aria-pressed", "true");
    expect(card).toHaveTextContent("DEAD");
    await userEvent.tab();
    await userEvent.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("is not pressed when not selected, and inert when disabled", async () => {
    const onSelect = vi.fn();
    render(<ListCard title="Strike" onSelect={onSelect} disabled />);
    const card = screen.getByRole("button", { name: "Strike" });
    expect(card).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(card);
    expect(onSelect).not.toHaveBeenCalled();
  });
});

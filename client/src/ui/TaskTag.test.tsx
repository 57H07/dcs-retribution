import { TaskTag } from "./TaskTag";
import { render, screen } from "@testing-library/react";

describe("TaskTag", () => {
  it.each([
    ["BARCAP", "air"],
    ["AEW&C", "air"],
    ["DEAD", "suppression"],
    ["CAS", "groundAttack"],
    ["Strike", "strike"],
    ["CSAR", "rescue"],
    ["Refueling", "support"],
    ["Transport", "logistics"],
  ])("colours %s with the %s task colour", (task, family) => {
    render(<TaskTag task={task} />);
    const tag = screen.getByText(task);
    expect(tag).toHaveAttribute("data-task-family", family);
    const kebab = family.replace(/[A-Z]/g, (l) => `-${l.toLowerCase()}`);
    expect(tag.style.color).toBe(`var(--ui-task-${kebab}-fg)`);
    expect(tag.style.background).toBe(`var(--ui-task-${kebab}-bg)`);
  });

  it("falls back to the neutral colour for an unknown task", () => {
    render(<TaskTag task="Mystery" />);
    expect(screen.getByText("Mystery")).toHaveAttribute(
      "data-task-family",
      "logistics",
    );
  });
});

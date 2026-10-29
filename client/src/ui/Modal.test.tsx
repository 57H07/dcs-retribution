import { Button } from "./Button";
import { Modal, ModalClose } from "./Modal";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

function Example() {
  return (
    <Modal
      title="Delete package"
      description="Its flights will be removed."
      trigger={<Button>Open</Button>}
      footer={
        <ModalClose asChild>
          <Button>Cancel</Button>
        </ModalClose>
      }
    >
      Body text
    </Modal>
  );
}

describe("Modal", () => {
  it("opens from its trigger as a named, described dialog with focus inside", async () => {
    render(<Example />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    const dialog = screen.getByRole("dialog", { name: "Delete package" });
    expect(dialog).toHaveAccessibleDescription("Its flights will be removed.");
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    expect(dialog).toHaveTextContent("Body text");
  });

  it("closes with Escape and gives focus back to the trigger", async () => {
    render(<Example />);
    const open = screen.getByRole("button", { name: "Open" });
    await userEvent.click(open);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(open).toHaveFocus();
  });

  it("closes with the ✕ button and with a ModalClose action", async () => {
    render(<Example />);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("follows a controlled open state without description", () => {
    render(<Modal title="Settings" open onOpenChange={() => undefined} />);
    expect(
      screen.getByRole("dialog", { name: "Settings" }),
    ).toBeInTheDocument();
  });
});

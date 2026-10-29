import { ToastProvider, useToast } from "./Toast";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

function Trigger() {
  const toast = useToast();
  return (
    <button
      onClick={() =>
        toast({
          title: "Order placed",
          description: "Next turn.",
          tone: "success",
        })
      }
    >
      Notify
    </button>
  );
}

describe("Toast", () => {
  it("shows a notification and dismisses it with its button", async () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Notify" }));
    const toast = screen.getByText("Order placed").closest("li");
    expect(toast).toHaveAttribute("data-tone", "success");
    expect(toast).toHaveTextContent("Next turn.");
    expect(
      screen.getByRole("region", { name: /Notifications/ }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByText("Order placed")).not.toBeInTheDocument();
  });

  it("hides the notification after its duration", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      render(
        <ToastProvider duration={1000}>
          <Trigger />
        </ToastProvider>,
      );
      await userEvent.click(screen.getByRole("button", { name: "Notify" }));
      expect(screen.getByText("Order placed")).toBeInTheDocument();
      act(() => {
        vi.advanceTimersByTime(1500);
      });
      expect(screen.queryByText("Order placed")).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it("requires a provider", () => {
    // Keep React's and jsdom's reports of the expected error out of the log.
    const error = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    const swallow = (event: ErrorEvent) => event.preventDefault();
    window.addEventListener("error", swallow);
    try {
      expect(() => render(<Trigger />)).toThrow(/ToastProvider/);
    } finally {
      window.removeEventListener("error", swallow);
      error.mockRestore();
    }
  });
});

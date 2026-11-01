import { commandErrorMessage } from "../api/commands";
import { useToast } from "../ui";
import { useCallback } from "react";

type Result = { error?: unknown } | { data: unknown };

/**
 * Awaits a command and shows the server's refusal as a toast; `true` when it
 * was applied. The refusals are the engine's: nothing is decided here.
 */
export function useCommand() {
  const toast = useToast();
  return useCallback(
    async (pending: Promise<Result>, failure: string): Promise<boolean> => {
      const result = await pending;
      if ("error" in result && result.error !== undefined) {
        toast({
          title: failure,
          description: commandErrorMessage(
            result.error as Parameters<typeof commandErrorMessage>[0],
          ),
          tone: "danger",
        });
        return false;
      }
      return true;
    },
    [toast],
  );
}

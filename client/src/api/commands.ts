import { SerializedError } from "@reduxjs/toolkit";
import { FetchBaseQueryError } from "@reduxjs/toolkit/query";

/**
 * Readable message of a failed API command (see docs/dev/api-commands.md).
 *
 * The server refuses a command with a 4xx status and a `{ detail: string }` body
 * meant to be shown to the player as is. Anything else (network error, server
 * crash, validation error) gets a generic message.
 */
export function commandErrorMessage(
  error: FetchBaseQueryError | SerializedError | undefined,
): string | undefined {
  if (error === undefined) {
    return undefined;
  }
  if ("status" in error) {
    const data = error.data as { detail?: unknown } | undefined;
    if (typeof data?.detail === "string") {
      return data.detail;
    }
    return `The server could not run the command (${error.status}).`;
  }
  return error.message ?? "The server could not run the command.";
}

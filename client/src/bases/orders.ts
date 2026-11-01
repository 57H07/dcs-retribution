import { commandErrorMessage } from "../api/commands";

export type Refusal = Parameters<typeof commandErrorMessage>[0];
type Result = { error?: unknown } | { data: unknown };

/** The server's refusal of a mutation, or null when it went through. */
export function refusalOf(result: Result): Refusal | null {
  return "error" in result && result.error !== undefined
    ? (result.error as Refusal)
    : null;
}

export function signed(quantity: number): string {
  return quantity > 0 ? `+${quantity}` : `${quantity}`;
}

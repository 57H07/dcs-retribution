/** "$100M", "$2.5M", "-$18M": the money figures of the Qt base menu. */
export function money(millions: number): string {
  const amount = `$${Number(Math.abs(millions).toFixed(1))}M`;
  return millions < 0 ? `-${amount}` : amount;
}

// Display helpers of the packages panel (WEB-01.2). Formatting and filtering
// only: tasks, TOTs and missing pilots all come from the server.
import { Package, PackageFlight } from "../../api/liberationApi";

/** "07:12" from the server's naive ISO time ("2022-05-17T07:12:00"). */
export function formatTot(tot: string | null | undefined): string | undefined {
  if (tot == null) {
    return undefined;
  }
  const match = /T(\d{2}:\d{2})/.exec(tot);
  return match ? match[1] : undefined;
}

export function packageTitle(pkg: Package): string {
  return pkg.custom_name != null && pkg.custom_name !== ""
    ? pkg.custom_name
    : pkg.target;
}

/** "4 × F-16CM · Player": aircraft of a flight, and its player slots. */
export function flightSummary(flight: PackageFlight): string {
  const players =
    flight.clients > 0
      ? flight.clients === 1
        ? " · Player"
        : ` · ${flight.clients} players`
      : "";
  return `${flight.count} × ${flight.aircraft}${players}`;
}

export function missingPilotsLabel(count: number): string {
  return `Missing ${count} pilot${count === 1 ? "" : "s"}`;
}

/** True when the filter text appears in the package's name, task or aircraft. */
export function matchesFilter(pkg: Package, filter: string): boolean {
  const needle = filter.trim().toLowerCase();
  if (needle === "") {
    return true;
  }
  const haystack = [
    pkg.target,
    pkg.custom_name ?? "",
    pkg.description,
    pkg.task ?? "",
    ...pkg.flights.flatMap((f) => [f.aircraft, f.task, f.squadron]),
  ];
  return haystack.some((text) => text.toLowerCase().includes(needle));
}

/** The package flying this flight, if any. */
export function packageOfFlight(
  packages: Package[],
  flightId: string | null,
): Package | undefined {
  if (flightId == null) {
    return undefined;
  }
  return packages.find((p) => p.flights.some((f) => f.id === flightId));
}

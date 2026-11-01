// Shared by the General and Pilots tabs of a flight (WEB-04.2): the read model of
// `GET .../settings`, and refused commands as toasts. The engine lists what is possible
// and has the last word.
import { commandErrorMessage } from "../api/commands";
import {
  FlightSettings,
  useGetFlightSettingsQuery,
} from "../api/liberationApi";
import { useToast } from "../ui";
import styles from "./FlightSettings.module.css";
import { ReactNode } from "react";

export interface FlightTabProps {
  packageId: string;
  flightId: string;
}

type Result = { error?: unknown } | { data: unknown };

export function useReportRefusal() {
  const toast = useToast();
  return (title: string, result: Result) => {
    if ("error" in result && result.error !== undefined) {
      toast({
        title,
        description: commandErrorMessage(
          result.error as Parameters<typeof commandErrorMessage>[0],
        ),
        tone: "danger",
      });
    }
  };
}

export function FlightSettingsLoader({
  packageId,
  flightId,
  children,
}: FlightTabProps & { children: (settings: FlightSettings) => ReactNode }) {
  const { data, error, isLoading } = useGetFlightSettingsQuery({
    packageId,
    flightId,
  });
  // A squadron change replaces the flight: its refetch may answer 404 just before the
  // editor moves to the new one, so the last answer stays on screen.
  if (data != null) {
    return <>{children(data)}</>;
  }
  if (isLoading) {
    return <p className={styles.hint}>Loading…</p>;
  }
  return (
    <p className={styles.hint} role="alert">
      {(error && commandErrorMessage(error)) ?? "This flight is not available."}
    </p>
  );
}

/** A flight under way can only be aborted: its fields are read-only. */
export function UnderWayNotice({ settings }: { settings: FlightSettings }) {
  return settings.editable ? null : (
    <p className={styles.hint}>
      This flight is under way: only its name and callsign can change.
    </p>
  );
}

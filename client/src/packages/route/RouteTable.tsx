// Waypoint table of the Route tab (WEB-04.4): the place, name, altitude, time and fuel
// of each waypoint, as the engine computes them.
import { FlightRoute, FlightRouteWaypoint } from "../../api/liberationApi";
import { Button, NumberField, Table, TableColumn } from "../../ui";
import styles from "./RouteTab.module.css";
import { KeyboardEvent, ReactNode, useEffect, useState } from "react";

export interface RouteTableProps {
  route: FlightRoute;
  selectedIndex?: number;
  onSelect: (index: number) => void;
  onRename: (index: number, name: string) => void;
  onAltitude: (index: number, altitudeFt: number) => void;
  onDelete: (waypoint: FlightRouteWaypoint) => void;
}

/** "07:12:30" from the server's naive ISO time. */
function timeOfDay(time: string): string {
  return /T(\d{2}:\d{2}:\d{2})/.exec(time)?.[1] ?? "";
}

function timeLabel(waypoint: FlightRouteWaypoint): string {
  if (waypoint.time == null) {
    return "—";
  }
  const prefix = waypoint.time_kind === "depart" ? "Depart " : "";
  return `${prefix}${timeOfDay(waypoint.time)}`;
}

/** The table's rows answer Enter and Space: not while a control of theirs is used. */
function OwnKeys({ children }: { children: ReactNode }) {
  return (
    <span
      className={styles.control}
      onKeyDown={(event: KeyboardEvent) => event.stopPropagation()}
    >
      {children}
    </span>
  );
}

function NameField({
  waypoint,
  onRename,
}: {
  waypoint: FlightRouteWaypoint;
  onRename: (name: string) => void;
}) {
  const [draft, setDraft] = useState(waypoint.name);
  useEffect(() => setDraft(waypoint.name), [waypoint.name]);

  const commit = () => {
    if (draft !== waypoint.name) {
      onRename(draft);
    }
  };

  return (
    <input
      className={styles.name}
      aria-label={`Name of waypoint ${waypoint.index}`}
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          commit();
        }
      }}
    />
  );
}

export function RouteTable({
  route,
  selectedIndex,
  onSelect,
  onRename,
  onAltitude,
  onDelete,
}: RouteTableProps) {
  const columns: TableColumn<FlightRouteWaypoint>[] = [
    {
      key: "index",
      header: "#",
      mono: true,
      cell: (waypoint) => waypoint.index,
    },
    {
      key: "name",
      header: "Waypoint",
      cell: (waypoint) => (
        <span className={styles.nameCell}>
          <OwnKeys>
            <NameField
              waypoint={waypoint}
              onRename={(name) => onRename(waypoint.index, name)}
            />
          </OwnKeys>
          {waypoint.threat != null && (
            <span
              className={styles.threat}
              role="img"
              aria-label={waypoint.threat}
              title={waypoint.threat}
            >
              ⚠
            </span>
          )}
        </span>
      ),
    },
    {
      key: "altitude",
      header: "Alt (ft)",
      align: "end",
      mono: true,
      cell: (waypoint) => (
        <OwnKeys>
          <NumberField
            label={`Altitude of waypoint ${waypoint.index}`}
            hideLabel
            hideSteppers
            className={styles.altitude}
            value={waypoint.altitude_ft}
            min={route.min_altitude_ft}
            max={route.max_altitude_ft}
            step={1000}
            unit={waypoint.altitude_reference}
            onValueChange={(value) => {
              if (value !== waypoint.altitude_ft) {
                onAltitude(waypoint.index, value);
              }
            }}
          />
        </OwnKeys>
      ),
    },
    {
      key: "time",
      header: "Time",
      align: "end",
      mono: true,
      cell: (waypoint) => (
        <span className={waypoint.is_tot ? styles.tot : undefined}>
          {timeLabel(waypoint)}
        </span>
      ),
    },
    {
      key: "fuel",
      header: "Min fuel (lb)",
      align: "end",
      mono: true,
      cell: (waypoint) => waypoint.min_fuel_lb?.toLocaleString("en-US") ?? "—",
    },
    {
      key: "delete",
      header: "",
      align: "end",
      cell: (waypoint) =>
        waypoint.can_delete && (
          <OwnKeys>
            <Button
              variant="ghost"
              aria-label={`Delete waypoint ${waypoint.index}`}
              onClick={(event) => {
                event.stopPropagation();
                onDelete(waypoint);
              }}
            >
              ✕
            </Button>
          </OwnKeys>
        ),
    },
  ];

  return (
    <Table
      caption="Waypoints"
      hideCaption
      columns={columns}
      rows={route.waypoints}
      rowKey={(waypoint) => String(waypoint.index)}
      selectedKey={selectedIndex === undefined ? undefined : String(selectedIndex)}
      onRowClick={(waypoint) => onSelect(waypoint.index)}
    />
  );
}

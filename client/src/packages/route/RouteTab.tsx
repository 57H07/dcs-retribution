// Route tab of a flight (WEB-04.4, mockups/Package.dc.html): map and waypoint table,
// adding, removing and moving waypoints, recreating the route, threat warnings. Changes
// apply at once; the engine decides everything and refusals come back as toasts.
import { commandErrorMessage } from "../../api/commands";
import {
  FlightRoute,
  FlightRouteWaypoint,
  useAddFlightRtbWaypointMutation,
  useDeleteFlightWaypointMutation,
  useGetFlightRouteQuery,
  useInsertFlightNavWaypointMutation,
  useMoveFlightWaypointMutation,
  useRecreateFlightRouteMutation,
  useRenameFlightWaypointMutation,
  useSetFlightRouteAltitudeMutation,
  useSetFlightWaypointAltitudeMutation,
} from "../../api/liberationApi";
import settings from "../../settings/SettingsScreen.module.css";
import { Button, Modal, ModalClose, NumberField, useToast } from "../../ui";
import editor from "../PackageEditor.module.css";
import { AddWaypointButton } from "./AddWaypointForm";
import { RouteMap } from "./RouteMap";
import styles from "./RouteTab.module.css";
import { RouteTable } from "./RouteTable";
import { LatLngLiteral } from "leaflet";
import { useState } from "react";

type Result = { error?: unknown } | { data: unknown };

/** Shows a refused command as a toast; true when it went through. */
function useReport() {
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
      return false;
    }
    return true;
  };
}

export function RouteTab({ flightId }: { flightId: string }) {
  const { data, error, isLoading } = useGetFlightRouteQuery({ flightId });
  if (isLoading) {
    return <p className={editor.hint}>Loading the route…</p>;
  }
  if (error) {
    return (
      <p className={editor.hint} role="alert">
        {commandErrorMessage(error) ?? "This route is not available."}
      </p>
    );
  }
  if (data == null) {
    return null;
  }
  return <RouteEditor route={data} />;
}

/** What waits for the player's word because it makes the flight plan custom. */
type Degrading = { rtb: true } | { rtb: false; waypoint: FlightRouteWaypoint };

function RouteEditor({ route }: { route: FlightRoute }) {
  const flightId = route.flight_id;
  const report = useReport();
  const [selectedIndex, setSelectedIndex] = useState<number>();
  const [degrading, setDegrading] = useState<Degrading>();
  const [task, setTask] = useState<string>();
  const [recreating, setRecreating] = useState(false);
  const [bulkAltitude, setBulkAltitude] = useState<number>();

  const [move] = useMoveFlightWaypointMutation();
  const [rename] = useRenameFlightWaypointMutation();
  const [setAltitude] = useSetFlightWaypointAltitudeMutation();
  const [setRouteAltitude] = useSetFlightRouteAltitudeMutation();
  const [deleteWaypoint] = useDeleteFlightWaypointMutation();
  const [insertNav] = useInsertFlightNavWaypointMutation();
  const [addRtb] = useAddFlightRtbWaypointMutation();
  const [recreate, recreateState] = useRecreateFlightRouteMutation();

  const selected = route.waypoints.find((w) => w.index === selectedIndex);
  const threats = route.waypoints.flatMap((w) => w.threat ?? []);
  const recreateTask = task ?? route.recreate_tasks[0];

  const moved = async (index: number, position: LatLngLiteral) =>
    report(
      "Could not move the waypoint",
      await move({ flightId, index, leafletPoint: position }),
    );

  const remove = async (waypoint: FlightRouteWaypoint, allowDegrade: boolean) =>
    report(
      "Could not delete the waypoint",
      await deleteWaypoint({ flightId, index: waypoint.index, allowDegrade }),
    );

  const askDelete = (waypoint: FlightRouteWaypoint) => {
    if (waypoint.delete_degrades) {
      setDegrading({ rtb: false, waypoint });
    } else {
      remove(waypoint, false);
    }
  };

  const rtb = async (allowDegrade: boolean) =>
    report(
      "Could not add the waypoint",
      await addRtb({ flightId, allowDegrade }),
    );

  const confirmDegrade = () => {
    if (degrading?.rtb === false) {
      remove(degrading.waypoint, true);
    } else {
      rtb(true);
    }
    setDegrading(undefined);
  };

  const confirmRecreate = async () => {
    const result = await recreate({
      flightId,
      recreateRouteJs: { task: recreateTask },
    });
    setRecreating(false);
    setTask(undefined);
    report("Could not recreate the route", result);
  };

  return (
    <div className={styles.tab}>
      <div className={styles.panels}>
        <div className={styles.mapPanel}>
          <RouteMap
            route={route}
            selectedIndex={selectedIndex}
            onSelect={setSelectedIndex}
            onMove={moved}
          />
        </div>
        <div className={styles.tablePanel}>
          <RouteTable
            route={route}
            selectedIndex={selectedIndex}
            onSelect={setSelectedIndex}
            onRename={async (index, name) =>
              report(
                "Could not rename the waypoint",
                await rename({
                  flightId,
                  index,
                  waypointNameJs: { name },
                }),
              )
            }
            onAltitude={async (index, altitude_ft) =>
              report(
                "Could not set the altitude",
                await setAltitude({
                  flightId,
                  index,
                  waypointAltitudeJs: { altitude_ft },
                }),
              )
            }
            onDelete={askDelete}
          />
        </div>
      </div>
      <div className={styles.actions}>
        <Button
          disabled={!selected?.can_insert_after}
          title={
            selected === undefined
              ? "Select the waypoint it follows."
              : selected.can_insert_after
                ? undefined
                : "A NAV point cannot follow this waypoint."
          }
          onClick={async () => {
            if (selected !== undefined) {
              report(
                "Could not add the NAV point",
                await insertNav({ flightId, index: selected.index }),
              );
            }
          }}
        >
          Insert NAV point
        </Button>
        <AddWaypointButton flightId={flightId} />
        <Button
          title="For player flights: AI flights do not fly it."
          onClick={() =>
            route.is_custom ? rtb(false) : setDegrading({ rtb: true })
          }
        >
          Add RTB waypoint
        </Button>
        <span className={styles.group}>
          <NumberField
            label="Altitude of all en-route waypoints"
            hideLabel
            hideSteppers
            className={styles.altitude}
            value={bulkAltitude ?? route.bulk_altitude_ft}
            min={route.min_altitude_ft}
            max={route.max_altitude_ft}
            step={1000}
            unit="ft"
            onValueChange={setBulkAltitude}
          />
          <Button
            title="Takeoff, landing, divert, target, landing-zone, tanker and AGL waypoints are left unchanged."
            onClick={async () => {
              report(
                "Could not set the altitude",
                await setRouteAltitude({
                  flightId,
                  waypointAltitudeJs: {
                    altitude_ft: bulkAltitude ?? route.bulk_altitude_ft,
                  },
                }),
              );
              setBulkAltitude(undefined);
            }}
          >
            Apply to all
          </Button>
        </span>
        <span className={styles.group}>
          <select
            className={settings.select}
            aria-label="Task of the recreated route"
            value={recreateTask}
            onChange={(event) => setTask(event.target.value)}
          >
            {route.recreate_tasks.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <Button onClick={() => setRecreating(true)}>Recreate route</Button>
        </span>
      </div>
      {route.is_custom && (
        <p className={editor.hint}>
          Custom flight plan: it no longer respects the TOTs of the package.
          Recreating the route brings them back.
        </p>
      )}
      {threats.length > 0 && (
        <ul className={styles.threats} aria-label="Threat warnings">
          {threats.map((threat) => (
            <li key={threat}>{threat}</li>
          ))}
        </ul>
      )}
      <Modal
        title="Make this a custom flight plan?"
        description="This change requires a custom flight plan, which no longer respects the TOTs of the package."
        open={degrading !== undefined}
        onOpenChange={(open) => {
          if (!open) {
            setDegrading(undefined);
          }
        }}
        footer={
          <>
            <ModalClose asChild>
              <Button variant="ghost">Cancel</Button>
            </ModalClose>
            <Button variant="danger" onClick={confirmDegrade}>
              Continue
            </Button>
          </>
        }
      />
      <Modal
        title="Recreate the route?"
        description={`The route is planned again as ${recreateTask}: your changes to it are lost.`}
        open={recreating}
        onOpenChange={setRecreating}
        footer={
          <>
            <ModalClose asChild>
              <Button variant="ghost">Cancel</Button>
            </ModalClose>
            <Button
              variant="danger"
              disabled={recreateState.isLoading}
              onClick={confirmRecreate}
            >
              Recreate
            </Button>
          </>
        }
      />
    </div>
  );
}

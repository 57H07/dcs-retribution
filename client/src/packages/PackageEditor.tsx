// Package editor (WEB-04.1), after mockups/Package.dc.html: task, target, TOT and
// flights of a package. Changes apply at once (no save step); the engine decides
// everything and refusals come back as toasts. The right side is the frame of the
// flight screens: see FlightSections.tsx.
import { commandErrorMessage } from "../api/commands";
import {
  PackageDetail,
  PackageEditorFlight,
  useDeletePackageMutation,
  useGetPackageQuery,
  useRemovePackageFlightMutation,
  useRenamePackageMutation,
  useSetPackageTotEarliestMutation,
  useSetPackageTotMutation,
} from "../api/liberationApi";
import { selectPackage } from "../api/selectionSlice";
import { useAppDispatch } from "../app/hooks";
import {
  flightSummary,
  formatTot,
  missingPilotsLabel,
} from "../command/packages/packageFormat";
import settings from "../settings/SettingsScreen.module.css";
import { PATHS } from "../shell/paths";
import { Button, ListCard, TaskTag, useToast } from "../ui";
import { AddFlightButton } from "./AddFlightForm";
import { AutoCreateButton } from "./AutoCreateForm";
import { FlightSections } from "./FlightSections";
import styles from "./PackageEditor.module.css";
import { TransportEntry } from "./TransportEntry";
import { KeyboardEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

type Result = { error?: unknown } | { data: unknown };

/** Shows a refused command as a toast. */
function useReportRefusal() {
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

/** "07:12:30" from the server's naive ISO time. */
function timeOfDay(tot: string | null | undefined): string {
  return tot == null ? "" : (/T(\d{2}:\d{2}:\d{2})/.exec(tot)?.[1] ?? "");
}

function subtitle(pkg: PackageDetail): string {
  const parts = [];
  if (pkg.custom_name != null) {
    parts.push(pkg.custom_name);
  }
  if (pkg.closest_base != null) {
    parts.push(`${pkg.closest_base_distance_nm} nm from ${pkg.closest_base}`);
  }
  return parts.join(" · ");
}

export function PackageEditor() {
  const { id = "" } = useParams();
  const { data, error, isLoading } = useGetPackageQuery({ packageId: id });

  return (
    <div className={settings.screen}>
      <header className={settings.header}>
        <Link to={PATHS.command} className={settings.back}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M15 6l-6 6 6 6" />
          </svg>
          Command view
        </Link>
        <span className={settings.divider} />
        {data && !error ? (
          <PackageHeader pkg={data} />
        ) : (
          <h1 className={settings.title}>Package</h1>
        )}
      </header>
      {isLoading ? (
        <p className={styles.state}>Loading the package…</p>
      ) : error ? (
        <p className={styles.state} role="alert">
          {commandErrorMessage(error) ?? "This package is not available."}
        </p>
      ) : data == null ? (
        <p className={styles.state}>No campaign loaded.</p>
      ) : (
        <PackageBody pkg={data} />
      )}
    </div>
  );
}

function PackageHeader({ pkg }: { pkg: PackageDetail }) {
  const navigate = useNavigate();
  const report = useReportRefusal();
  const [setEarliest, earliestState] = useSetPackageTotEarliestMutation();
  const [deletePackage, deleteState] = useDeletePackageMutation();

  const earliest = async () =>
    report(
      "Could not set the earliest TOT",
      await setEarliest({ packageId: pkg.id }),
    );

  const remove = async () => {
    const result = await deletePackage({ packageId: pkg.id });
    report("Could not delete the package", result);
    if (!("error" in result)) {
      navigate(PATHS.command);
    }
  };

  const detail = subtitle(pkg);
  return (
    <>
      <TaskTag task={pkg.task ?? pkg.description} />
      <h1 className={settings.title}>{pkg.target}</h1>
      {detail !== "" && <span className={styles.subtitle}>{detail}</span>}
      <span className={styles.spacer} />
      <TotField pkg={pkg} />
      <Button
        aria-pressed={pkg.auto_asap}
        title="Sets the TOT to the earliest time all flights can reach the target, and keeps it there when flights change."
        disabled={pkg.tot_locked || earliestState.isLoading}
        onClick={earliest}
      >
        Earliest TOT
      </Button>
      <Button
        variant="danger"
        disabled={deleteState.isLoading}
        onClick={remove}
      >
        Delete package
      </Button>
    </>
  );
}

function TotField({ pkg }: { pkg: PackageDetail }) {
  const report = useReportRefusal();
  const [setTot] = useSetPackageTotMutation();
  const current = timeOfDay(pkg.tot);
  const [draft, setDraft] = useState(current);

  useEffect(() => setDraft(current), [current]);

  const commit = async () => {
    if (draft === "" || draft === current) {
      setDraft(current);
      return;
    }
    // An input may leave out zero seconds ("07:12").
    const tot = draft.length === 5 ? `${draft}:00` : draft;
    if (tot === current) {
      return;
    }
    const result = await setTot({
      packageId: pkg.id,
      packageTotJs: { tot },
    });
    report("Could not set the TOT", result);
    if ("error" in result) {
      setDraft(current);
    }
  };

  return (
    <label className={styles.tot}>
      <span className={styles.totLabel}>Time on target</span>
      <input
        className={styles.totInput}
        type="time"
        step={1}
        value={draft}
        disabled={pkg.tot_locked}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
          if (event.key === "Enter") {
            commit();
          }
        }}
      />
    </label>
  );
}

function PackageBody({ pkg }: { pkg: PackageDetail }) {
  const dispatch = useAppDispatch();
  const report = useReportRefusal();
  const [removeFlight, removeState] = useRemovePackageFlightMutation();
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const selected =
    pkg.flights.find((flight) => flight.id === selectedId) ?? pkg.flights[0];

  // The map shows the flight plan of the flight being edited, as in the panel.
  const selectedFlightId = selected?.id;
  useEffect(() => {
    selectPackage(dispatch, pkg.id, selectedFlightId);
  }, [dispatch, pkg.id, selectedFlightId]);

  const remove = async (flight: PackageEditorFlight) =>
    report(
      flight.cancelable
        ? "Could not remove the flight"
        : "Could not abort the flight",
      await removeFlight({ packageId: pkg.id, flightId: flight.id }),
    );

  return (
    <div className={styles.body}>
      <aside className={styles.side}>
        <PackageNameField pkg={pkg} />
        <div className={styles.flightsHeader}>
          <span className={styles.flightsTitle}>
            Flights · {pkg.flights.length}
          </span>
          <span className={styles.spacer} />
          {pkg.can_auto_create && <AutoCreateButton packageId={pkg.id} />}
          <AddFlightButton packageId={pkg.id} onAdded={setSelectedId} />
        </div>
        <TransportEntry pkg={pkg} />
        {pkg.flights.length === 0 ? (
          <p className={styles.hint}>
            No flight yet: add one or auto-create them. An empty package has no
            effect on the mission.
          </p>
        ) : (
          <ul className={styles.flights} aria-label="Flights">
            {pkg.flights.map((flight) => (
              <li key={flight.id}>
                <ListCard
                  selected={flight.id === selected?.id}
                  onSelect={() => setSelectedId(flight.id)}
                  title={flightSummary(flight)}
                  subtitle={
                    <>
                      <span>
                        {flight.task} · {flight.departure}
                      </span>
                      <span className={styles.times}>
                        Start {formatTot(flight.startup)} · T/O{" "}
                        {formatTot(flight.takeoff)}
                      </span>
                      {flight.missing_pilots > 0 && (
                        <span className={styles.warning}>
                          {missingPilotsLabel(flight.missing_pilots)}
                        </span>
                      )}
                    </>
                  }
                />
              </li>
            ))}
          </ul>
        )}
      </aside>
      <main className={styles.main}>
        {selected === undefined ? (
          <p className={styles.state}>
            The sections of a flight appear with the first flight.
          </p>
        ) : (
          <FlightSections
            key={selected.id}
            flight={selected}
            actions={
              <Button
                variant="danger"
                disabled={removeState.isLoading}
                onClick={() => remove(selected)}
              >
                {selected.cancelable ? "Remove flight" : "Abort flight"}
              </Button>
            }
          />
        )}
      </main>
    </div>
  );
}

function PackageNameField({ pkg }: { pkg: PackageDetail }) {
  const report = useReportRefusal();
  const [rename] = useRenamePackageMutation();
  const current = pkg.custom_name ?? "";
  const [draft, setDraft] = useState(current);

  useEffect(() => setDraft(current), [current]);

  const commit = async () => {
    if (draft !== current) {
      report(
        "Could not rename the package",
        await rename({ packageId: pkg.id, packageNameJs: { name: draft } }),
      );
    }
  };

  return (
    <label className={styles.name}>
      Package name
      <input
        className={styles.nameInput}
        value={draft}
        placeholder={pkg.target}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            commit();
          }
        }}
      />
    </label>
  );
}

// Packages panel of the command view (WEB-01.2): the friendly and enemy ATOs as
// cards, a filter, and the selection shared with the map through the selected
// flight of the flights slice (the map highlights its flight plan).
import { commandErrorMessage } from "../../api/commands";
import { selectFlight, selectSelectedFlightId } from "../../api/flightsSlice";
import {
  Package,
  useDeletePackageMutation,
  useListPackagesQuery,
} from "../../api/liberationApi";
import {
  selectedPackageId,
  selectPackage,
  selectSelectedPackageKey,
} from "../../api/selectionSlice";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { useQtCommands } from "../../shell/useQtCommands";
import {
  Button,
  ListCard,
  TaskTag,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useToast,
} from "../../ui";
import {
  flightSummary,
  formatTot,
  matchesFilter,
  missingPilotsLabel,
  packageTitle,
} from "./packageFormat";
import styles from "./PackagesPanel.module.css";
import { useEffect, useRef, useState } from "react";

type Side = "friendly" | "enemy";

export interface PackagesPanelProps {
  /** "+ New": how to plan a package (from a target on the map for now). */
  onNewPackage?: () => void;
}

export function PackagesPanel({ onNewPackage }: PackagesPanelProps) {
  const { data } = useListPackagesQuery();
  const packages = data ?? [];
  const dispatch = useAppDispatch();
  const selectedFlightId = useAppSelector(selectSelectedFlightId);
  const packageKey = useAppSelector(selectSelectedPackageKey);
  const [side, setSide] = useState<Side>("friendly");
  const [filter, setFilter] = useState("");

  // Shared with the timeline and the map (selectionSlice).
  const selectedId = selectedPackageId(
    packageKey,
    selectedFlightId,
    packages.map((p) => ({ id: p.id, flight_ids: p.flights.map((f) => f.id) })),
  );
  const selectedBlue = packages.find((p) => p.id === selectedId)?.blue;

  // A package picked on the map or the timeline shows its ATO (as in Qt).
  useEffect(() => {
    if (selectedBlue !== undefined) {
      setSide(selectedBlue ? "friendly" : "enemy");
    }
  }, [selectedId, selectedBlue]);

  const select = (pkg: Package) =>
    selectPackage(dispatch, pkg.id, pkg.flights[0]?.id);

  const friendly = packages.filter((p) => p.blue);
  const enemy = packages.filter((p) => !p.blue);
  const list = (items: Package[], emptyText: string) => {
    const shown = items.filter((p) => matchesFilter(p, filter));
    if (shown.length === 0) {
      return (
        <p className={styles.empty}>
          {items.length === 0 ? emptyText : "No package matches the filter."}
        </p>
      );
    }
    return (
      <ul className={styles.cards}>
        {shown.map((pkg) => (
          <PackageCard
            key={pkg.id}
            pkg={pkg}
            selected={pkg.id === selectedId}
            selectedFlightId={selectedFlightId}
            onSelect={() => select(pkg)}
          />
        ))}
      </ul>
    );
  };

  return (
    <Tabs
      className={styles.panel}
      value={side}
      onValueChange={(value) => setSide(value as Side)}
    >
      <TabsList stretch aria-label="Air tasking orders">
        <TabsTrigger value="friendly">Packages · {friendly.length}</TabsTrigger>
        <TabsTrigger value="enemy">Enemy ATO · {enemy.length}</TabsTrigger>
      </TabsList>
      <div className={styles.toolbar}>
        <input
          className={styles.filter}
          type="search"
          placeholder="Filter packages"
          aria-label="Filter packages"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        />
        {onNewPackage && (
          <Button variant="primary" onClick={onNewPackage}>
            + New
          </Button>
        )}
      </div>
      <TabsContent value="friendly" className={styles.content}>
        {list(friendly, "No package planned yet.")}
      </TabsContent>
      <TabsContent value="enemy" className={styles.content}>
        {list(enemy, "The enemy has no package planned.")}
      </TabsContent>
    </Tabs>
  );
}

interface PackageCardProps {
  pkg: Package;
  selected: boolean;
  selectedFlightId: string | null;
  onSelect: () => void;
}

function PackageCard({
  pkg,
  selected,
  selectedFlightId,
  onSelect,
}: PackageCardProps) {
  const dispatch = useAppDispatch();
  const qt = useQtCommands();
  const toast = useToast();
  const [deletePackage, { isLoading: deleting }] = useDeletePackageMutation();
  const ref = useRef<HTMLLIElement>(null);
  const tot = formatTot(pkg.tot);

  useEffect(() => {
    if (selected) {
      ref.current?.scrollIntoView?.({ block: "nearest" });
    }
  }, [selected]);

  const remove = async () => {
    const result = await deletePackage({ packageId: pkg.id });
    if ("error" in result) {
      toast({
        title: "Could not delete the package",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    }
  };

  const first = pkg.flights[0];
  return (
    <li ref={ref} className={styles.item} data-selected={selected || undefined}>
      <ListCard
        selected={selected}
        onSelect={onSelect}
        leading={<TaskTag task={pkg.task ?? pkg.description} />}
        title={packageTitle(pkg)}
        meta={tot && `TOT ${tot}`}
        subtitle={
          <>
            {pkg.flights.length === 0 && <span>No flight</span>}
            {pkg.flights.map((flight) => (
              <span key={flight.id}>{flightSummary(flight)}</span>
            ))}
            {pkg.missing_pilots > 0 && (
              <span className={styles.warning}>
                {missingPilotsLabel(pkg.missing_pilots)}
              </span>
            )}
          </>
        }
      />
      {selected && (
        <div className={styles.details}>
          {pkg.flights.length > 0 && (
            <ul className={styles.flights} aria-label="Flights">
              {pkg.flights.map((flight) => (
                <li key={flight.id}>
                  <button
                    type="button"
                    className={styles.flight}
                    aria-pressed={flight.id === selectedFlightId}
                    onClick={() => dispatch(selectFlight(flight.id))}
                  >
                    <span className={styles.flightTask}>{flight.task}</span>
                    <span>{flightSummary(flight)}</span>
                    <span className={styles.flightFrom}>
                      {flight.squadron} · {flight.departure}
                    </span>
                    {flight.missing_pilots > 0 && (
                      <span className={styles.warning}>
                        {missingPilotsLabel(flight.missing_pilots)}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className={styles.actions}>
            {pkg.blue && first !== undefined && (
              <Button onClick={() => qt.editPackageOfFlight(first.id)}>
                Edit
              </Button>
            )}
            <Button variant="danger" onClick={remove} disabled={deleting}>
              Delete
            </Button>
          </div>
        </div>
      )}
    </li>
  );
}

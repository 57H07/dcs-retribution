// Air Wing screen (WEB-03), after mockups/AirWing.dc.html: the Qt AirWingDialog
// and SquadronDialog. The engine sends every figure, status and refusal (GET
// /air-wing): this screen only lays them out and sends commands.
import {
  AirWing,
  AirWingSquadron,
  InventoryRow,
  useGetAirWingQuery,
} from "../api/liberationApi";
import { QueryBody, ScreenFrame } from "../secondary/ScreenFrame";
import { AIR_WING_VIEWS, AirWingView, PATHS } from "../shell/paths";
import {
  Button,
  ListCard,
  MilSymbol,
  Table,
  TableColumn,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../ui";
import styles from "./AirWing.module.css";
import { PilotsTable } from "./PilotsTable";
import { SquadronSheet } from "./SquadronSheet";
import { useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

const LABELS: Record<AirWingView, string> = {
  squadrons: "Squadrons",
  aircraft: "Aircraft",
  pilots: "Pilots",
};

function isView(value: string | undefined): value is AirWingView {
  return AIR_WING_VIEWS.includes(value as AirWingView);
}

function owned(squadron: AirWingSquadron): string {
  return squadron.max_aircraft != null
    ? `${squadron.owned}/${squadron.max_aircraft}`
    : `${squadron.owned}`;
}

function autoTasks(squadron: AirWingSquadron): string {
  return squadron.tasks
    .filter((t) => t.auto_assign)
    .map((t) => t.task)
    .join(", ");
}

function SquadronsView({ airWing }: { airWing: AirWing }) {
  const [selectedId, setSelectedId] = useState<string>();
  const squadrons = airWing.bases.flatMap((base) => base.squadrons);
  if (squadrons.length === 0) {
    return <p className={styles.hint}>This air wing has no squadron.</p>;
  }
  const selected =
    squadrons.find((squadron) => squadron.id === selectedId) ?? squadrons[0];
  return (
    <div className={styles.squadrons}>
      <aside className={styles.list} aria-label="Squadrons by base">
        {airWing.bases.map((base) => (
          <section key={base.id} className={styles.base} aria-label={base.name}>
            <h2 className={styles.baseName}>{base.name}</h2>
            {base.squadrons.map((squadron) => (
              <ListCard
                key={squadron.id}
                leading={
                  <MilSymbol
                    sidc={squadron.sidc}
                    size={20}
                    label={squadron.primary_task}
                  />
                }
                title={squadron.name}
                meta={owned(squadron)}
                subtitle={[squadron.aircraft, autoTasks(squadron)]
                  .filter(Boolean)
                  .join(" · ")}
                selected={squadron.id === selected.id}
                onSelect={() => setSelectedId(squadron.id)}
              />
            ))}
          </section>
        ))}
      </aside>
      <SquadronSheet key={selected.id} squadron={selected} />
    </div>
  );
}

const INVENTORY_COLUMNS: TableColumn<InventoryRow>[] = [
  { key: "base", header: "Base", cell: (r) => r.base, sortValue: (r) => r.base },
  {
    key: "aircraft",
    header: "Type",
    cell: (r) => r.aircraft,
    sortValue: (r) => r.aircraft,
  },
  { key: "task", header: "Task", cell: (r) => r.task, sortValue: (r) => r.task },
  {
    key: "target",
    header: "Target",
    cell: (r) => r.target,
    sortValue: (r) => r.target,
  },
  {
    key: "pilot",
    header: "Pilot",
    cell: (r) => r.pilot,
    sortValue: (r) => r.pilot,
  },
  {
    key: "crew",
    header: "Player",
    cell: (r) => r.crew,
    sortValue: (r) => r.crew,
  },
];

function AircraftView({ airWing }: { airWing: AirWing }) {
  const [unallocatedOnly, setUnallocatedOnly] = useState(false);
  const rows = useMemo(
    () =>
      unallocatedOnly
        ? airWing.inventory.filter((row) => !row.allocated)
        : airWing.inventory,
    [airWing.inventory, unallocatedOnly],
  );
  return (
    <div className={styles.view}>
      <label className={styles.check}>
        <input
          type="checkbox"
          checked={unallocatedOnly}
          onChange={(event) => setUnallocatedOnly(event.target.checked)}
        />
        Unallocated only
      </label>
      <Table
        caption="Aircraft"
        hideCaption
        columns={INVENTORY_COLUMNS}
        rows={rows}
        rowKey={(row) => row.key}
        emptyText="No aircraft."
      />
    </div>
  );
}

export function AirWingScreen() {
  const { view } = useParams();
  const navigate = useNavigate();
  const [enemy, setEnemy] = useState(false);
  const query = useGetAirWingQuery(
    { enemy },
    { refetchOnMountOrArgChange: true },
  );
  if (view !== undefined && !isView(view)) {
    return <Navigate to={PATHS.airWing} replace />;
  }
  const current: AirWingView = view ?? "squadrons";
  const airWing = query.data;
  return (
    <ScreenFrame
      title="Air Wing"
      actions={
        <>
          {airWing != null && (
            <span className={styles.hint}>
              {airWing.squadron_count} squadrons · {airWing.aircraft_count}{" "}
              aircraft · {airWing.pilot_count} pilots
            </span>
          )}
          {airWing?.adjustments_enabled && (
            <Button asChild>
              <Link to={PATHS.airWingConfig}>Air wing adjustments</Link>
            </Button>
          )}
          <label className={styles.check}>
            <input
              type="checkbox"
              checked={enemy}
              onChange={(event) => setEnemy(event.target.checked)}
            />
            Show enemy
          </label>
        </>
      }
    >
      <Tabs
        className={styles.tabs}
        value={current}
        onValueChange={(next) =>
          navigate(PATHS.airWingView(next as AirWingView))
        }
      >
        <TabsList aria-label="Air wing views">
          {AIR_WING_VIEWS.map((id) => (
            <TabsTrigger key={id} value={id}>
              {LABELS[id]}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value={current}>
          <QueryBody query={query} name="air wing">
            {(data) => {
              if (current === "aircraft") {
                return <AircraftView airWing={data} />;
              }
              if (current === "pilots") {
                return (
                  <div className={styles.view}>
                    <PilotsTable
                      caption="Pilots"
                      squadrons={data.bases.flatMap((b) => b.squadrons)}
                      showSquadron
                      emptyText="No pilot."
                    />
                  </div>
                );
              }
              return <SquadronsView airWing={data} />;
            }}
          </QueryBody>
        </TabsContent>
      </Tabs>
    </ScreenFrame>
  );
}

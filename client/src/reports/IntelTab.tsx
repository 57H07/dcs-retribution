// Intel tab: aircraft and ground units of a coalition by base and type, as the
// "Air forces" and "Ground forces" tabs of the Qt intel window. Its "Economy"
// tab is the Finances tab with "Enemy info" on.
import {
  BaseForcesJs,
  ForcesJs,
  UnitCountJs,
  useGetIntelReportQuery,
} from "../api/liberationApi";
import { Table, TableColumn } from "../ui";
import styles from "./Reports.module.css";
import { EnemySwitch, ReportBody, StatCard } from "./common";
import { useState } from "react";

const COLUMNS: TableColumn<UnitCountJs>[] = [
  {
    key: "name",
    header: "Type",
    cell: (u) => u.name,
    sortValue: (u) => u.name,
  },
  {
    key: "count",
    header: "Count",
    cell: (u) => u.count,
    align: "end",
    mono: true,
    sortValue: (u) => u.count,
  },
];

function BaseTable({ base }: { base: BaseForcesJs }) {
  return (
    <Table
      className={styles.baseTable}
      caption={`${base.name} (${base.total})`}
      columns={COLUMNS}
      rows={base.units}
      rowKey={(u) => u.name}
    />
  );
}

function Forces({
  title,
  forces,
  empty,
}: {
  title: string;
  forces: ForcesJs;
  empty: string;
}) {
  return (
    <section className={styles.section} aria-label={title}>
      <h2 className={styles.sectionTitle}>
        {title} <span className={styles.count}>{forces.total}</span>
      </h2>
      {forces.bases.length === 0 ? (
        <p className={styles.state}>{empty}</p>
      ) : (
        <div className={styles.bases}>
          {forces.bases.map((base) => (
            <BaseTable key={base.id} base={base} />
          ))}
        </div>
      )}
    </section>
  );
}

export function IntelTab() {
  const query = useGetIntelReportQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  const [enemy, setEnemy] = useState(false);
  return (
    <>
      <EnemySwitch enemy={enemy} onChange={setEnemy} />
      <ReportBody query={query} name="intel report">
        {(intel) => {
          const coalition = enemy ? intel.enemy : intel.friendly;
          const tone = enemy ? "enemy" : "friendly";
          return (
            <>
              <div className={styles.cards}>
                <StatCard
                  title="Aircraft"
                  value={coalition.aircraft.total}
                  detail={`at ${coalition.aircraft.bases.length} bases`}
                  tone={tone}
                />
                <StatCard
                  title="Ground units"
                  value={coalition.ground.total}
                  detail={`at ${coalition.ground.bases.length} bases`}
                  tone={tone}
                />
              </div>
              <Forces
                title="Air forces"
                forces={coalition.aircraft}
                empty="No aircraft."
              />
              <Forces
                title="Ground forces"
                forces={coalition.ground}
                empty="No ground units."
              />
            </>
          );
        }}
      </ReportBody>
    </>
  );
}

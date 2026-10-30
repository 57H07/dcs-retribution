// Finances tab: income by base and by building, multiplier and balance, as the
// Qt finances window (and, with "Enemy info", the intel window's Economy tab).
import {
  BaseIncomeJs,
  BuildingIncomeJs,
  CoalitionFinancesJs,
  useGetFinancesReportQuery,
} from "../api/liberationApi";
import { Table, TableColumn } from "../ui";
import styles from "./Reports.module.css";
import { EnemySwitch, formatMillions, ReportBody, StatCard } from "./common";
import { useState } from "react";

const BASE_COLUMNS: TableColumn<BaseIncomeJs>[] = [
  {
    key: "name",
    header: "Base",
    cell: (b) => b.name,
    sortValue: (b) => b.name,
  },
  {
    key: "income",
    header: "Income",
    cell: (b) => formatMillions(b.income),
    align: "end",
    mono: true,
    sortValue: (b) => b.income,
  },
];

type BuildingRow = BuildingIncomeJs & { key: string };

const BUILDING_COLUMNS: TableColumn<BuildingRow>[] = [
  {
    key: "name",
    header: "Building",
    cell: (b) => b.name,
    sortValue: (b) => b.name,
  },
  {
    key: "category",
    header: "Category",
    cell: (b) => b.category.toUpperCase(),
    sortValue: (b) => b.category,
  },
  {
    key: "count",
    header: "Buildings",
    cell: (b) => `${b.count} × ${formatMillions(b.income_per_building)}`,
    mono: true,
    sortValue: (b) => b.count,
  },
  {
    key: "income",
    header: "Income",
    cell: (b) => formatMillions(b.income),
    align: "end",
    mono: true,
    sortValue: (b) => b.income,
  },
];

function Finances({
  finances,
  enemy,
}: {
  finances: CoalitionFinancesJs;
  enemy: boolean;
}) {
  const buildings: BuildingRow[] = finances.buildings.map((b, index) => ({
    ...b,
    key: `${index}-${b.name}`,
  }));
  return (
    <>
      <div className={styles.cards}>
        <StatCard
          title="Balance"
          value={formatMillions(finances.budget)}
          tone={enemy ? "enemy" : "friendly"}
        />
        <StatCard
          title="Income per turn"
          value={formatMillions(finances.total)}
          detail={`Income multiplier: ${finances.multiplier.toFixed(1)}`}
        />
        <StatCard
          title="From bases"
          value={formatMillions(finances.from_bases)}
          detail={`${formatMillions(finances.from_buildings)} from buildings`}
        />
      </div>
      <section className={styles.section} aria-label="Income by base">
        <h2 className={styles.sectionTitle}>Bases</h2>
        <Table
          caption="Income by base"
          hideCaption
          columns={BASE_COLUMNS}
          rows={finances.bases}
          rowKey={(b) => b.id}
          emptyText="No base produces income."
        />
      </section>
      <section className={styles.section} aria-label="Income by building">
        <h2 className={styles.sectionTitle}>Buildings</h2>
        <Table
          caption="Income by building"
          hideCaption
          columns={BUILDING_COLUMNS}
          rows={buildings}
          rowKey={(b) => b.key}
          emptyText="No building produces income."
        />
      </section>
    </>
  );
}

export function FinancesTab() {
  const query = useGetFinancesReportQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  const [enemy, setEnemy] = useState(false);
  return (
    <>
      <EnemySwitch enemy={enemy} onChange={setEnemy} />
      <ReportBody query={query} name="finances">
        {(finances) => (
          <Finances
            finances={enemy ? finances.enemy : finances.friendly}
            enemy={enemy}
          />
        )}
      </ReportBody>
    </>
  );
}

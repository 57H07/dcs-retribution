// Pilot career (WEB-08.2): the Qt CareerDialog (PER-03.4) for every player
// pilot, from GET /careers. The engine writes every figure and date.
import {
  AwardJs,
  CareerJs,
  LogbookEntryJs,
  useListCareersQuery,
} from "../api/liberationApi";
import { Table, TableColumn } from "../ui";
import { QueryBody, ScreenFrame } from "./ScreenFrame";
import styles from "./Secondary.module.css";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

const AWARD_COLUMNS: TableColumn<AwardJs>[] = [
  { key: "name", header: "Award", cell: (a) => a.name },
  { key: "kind", header: "Type", cell: (a) => a.kind },
  { key: "date", header: "Date", cell: (a) => a.date, mono: true },
  {
    key: "turn",
    header: "Turn",
    cell: (a) => a.turn,
    align: "end",
    mono: true,
  },
  { key: "description", header: "Details", cell: (a) => a.description },
];

const count = (value: number) => (value ? value : "");

const HISTORY_COLUMNS: TableColumn<LogbookEntryJs>[] = [
  {
    key: "turn",
    header: "Turn",
    cell: (e) => e.turn,
    align: "end",
    mono: true,
    sortValue: (e) => e.turn,
  },
  { key: "date", header: "Date", cell: (e) => e.date, mono: true },
  { key: "squadron", header: "Squadron", cell: (e) => e.squadron },
  { key: "aircraft", header: "Aircraft", cell: (e) => e.aircraft },
  { key: "task", header: "Task", cell: (e) => e.task },
  { key: "combat", header: "Combat", cell: (e) => (e.combat ? "Yes" : "") },
  {
    key: "time",
    header: "Flight time",
    cell: (e) => e.flight_time,
    align: "end",
    mono: true,
  },
  {
    key: "air",
    header: "Air",
    cell: (e) => count(e.air_kills),
    align: "end",
    mono: true,
  },
  {
    key: "ground",
    header: "Ground",
    cell: (e) => count(e.ground_kills),
    align: "end",
    mono: true,
  },
  {
    key: "naval",
    header: "Naval",
    cell: (e) => count(e.naval_kills),
    align: "end",
    mono: true,
  },
  {
    key: "rescues",
    header: "Rescues",
    cell: (e) => count(e.rescues),
    align: "end",
    mono: true,
  },
  { key: "loss", header: "Lost", cell: (e) => e.loss },
];

function Career({ career }: { career: CareerJs }) {
  return (
    <>
      <section className={styles.section} aria-label="Pilot">
        <h2 className={styles.sectionTitle}>
          {career.rank ?? "No rank yet"} {career.pilot}
        </h2>
        <span className={styles.cardDetail}>
          {career.squadron} — {career.status}
        </span>
      </section>
      <section className={styles.section} aria-label="Logbook">
        <h2 className={styles.sectionTitle}>Logbook</h2>
        <dl className={styles.totals}>
          {career.totals.map((total) => (
            <div key={total.label} className={styles.total}>
              <dt>{total.label}</dt>
              <dd>{total.value}</dd>
            </div>
          ))}
        </dl>
      </section>
      <section className={styles.section} aria-label="Ranks and decorations">
        <h2 className={styles.sectionTitle}>Ranks and decorations</h2>
        <Table
          caption="Ranks and decorations"
          hideCaption
          columns={AWARD_COLUMNS}
          rows={career.awards}
          rowKey={(a) => `${a.turn}-${a.name}`}
          emptyText="Ranks and decorations are awarded after each mission."
        />
      </section>
      <section className={styles.section} aria-label="Mission history">
        <h2 className={styles.sectionTitle}>
          Mission history{" "}
          <span className={styles.count}>{career.history.length}</span>
        </h2>
        <Table
          caption="Mission history"
          hideCaption
          columns={HISTORY_COLUMNS}
          rows={career.history}
          rowKey={(e) => `${e.turn}-${e.date}-${e.aircraft}`}
          emptyText="No mission flown yet."
        />
      </section>
    </>
  );
}

function Careers({ careers }: { careers: CareerJs[] }) {
  // The air wing screen links a pilot's career: /career?pilot=<id>.
  const [params] = useSearchParams();
  const [index, setIndex] = useState(() =>
    Math.max(
      careers.findIndex((career) => career.pilot_id === params.get("pilot")),
      0,
    ),
  );
  if (careers.length === 0) {
    return (
      <p className={styles.state}>
        No player pilot: assign yourself to a flight to start a career.
      </p>
    );
  }
  const current = careers[Math.min(index, careers.length - 1)];
  return (
    <>
      {careers.length > 1 && (
        <label className={styles.cardDetail}>
          Pilot{" "}
          <select
            className={styles.select}
            value={index}
            onChange={(event) => setIndex(Number(event.target.value))}
          >
            {careers.map((career, i) => (
              <option key={`${career.squadron}-${career.pilot}`} value={i}>
                {career.pilot} ({career.squadron})
              </option>
            ))}
          </select>
        </label>
      )}
      <Career career={current} />
    </>
  );
}

export function CareerScreen() {
  const query = useListCareersQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  return (
    <ScreenFrame title="Pilot career">
      <QueryBody query={query} name="careers">
        {(careers) => <Careers careers={careers} />}
      </QueryBody>
    </ScreenFrame>
  );
}

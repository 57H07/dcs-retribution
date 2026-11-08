// War diary (#193): one entry per accepted mission result, newest first, from
// GET /war-diary. The engine writes every entry and its summary; "Export…"
// saves the whole diary as one HTML page through the native save dialog.
import { commandErrorMessage } from "../api/commands";
import {
  WarDiary,
  WarDiaryEntry,
  useExportWarDiaryMutation,
  useGetWarDiaryQuery,
} from "../api/liberationApi";
import { formatIncome, formatMoney } from "../command/format";
import { PATHS } from "../shell/paths";
import { Button, useToast } from "../ui";
import { QueryBody, ScreenFrame } from "./ScreenFrame";
import styles from "./Secondary.module.css";
import diary from "./WarDiaryScreen.module.css";
import { ReactNode, useState } from "react";
import { Link } from "react-router-dom";

function Details({ title, items }: { title: string; items: ReactNode[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className={diary.group}>
      <h4 className={diary.groupTitle}>{title}</h4>
      <ul className={diary.items}>
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function CareerLink({ id, name }: { id?: string | null; name: string }) {
  return id ? (
    <Link
      className={styles.link}
      to={`${PATHS.career}?pilot=${id}`}
      aria-label={`Career of ${name}`}
    >
      {name}
    </Link>
  ) : (
    <>{name}</>
  );
}

function EntryDetails({ entry }: { entry: WarDiaryEntry }) {
  return (
    <div className={diary.details}>
      <Details
        title="Bases"
        items={entry.bases.map((b) => (
          <>
            <Link className={styles.link} to={PATHS.base(b.id)}>
              {b.name}
            </Link>{" "}
            <span data-tone={b.taken ? "good" : "bad"}>
              {b.taken ? "taken" : "lost"}
            </span>
          </>
        ))}
      />
      <Details
        title="Front lines"
        items={entry.fronts.map(
          (f) => `${f.name}: ${f.moved_km > 0 ? "+" : ""}${f.moved_km} km`,
        )}
      />
      <Details
        title="Packages"
        items={entry.packages.map((p) => (
          <>
            {p.task} · <b>{p.target}</b>
            <span className={styles.cardDetail}>
              {" "}
              ({p.flights.join(", ")})
            </span>{" "}
            <span data-tone={p.tone}>{p.result}</span>
            <span className={styles.cardDetail}>
              {" "}
              · {p.lost} / {p.aircraft} lost
            </span>
          </>
        ))}
      />
      <Details
        title="Our losses"
        items={entry.friendly_losses.map((x) => `${x.name} × ${x.count}`)}
      />
      <Details
        title="Enemy losses"
        items={entry.enemy_losses.map((x) => `${x.name} × ${x.count}`)}
      />
      <Details
        title="Pilots"
        items={entry.pilots.map((p) => (
          <>
            <CareerLink id={p.pilot_id} name={p.name} />
            <span className={styles.cardDetail}>
              {" "}
              ({p.squadron}, {p.aircraft})
            </span>{" "}
            · {p.fate}
          </>
        ))}
      />
      <Details
        title="Awards"
        items={entry.awards.map((a) => (
          <>
            {a.pilot}
            {" · "}
            {a.kind === "Rank" ? `Promoted to ${a.name}` : `Awarded ${a.name}`}
            {a.reason ? (
              <span className={styles.cardDetail}> · {a.reason}</span>
            ) : null}
          </>
        ))}
      />
      {entry.budget_next_turn != null && (
        <p className={styles.cardDetail}>
          Budget next turn {formatMoney(entry.budget_next_turn)}
          {entry.income_next_turn != null &&
            ` · ${formatIncome(entry.income_next_turn)} income`}
        </p>
      )}
    </div>
  );
}

function Entry({ entry }: { entry: WarDiaryEntry }) {
  const [open, setOpen] = useState(false);
  const titleId = `diary-turn-${entry.turn}`;
  return (
    <article className={diary.entry} aria-labelledby={titleId}>
      <header className={diary.entryHeader}>
        <h3 id={titleId} className={styles.cardTitle}>
          Turn {entry.turn} · {entry.date}
        </h3>
        <span className={diary.verdict} data-tone={entry.verdict_tone}>
          {entry.verdict}
        </span>
        <Button aria-expanded={open} onClick={() => setOpen((value) => !value)}>
          Details
        </Button>
      </header>
      <p className={styles.prose}>{entry.summary}</p>
      <span className={styles.cardDetail}>
        {entry.weather} · air kills {entry.air_kills_friendly} :{" "}
        {entry.air_kills_enemy} · ground {entry.ground_kills_friendly} :{" "}
        {entry.ground_kills_enemy}
      </span>
      {open && <EntryDetails entry={entry} />}
    </article>
  );
}

function Diary({ diary: data }: { diary: WarDiary }) {
  return (
    <>
      {data.since_turn != null && (
        <p className={styles.help}>
          This campaign was started before the war diary existed: it begins at
          turn {data.since_turn}.
        </p>
      )}
      {data.entries.length === 0 ? (
        <p className={styles.state}>
          No turn recorded yet: an entry is written each time you accept a
          mission result.
        </p>
      ) : (
        <div className={styles.list}>
          {data.entries.map((entry) => (
            <Entry key={entry.turn} entry={entry} />
          ))}
        </div>
      )}
    </>
  );
}

export function WarDiaryScreen() {
  const query = useGetWarDiaryQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  const [exportDiary, exporting] = useExportWarDiaryMutation();
  const toast = useToast();

  const onExport = async () => {
    const result = await exportDiary();
    if ("error" in result) {
      toast({
        title: "War diary not exported",
        description: commandErrorMessage(
          result.error as Parameters<typeof commandErrorMessage>[0],
        ),
        tone: "danger",
      });
      return;
    }
    if (result.data.outcome === "saved") {
      toast({
        title: "War diary exported",
        description: result.data.path ?? "",
        tone: "success",
      });
    }
  };

  return (
    <ScreenFrame
      title="War diary"
      actions={
        query.data != null && (
          <Button onClick={onExport} disabled={exporting.isLoading}>
            Export…
          </Button>
        )
      }
    >
      <QueryBody query={query} name="war diary">
        {(data) => <Diary diary={data} />}
      </QueryBody>
    </ScreenFrame>
  );
}

// After-action report (WEB-05.2), after Qt's QDebriefingWindow and
// mockups/Debrief.dc.html. The engine builds the whole report
// (game/debriefingreport.py): this screen shows GET /game/mission/result/report
// and sends "Accept results". Each player pilot gets a "Your sortie" card
// at the top (#192). Before acceptance the report covers what the
// mission decided; accepting applies the results exactly as the Qt path does,
// and the report then adds what applying them decided (prisoners, pilots still
// down, budget, the engine's log). "Continue" goes back to the command view.
import { commandErrorMessage } from "../api/commands";
import {
  AfterActionReport,
  LossLine,
  SortieAward,
  SortieCard,
  useAcceptMissionResultMutation,
  useGetMissionReportQuery,
  useLoadMissionResultFileMutation,
} from "../api/liberationApi";
import { formatIncome, formatMoney, formatTurn } from "../command/format";
import { PATHS } from "../shell/paths";
import { Button, Table, TableColumn, TaskTag, useToast } from "../ui";
import styles from "./DebriefScreen.module.css";
import { Link, useNavigate } from "react-router-dom";

function Stat({
  label,
  value,
  detail,
}: {
  label: string;
  value: React.ReactNode;
  detail: React.ReactNode;
}) {
  return (
    <div className={styles.stat}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
      <span className={styles.statDetail}>{detail}</span>
    </div>
  );
}

function Ratio({ left, right }: { left: number; right: string | number }) {
  return (
    <>
      {left} <span className={styles.statSecondary}>{right}</span>
    </>
  );
}

const AFTER_ACCEPT = "Known once the results are accepted";

/** The four headline figures of the report. */
export function Headline({ report }: { report: AfterActionReport }) {
  const rescued = report.pilots_rescued.length;
  const captured = report.pilots_captured;
  const bounty =
    report.rescue_bounty > 0
      ? ` · ${formatMoney(report.rescue_bounty)} bounty`
      : "";
  return (
    <div className={styles.stats}>
      <Stat
        label="Air kills"
        value={
          <Ratio
            left={report.air_kills_friendly}
            right={`: ${report.air_kills_enemy}`}
          />
        }
        detail="friendly : enemy"
      />
      <Stat
        label="Ground units destroyed"
        value={
          <Ratio
            left={report.ground_kills_friendly}
            right={`: ${report.ground_kills_enemy}`}
          />
        }
        detail={
          report.bases_captured || report.bases_lost
            ? `${report.bases_captured} bases captured · ${report.bases_lost} lost`
            : "friendly : enemy"
        }
      />
      <Stat
        label="Pilots"
        value={
          <Ratio
            left={rescued}
            right={
              captured == null ? "rescued" : `rescued · ${captured.length} POW`
            }
          />
        }
        detail={
          report.pilots_still_down == null
            ? AFTER_ACCEPT
            : `${report.pilots_still_down} still down${bounty}`
        }
      />
      <Stat
        label="Budget next turn"
        value={
          report.budget_next_turn == null
            ? "—"
            : formatMoney(report.budget_next_turn)
        }
        detail={
          report.income_next_turn == null
            ? AFTER_ACCEPT
            : `${formatIncome(report.income_next_turn)} income`
        }
      />
    </div>
  );
}

function Award({ award }: { award: SortieAward }) {
  const what =
    award.kind === "Rank"
      ? `Promoted to ${award.name}`
      : `Awarded ${award.name}`;
  return (
    <li className={styles.award}>
      {award.abbreviation ? (
        <span className={styles.badge}>{award.abbreviation}</span>
      ) : null}
      <span className={styles.packageTarget}>
        <b>{what}</b>
        {award.reason ? (
          <span className={styles.muted}>{award.reason}</span>
        ) : null}
      </span>
    </li>
  );
}

/** How the mission went for one player pilot (#192). */
function SortieCardView({ card }: { card: SortieCard }) {
  const titleId = `sortie-${card.pilot_id}`;
  const logged =
    card.sorties_logged == null
      ? `${card.flight_time} planned`
      : `${card.sorties_logged} ${
          card.sorties_logged === 1 ? "sortie" : "sorties"
        } logged · ${card.flight_time}`;
  return (
    <article className={styles.sortie} aria-labelledby={titleId}>
      <header className={styles.sortieHeader}>
        <h3 id={titleId} className={styles.sortieTitle}>
          {card.pilot}
        </h3>
        <Link
          className={styles.careerLink}
          to={`${PATHS.career}?pilot=${card.pilot_id}`}
          aria-label={`Career of ${card.pilot}`}
        >
          Career
        </Link>
      </header>
      <span className={styles.muted}>
        {[card.flight, card.aircraft, card.squadron]
          .filter(Boolean)
          .join(" · ")}
      </span>
      {card.target ? (
        <div className={styles.sortieRow}>
          {card.task ? <TaskTag task={card.task} /> : null}
          <span>{card.target}</span>
          <span className={styles.result} data-tone={card.package_tone}>
            {card.package_result}
          </span>
        </div>
      ) : null}
      <div className={styles.sortieRow}>
        <span className={styles.result} data-tone={card.fate_tone}>
          {card.fate}
        </span>
        <span className={styles.mono}>
          {card.air_kills} air · {card.ground_kills} ground · {card.naval_kills}{" "}
          naval
        </span>
      </div>
      <span className={styles.muted}>
        {logged}
        {card.rescues ? ` · ${card.rescues} pilots rescued` : ""}
      </span>
      {card.awards == null ? (
        <p className={styles.muted}>
          Awards are decided when you accept the results.
        </p>
      ) : card.awards.length > 0 ? (
        <ul className={styles.awards}>
          {card.awards.map((award) => (
            <Award key={`${award.kind}-${award.name}`} award={award} />
          ))}
        </ul>
      ) : null}
    </article>
  );
}

function YourSortie({ report }: { report: AfterActionReport }) {
  if (report.your_sorties.length === 0) {
    return null;
  }
  return (
    <section className={styles.panel} aria-labelledby="debrief-your-sortie">
      <h2 id="debrief-your-sortie" className={styles.panelTitle}>
        Your sortie
      </h2>
      <div className={styles.sorties}>
        {report.your_sorties.map((card) => (
          <SortieCardView key={card.pilot_id} card={card} />
        ))}
      </div>
    </section>
  );
}

function Packages({ report }: { report: AfterActionReport }) {
  return (
    <section className={styles.panel} aria-labelledby="debrief-packages">
      <h2 id="debrief-packages" className={styles.panelTitle}>
        Packages
      </h2>
      {report.packages.length === 0 ? (
        <p className={styles.none}>No friendly package flew this mission.</p>
      ) : (
        <ul className={styles.packages}>
          {report.packages.map((p, index) => (
            <li key={index} className={styles.package}>
              {p.task ? <TaskTag task={p.task} /> : <span />}
              <span className={styles.packageTarget}>
                <b>{p.target}</b>
                <span className={styles.muted}>{p.flights.join(", ")}</span>
              </span>
              <span
                className={styles.mono}
                data-tone={p.lost > 0 ? "mixed" : "neutral"}
              >
                {p.lost} / {p.aircraft} lost
              </span>
              <span className={styles.result} data-tone={p.tone}>
                {p.result}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function EventLog({ report }: { report: AfterActionReport }) {
  return (
    <section className={styles.panel} aria-labelledby="debrief-log">
      <h2 id="debrief-log" className={styles.panelTitle}>
        Event log
      </h2>
      {report.events.length === 0 ? (
        <p className={styles.none}>Nothing to report.</p>
      ) : (
        <ol className={styles.log}>
          {report.events.map((event, index) => (
            <li key={index} className={styles.logLine}>
              <span className={styles.time}>{event.time ?? "mission"}</span>
              <span data-tone={event.tone}>{event.text}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

/** The campaign objectives (#194) met or missed at the end of the turn. */
function Objectives({ report }: { report: AfterActionReport }) {
  const objectives = report.objectives ?? [];
  if (objectives.length === 0) {
    return null;
  }
  return (
    <section className={styles.panel} aria-labelledby="debrief-objectives">
      <h2 id="debrief-objectives" className={styles.panelTitle}>
        Objectives
      </h2>
      <ul className={styles.pilots}>
        {objectives.map((o) => (
          <li key={o.title} data-tone={o.met ? "good" : "bad"}>
            {o.met
              ? `Met: ${o.title}${o.granted ? ` · ${o.granted}` : ""}`
              : `Missed: ${o.title}`}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Losses({ caption, lines }: { caption: string; lines: LossLine[] }) {
  const columns: TableColumn<LossLine>[] = [
    { key: "name", header: "Unit", cell: (line) => line.name },
    {
      key: "count",
      header: "Lost",
      cell: (line) => line.count,
      align: "end",
      mono: true,
    },
  ];
  return (
    <div className={styles.panel}>
      {lines.length === 0 ? (
        <>
          <h2 className={styles.panelTitle}>{caption}</h2>
          <p className={styles.none}>No losses.</p>
        </>
      ) : (
        <Table
          caption={caption}
          columns={columns}
          rows={lines}
          rowKey={(line) => line.name}
        />
      )}
    </div>
  );
}

function Pilots({ report }: { report: AfterActionReport }) {
  const captured = report.pilots_captured ?? [];
  if (report.pilots_rescued.length === 0 && captured.length === 0) {
    return null;
  }
  return (
    <section className={styles.panel} aria-labelledby="debrief-pilots">
      <h2 id="debrief-pilots" className={styles.panelTitle}>
        Rescued and captured pilots
      </h2>
      <ul className={styles.pilots}>
        {report.pilots_rescued.map((p) => (
          <li key={`rescued-${p.name}`} data-tone="good">
            {p.name} · {p.squadron} ({p.aircraft}) · rescued
          </li>
        ))}
        {captured.map((p) => (
          <li key={`pow-${p.name}`} data-tone="bad">
            {p.name} · {p.squadron} ({p.aircraft}) · held at {p.held_at}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Damaged({ report }: { report: AfterActionReport }) {
  if (report.damaged_units.length === 0) {
    return null;
  }
  type Row = AfterActionReport["damaged_units"][number];
  const columns: TableColumn<Row>[] = [
    {
      key: "side",
      header: "Side",
      cell: (row) =>
        row.friendly ? report.player_country : report.enemy_country,
    },
    { key: "type", header: "Type", cell: (row) => row.unit_type },
    {
      key: "damage",
      header: "Damage",
      cell: (row) => `${row.damage_percent} %`,
      align: "end",
      mono: true,
    },
    {
      key: "unavailability",
      header: "Unavailability",
      cell: (row) => row.unavailability,
    },
  ];
  return (
    <div className={styles.panel}>
      <Table
        caption="Damaged units"
        columns={columns}
        rows={report.damaged_units}
        rowKey={(row) => `${row.friendly}-${row.unit_type}`}
      />
    </div>
  );
}

export function DebriefScreen() {
  const { data } = useGetMissionReportQuery();
  const [accept, accepting] = useAcceptMissionResultMutation();
  const [loadFile, loading] = useLoadMissionResultFileMutation();
  const navigate = useNavigate();
  const toast = useToast();
  const busy = accepting.isLoading || loading.isLoading;

  const refused = (title: string, error: unknown) =>
    toast({
      title,
      description: commandErrorMessage(
        error as Parameters<typeof commandErrorMessage>[0],
      ),
      tone: "danger",
    });

  const onAccept = async () => {
    const answer = await accept();
    if ("error" in answer) {
      refused("Results not accepted", answer.error);
      return;
    }
    const state = answer.data.campaign_state;
    toast(
      state === "continue"
        ? {
            title: "Results accepted",
            description: `Turn ${answer.data.turn} begins.`,
            tone: "success",
          }
        : {
            title: state === "win" ? "Victory!" : "Defeat!",
            description: `You have ${state === "win" ? "won" : "lost"} the campaign.`,
            tone: state === "win" ? "success" : "danger",
          },
    );
  };

  const onReload = async () => {
    const answer = await loadFile();
    if ("error" in answer) {
      refused("state.json not loaded", answer.error);
    }
  };

  if (data == null) {
    return (
      <section className={styles.screen} aria-label="After-action report">
        <p className={styles.empty}>Loading the report…</p>
      </section>
    );
  }

  const report = data.report;
  if (data.status === "none" || report == null) {
    return (
      <section className={styles.screen} aria-label="After-action report">
        <header className={styles.header}>
          <div className={styles.heading}>
            <span className={styles.eyebrow}>After-action report</span>
            <h1 className={styles.title}>No debriefing yet</h1>
          </div>
          <div className={styles.spacer} />
          <Button asChild>
            <Link to={PATHS.command}>Back to the map</Link>
          </Button>
        </header>
        <p className={styles.empty}>
          No mission result has been received since Retribution started.
        </p>
      </section>
    );
  }

  const pending = data.status === "pending";

  return (
    <section className={styles.screen} aria-label="After-action report">
      <header className={styles.header}>
        <div className={styles.heading}>
          <span className={styles.eyebrow}>
            After-action report · Turn {formatTurn(report.turn)} · {report.date}
          </span>
          <h1 className={styles.title} data-tone={report.verdict_tone}>
            {report.verdict}
          </h1>
          <span className={styles.summary}>{report.summary}</span>
        </div>
        <div className={styles.spacer} />
        {pending ? (
          <div className={styles.actions}>
            <Button asChild>
              <Link to={PATHS.waiting}>Mission status</Link>
            </Button>
            <Button onClick={onReload} disabled={busy}>
              Reload state.json
            </Button>
            <Button
              variant="primary"
              size="lg"
              onClick={onAccept}
              disabled={busy || !data.can_accept}
            >
              {accepting.isLoading ? "Processing results…" : "Accept results"}
            </Button>
          </div>
        ) : (
          <Button
            variant="primary"
            size="lg"
            onClick={() => navigate(PATHS.command)}
          >
            Continue
          </Button>
        )}
      </header>

      <div className={styles.body}>
        {pending && !data.can_accept && (
          <p className={styles.note} role="status">
            The mission is still being played: its results can be accepted once
            it is over.
          </p>
        )}
        <YourSortie report={report} />
        <Headline report={report} />
        <Objectives report={report} />
        <div className={styles.columns}>
          <div className={styles.main}>
            <Packages report={report} />
          </div>
          <div className={styles.side}>
            <EventLog report={report} />
          </div>
        </div>
        <Pilots report={report} />
        <div className={styles.losses}>
          <Losses
            caption={`${report.player_country} lost units`}
            lines={report.friendly_losses}
          />
          <Losses
            caption={`${report.enemy_country} lost units`}
            lines={report.enemy_losses}
          />
        </div>
        <Damaged report={report} />
      </div>
    </section>
  );
}

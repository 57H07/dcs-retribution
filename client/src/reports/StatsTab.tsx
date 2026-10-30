// Stats tab: aircraft and combat vehicles of both coalitions at each turn, as
// the two charts of the Qt stats window (inline SVG, no chart library).
import { TurnStatsJs, useGetStatsReportQuery } from "../api/liberationApi";
import { Table, TableColumn } from "../ui";
import styles from "./Reports.module.css";
import { ReportBody, StatCard } from "./common";

const WIDTH = 640;
const HEIGHT = 220;
const PAD = { top: 12, right: 16, bottom: 32, left: 40 };

type Series = { name: string; tone: "friendly" | "enemy"; values: number[] };

/** Round the axis top up to a multiple of 10, leaving headroom as Qt did. */
function axisMax(values: number[]): number {
  return Math.ceil((Math.max(0, ...values) + 10) / 10) * 10;
}

export function LineChart({
  title,
  series,
}: {
  title: string;
  series: Series[];
}) {
  const turns = Math.max(...series.map((s) => s.values.length));
  const top = axisMax(series.flatMap((s) => s.values));
  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const x = (turn: number) =>
    PAD.left + (turns > 1 ? (turn / (turns - 1)) * plotWidth : plotWidth / 2);
  const y = (value: number) =>
    PAD.top + plotHeight - (value / top) * plotHeight;
  const yTicks = [0, top / 2, top];
  const xStep = Math.max(1, Math.ceil(turns / 10));
  const xTicks = Array.from({ length: turns }, (_, t) => t).filter(
    (t) => t % xStep === 0,
  );

  return (
    <figure className={styles.chart}>
      <figcaption className={styles.sectionTitle}>{title}</figcaption>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`${title}: ${series
          .map((s) => `${s.name} ${s.values[s.values.length - 1] ?? 0}`)
          .join(", ")} at the last turn`}
      >
        {yTicks.map((tick) => (
          <g key={tick}>
            <line
              className={styles.grid}
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={y(tick)}
              y2={y(tick)}
            />
            <text
              className={styles.axisLabel}
              x={PAD.left - 6}
              y={y(tick)}
              textAnchor="end"
              dominantBaseline="middle"
            >
              {tick}
            </text>
          </g>
        ))}
        {xTicks.map((turn) => (
          <text
            key={turn}
            className={styles.axisLabel}
            x={x(turn)}
            y={HEIGHT - PAD.bottom + 16}
            textAnchor="middle"
          >
            {turn}
          </text>
        ))}
        <text
          className={styles.axisLabel}
          x={PAD.left + plotWidth / 2}
          y={HEIGHT - 2}
          textAnchor="middle"
        >
          Turn
        </text>
        {series.map((s) => (
          <g key={s.name} className={styles.series} data-tone={s.tone}>
            <polyline
              points={s.values.map((v, t) => `${x(t)},${y(v)}`).join(" ")}
            />
            {s.values.length === 1 && (
              <circle cx={x(0)} cy={y(s.values[0])} r={3} />
            )}
          </g>
        ))}
      </svg>
      <div className={styles.legend}>
        {series.map((s) => (
          <span key={s.name} className={styles.legendItem} data-tone={s.tone}>
            {s.name}
          </span>
        ))}
      </div>
    </figure>
  );
}

const COLUMNS: TableColumn<TurnStatsJs>[] = [
  { key: "turn", header: "Turn", cell: (t) => t.turn, mono: true },
  ...(
    [
      ["friendly_aircraft", "Allied aircraft"],
      ["enemy_aircraft", "Enemy aircraft"],
      ["friendly_vehicles", "Allied vehicles"],
      ["enemy_vehicles", "Enemy vehicles"],
    ] as const
  ).map(([key, header]) => ({
    key,
    header,
    cell: (t: TurnStatsJs) => t[key],
    align: "end" as const,
    mono: true,
  })),
];

function Stats({ turns }: { turns: TurnStatsJs[] }) {
  if (turns.length === 0) {
    return <p className={styles.state}>No turn recorded yet.</p>;
  }
  const last = turns[turns.length - 1];
  return (
    <>
      <div className={styles.cards}>
        <StatCard
          title="Aircraft"
          value={
            <>
              {last.friendly_aircraft}
              <span className={styles.versus}> : {last.enemy_aircraft}</span>
            </>
          }
          detail="allied : enemy"
          tone="friendly"
        />
        <StatCard
          title="Combat vehicles"
          value={
            <>
              {last.friendly_vehicles}
              <span className={styles.versus}> : {last.enemy_vehicles}</span>
            </>
          }
          detail="allied : enemy"
          tone="friendly"
        />
      </div>
      <div className={styles.charts}>
        <LineChart
          title="Aircraft forces over time"
          series={[
            {
              name: "Allied aircraft count",
              tone: "friendly",
              values: turns.map((t) => t.friendly_aircraft),
            },
            {
              name: "Enemy aircraft count",
              tone: "enemy",
              values: turns.map((t) => t.enemy_aircraft),
            },
          ]}
        />
        <LineChart
          title="Combat vehicles over time"
          series={[
            {
              name: "Allied vehicle count",
              tone: "friendly",
              values: turns.map((t) => t.friendly_vehicles),
            },
            {
              name: "Enemy vehicle count",
              tone: "enemy",
              values: turns.map((t) => t.enemy_vehicles),
            },
          ]}
        />
      </div>
      <section className={styles.section} aria-label="Forces per turn">
        <h2 className={styles.sectionTitle}>Per turn</h2>
        <Table
          caption="Forces per turn"
          hideCaption
          columns={COLUMNS}
          rows={turns}
          rowKey={(t) => String(t.turn)}
        />
      </section>
    </>
  );
}

export function StatsTab() {
  const query = useGetStatsReportQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  return (
    <ReportBody query={query} name="stats">
      {(stats) => <Stats turns={stats.turns} />}
    </ReportBody>
  );
}

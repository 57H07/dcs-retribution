// Contextual inspector of the command view (WEB-01.3, W12): a floating card
// over the top-right of the map for the base or ground object clicked on the
// map. Its actions open the base screen (/bases/:id), which is still the Qt
// base menu until WEB-02 migrates it.
import { commandErrorMessage } from "../../api/commands";
import {
  ControlPointSummary,
  Count,
  Runway,
  TgoSummary,
  useGetControlPointSummaryQuery,
  useGetTgoSummaryQuery,
  useOpenTgoInfoDialogMutation,
} from "../../api/liberationApi";
import { MapSelection } from "../../maplayers/mapSelection";
import { PATHS } from "../../shell/paths";
import { Button, Gauge, GaugeTone, IconButton, MilSymbol } from "../../ui";
import styles from "./MapInspector.module.css";
import { SerializedError } from "@reduxjs/toolkit";
import { FetchBaseQueryError } from "@reduxjs/toolkit/query";
import { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

export interface MapInspectorProps {
  selection: MapSelection | null;
  onClose: () => void;
}

export function MapInspector({ selection, onClose }: MapInspectorProps) {
  if (selection === null) {
    return null;
  }
  return selection.kind === "controlPoint" ? (
    <ControlPointInspector id={selection.id} onClose={onClose} />
  ) : (
    <TgoInspector id={selection.id} onClose={onClose} />
  );
}

/** "12 nm from front", or nothing without a front line. */
export function distanceText(nm: number | null | undefined): string | null {
  if (nm === null || nm === undefined) {
    return null;
  }
  return `${Math.round(nm)} nm from front`;
}

function subtitle(...parts: (string | null)[]): string {
  return parts.filter((part) => part !== null).join(" · ");
}

interface CardProps {
  title: string;
  subtitle?: string;
  symbol?: ReactNode;
  onClose: () => void;
  children: ReactNode;
}

function Card({ title, subtitle, symbol, onClose, children }: CardProps) {
  return (
    <section className={styles.card} aria-label={`Inspector: ${title}`}>
      <header className={styles.header}>
        {symbol}
        <div className={styles.titles}>
          <span className={styles.title}>{title}</span>
          {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
        </div>
        <IconButton
          aria-label="Close inspector"
          className={styles.close}
          onClick={onClose}
        >
          ✕
        </IconButton>
      </header>
      <div className={styles.body}>{children}</div>
    </section>
  );
}

function Pending(props: {
  isLoading: boolean;
  error: FetchBaseQueryError | SerializedError | undefined;
  what: string;
  onClose: () => void;
}) {
  if (props.isLoading) {
    return (
      <Card title="Loading…" onClose={props.onClose}>
        <p className={styles.note} role="status">
          Loading the {props.what}…
        </p>
      </Card>
    );
  }
  return (
    <Card title={`No ${props.what}`} onClose={props.onClose}>
      <p className={styles.note} role="alert">
        Could not load this {props.what}.{" "}
        {props.error ? commandErrorMessage(props.error) : ""}
      </p>
    </Card>
  );
}

function CountGauge(props: { label: string; count: Count; tone: GaugeTone }) {
  return (
    <Gauge
      label={props.label}
      value={props.count.current}
      max={props.count.total}
      tone={props.tone}
      valueText={`${props.count.current}/${props.count.total}`}
    />
  );
}

const RUNWAY_GAUGE: Record<
  Runway["state"],
  { value: number; tone: GaugeTone; text: (runway: Runway) => string }
> = {
  operational: { value: 100, tone: "success", text: () => "OK" },
  damaged: { value: 0, tone: "hostile", text: () => "Damaged" },
  repairing: {
    value: 50,
    tone: "accent",
    text: (runway) =>
      runway.repair_turns_remaining
        ? `Repair ${runway.repair_turns_remaining}t`
        : "Repairing",
  },
};

function RunwayGauge({ runway }: { runway: Runway }) {
  const gauge = RUNWAY_GAUGE[runway.state];
  return (
    <Gauge
      label="Runway"
      value={gauge.value}
      tone={gauge.tone}
      valueText={gauge.text(runway)}
    />
  );
}

function ControlPointInspector(props: { id: string; onClose: () => void }) {
  // currentData: nothing from the previous selection while this one loads.
  const {
    currentData: data,
    error,
    isFetching,
  } = useGetControlPointSummaryQuery({
    cpId: props.id,
  });
  const navigate = useNavigate();
  if (!data) {
    return (
      <Pending
        isLoading={isFetching}
        error={error}
        what="base"
        onClose={props.onClose}
      />
    );
  }
  const openBase = () => navigate(PATHS.base(data.id));
  return (
    <Card
      title={data.name}
      subtitle={subtitle(
        data.category,
        distanceText(data.distance_to_front_nm),
      )}
      symbol={
        <MilSymbol
          sidc={data.sidc}
          size={22}
          label={`${data.blue ? "Friendly" : "Enemy"} ${data.category}`}
        />
      }
      onClose={props.onClose}
    >
      <ControlPointGauges summary={data} />
      <div className={styles.actions}>
        {data.blue ? (
          <>
            <Button disabled={!data.can_buy_aircraft} onClick={openBase}>
              Buy aircraft
            </Button>
            <Button disabled={!data.can_buy_ground_units} onClick={openBase}>
              Ground units
            </Button>
            {data.can_repair_runway && (
              <Button
                disabled={!data.can_afford_runway_repair}
                title={
                  data.can_afford_runway_repair
                    ? undefined
                    : "Not enough money for the repair"
                }
                onClick={openBase}
              >
                Repair ${data.runway_repair_cost}M
              </Button>
            )}
          </>
        ) : (
          <Button onClick={openBase}>Intel</Button>
        )}
      </div>
    </Card>
  );
}

function ControlPointGauges({ summary }: { summary: ControlPointSummary }) {
  const tone: GaugeTone = summary.blue ? "friendly" : "hostile";
  return (
    <div className={styles.gauges}>
      {summary.runway && <RunwayGauge runway={summary.runway} />}
      {summary.parking && (
        <CountGauge label="Parking" count={summary.parking} tone={tone} />
      )}
      {summary.ground_units && (
        <CountGauge
          label="Ground units"
          count={summary.ground_units}
          tone={tone}
        />
      )}
      {summary.ammo_depots.total > 0 && (
        <CountGauge
          label="Ammo depots"
          count={summary.ammo_depots}
          tone="accent"
        />
      )}
      {summary.fuel_depots.total > 0 && (
        <CountGauge
          label="Fuel depots"
          count={summary.fuel_depots}
          tone="accent"
        />
      )}
    </div>
  );
}

function TgoInspector(props: { id: string; onClose: () => void }) {
  // currentData: nothing from the previous selection while this one loads.
  const {
    currentData: data,
    error,
    isFetching,
  } = useGetTgoSummaryQuery({
    tgoId: props.id,
  });
  const navigate = useNavigate();
  const [openInfoDialog] = useOpenTgoInfoDialogMutation();
  if (!data) {
    return (
      <Pending
        isLoading={isFetching}
        error={error}
        what="site"
        onClose={props.onClose}
      />
    );
  }
  return (
    <Card
      title={data.name}
      subtitle={subtitle(
        data.category,
        data.control_point_name,
        distanceText(data.distance_to_front_nm),
      )}
      symbol={
        <MilSymbol
          sidc={data.sidc}
          size={22}
          label={`${data.blue ? "Friendly" : "Enemy"} ${data.category}`}
        />
      }
      onClose={props.onClose}
    >
      <TgoGauges summary={data} />
      <div className={styles.actions}>
        {/* The Qt site dialog (units, repair, buy) until it is migrated. */}
        <Button onClick={() => openInfoDialog({ tgoId: data.id })}>
          Details
        </Button>
        <Button onClick={() => navigate(PATHS.base(data.control_point_id))}>
          {data.control_point_name}
        </Button>
      </div>
    </Card>
  );
}

function TgoGauges({ summary }: { summary: TgoSummary }) {
  return (
    <div className={styles.gauges}>
      <CountGauge
        label="Units alive"
        count={summary.units}
        tone={summary.blue ? "friendly" : "hostile"}
      />
      {summary.dead && <p className={styles.note}>Destroyed</p>}
    </div>
  );
}

// "Ground forces HQ" tab (WEB-02.3): the Qt QGroundForcesHQ with the order pattern
// of the airfield tab. The -/+ only prepare the order, within the limits each row
// gets from the server; the server applies it on confirm and answers with what it
// refuses (budget, factory), shown as a toast. The front lines and their stances
// come from the server too.
import { commandErrorMessage } from "../api/commands";
import {
  Base,
  FrontLineStance,
  GroundForces,
  GroundUnitRow,
  useCheatMoveFrontLineMutation,
  useGetGroundForcesQuery,
  useOrderGroundUnitsMutation,
  useSetFrontLineStanceMutation,
} from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import { Button, IconButton, Table, useToast } from "../ui";
import styles from "./AirfieldTab.module.css";
import { money } from "./money";
import { Refusal, refusalOf, signed } from "./orders";
import { useState } from "react";

function stanceLabel(stance: string): string {
  return stance.charAt(0) + stance.slice(1).toLowerCase();
}

export function GroundForcesTab({ base }: { base: Base }) {
  const cpId = base.summary.id;
  const { data, error, isLoading } = useGetGroundForcesQuery({ cpId });
  if (isLoading) {
    return <p className={styles.hint}>Loading the ground forces…</p>;
  }
  if (error || data == null) {
    return (
      <p className={styles.hint} role="alert">
        {error
          ? commandErrorMessage(error as Refusal)
          : "No ground forces to show."}
      </p>
    );
  }
  return <GroundForcesBody base={base} forces={data} />;
}

function GroundForcesBody(props: { base: Base; forces: GroundForces }) {
  const { base, forces } = props;
  const toast = useToast();
  const cpId = base.summary.id;
  const [orderUnits, orderState] = useOrderGroundUnitsMutation();
  const [draft, setDraft] = useState<Record<string, number>>({});
  const busy = orderState.isLoading;

  const quantityOf = (row: GroundUnitRow) => draft[row.unit_id] ?? 0;
  const change = (row: GroundUnitRow, step: number) =>
    setDraft({ ...draft, [row.unit_id]: quantityOf(row) + step });

  const lines = forces.units.filter((row) => quantityOf(row) !== 0);
  const total = lines.reduce(
    (sum, row) => sum + quantityOf(row) * row.unit_cost,
    0,
  );
  const budgetAfter = base.budget - total;

  const send = async (
    orders: { unit_id: string; quantity: number }[],
    refused: string,
    done: string,
  ) => {
    const refusal = refusalOf(
      await orderUnits({ cpId, groundOrdersJs: { orders } }),
    );
    if (refusal !== null) {
      toast({
        title: refused,
        description: commandErrorMessage(refusal),
        tone: "danger",
      });
      return false;
    }
    toast({ title: done, tone: "success" });
    return true;
  };

  const confirm = async () => {
    const sent = await send(
      lines.map((row) => ({ unit_id: row.unit_id, quantity: quantityOf(row) })),
      "Order refused",
      "Order confirmed",
    );
    if (sent) {
      setDraft({});
    }
  };

  const cancelPending = (row: GroundUnitRow) =>
    send(
      [{ unit_id: row.unit_id, quantity: -row.pending }],
      "Cancellation refused",
      `Orders cancelled: ${row.name}`,
    );

  return (
    <div className={styles.layout}>
      <div className={styles.main}>
        <p className={styles.hint}>
          Ground units ordered now arrive next turn. They cannot be sold.
        </p>
        {forces.recruitment_refusal != null && (
          <p className={styles.warning} role="alert">
            {forces.recruitment_refusal}
          </p>
        )}
        <Table
          caption={`Ground units at ${base.summary.name}`}
          columns={[
            { key: "unit", header: "Unit", cell: (r) => r.name },
            {
              key: "cost",
              header: "Unit cost",
              cell: (r) => money(r.unit_cost),
              align: "end",
              mono: true,
            },
            {
              key: "owned",
              header: "Owned",
              cell: (r) => r.owned,
              align: "end",
              mono: true,
            },
            {
              key: "pending",
              header: "On order",
              align: "end",
              cell: (r) => (
                <span className={styles.pending}>
                  <span className={styles.mono}>{signed(r.pending)}</span>
                  {r.pending !== 0 && (
                    <Button
                      disabled={busy}
                      aria-label={`Cancel pending order of ${r.name}`}
                      onClick={() => cancelPending(r)}
                    >
                      Cancel
                    </Button>
                  )}
                </span>
              ),
            },
            {
              key: "order",
              header: "Order",
              align: "end",
              cell: (r) => (
                <span className={styles.stepper}>
                  <IconButton
                    variant="secondary"
                    aria-label={`Remove one ${r.name}`}
                    disabled={busy || quantityOf(r) <= -r.pending}
                    onClick={() => change(r, -1)}
                  >
                    −
                  </IconButton>
                  <span
                    className={styles.quantity}
                    aria-label={`Order for ${r.name}`}
                  >
                    {signed(quantityOf(r))}
                  </span>
                  <IconButton
                    variant="secondary"
                    aria-label={`Add one ${r.name}`}
                    disabled={busy || quantityOf(r) >= r.max_add}
                    onClick={() => change(r, 1)}
                  >
                    +
                  </IconButton>
                </span>
              ),
            },
          ]}
          rows={forces.units}
          rowKey={(r) => r.unit_id}
          emptyText="Your faction has no ground units."
        />
      </div>
      <div className={styles.column}>
        <aside className={styles.summary} aria-label="Order summary">
          <h3 className={styles.title}>Order summary</h3>
          {lines.length === 0 ? (
            <p className={styles.hint}>Use − and + to prepare an order.</p>
          ) : (
            lines.map((row) => (
              <div key={row.unit_id} className={styles.line}>
                <span>
                  {quantityOf(row)} × {row.name}
                </span>
                <span className={styles.mono}>
                  {money(quantityOf(row) * row.unit_cost)}
                </span>
              </div>
            ))
          )}
          <div className={styles.separator} />
          <div className={styles.total}>
            <span>Total</span>
            <span className={styles.mono}>{money(total)}</span>
          </div>
          <div className={styles.line}>
            <span className={styles.hint}>Budget after order</span>
            <span className={budgetAfter < 0 ? styles.over : styles.mono}>
              {money(budgetAfter)}
            </span>
          </div>
          <Button
            variant="primary"
            size="lg"
            disabled={busy || lines.length === 0}
            onClick={confirm}
          >
            Confirm order
          </Button>
        </aside>
        <ForcesPanel forces={forces} />
        {forces.front_lines.length > 0 && (
          <FrontLinesPanel cpId={cpId} forces={forces} />
        )}
      </div>
    </div>
  );
}

function ForcesPanel({ forces }: { forces: GroundForces }) {
  const rows: [string, number | string][] = [
    ["Ground units here", forces.present],
    ["Ordered", forces.ordered],
    ["On their way here", forces.transferring],
  ];
  if (forces.deployable_limit != null) {
    rows.push(["Deployable at the front", forces.deployable_limit]);
    rows.push(["Held in reserve", forces.reserve ?? 0]);
  }
  rows.push(["Factory", forces.has_factory ? "Yes" : "No"]);
  return (
    <section className={styles.incoming} aria-label="Forces at this base">
      <h3 className={styles.title}>Forces at this base</h3>
      {rows.map(([label, value]) => (
        <div key={label} className={styles.line}>
          <span className={styles.hint}>{label}</span>
          <span className={styles.mono}>{value}</span>
        </div>
      ))}
    </section>
  );
}

function FrontLinesPanel(props: { cpId: string; forces: GroundForces }) {
  const { cpId, forces } = props;
  return (
    <section className={styles.incoming} aria-label="Front lines">
      <h3 className={styles.title}>Front lines</h3>
      {forces.front_lines.map((front) => (
        <FrontLineRow
          key={front.enemy_id}
          cpId={cpId}
          front={front}
          options={forces.stance_options}
          cheats={forces.front_line_cheats}
        />
      ))}
    </section>
  );
}

function FrontLineRow(props: {
  cpId: string;
  front: FrontLineStance;
  options: string[];
  cheats: boolean;
}) {
  const { cpId, front } = props;
  const toast = useToast();
  const [setStance, stanceState] = useSetFrontLineStanceMutation();
  const [moveFrontLine, moveState] = useCheatMoveFrontLineMutation();

  const refused = (title: string, refusal: Refusal) =>
    toast({
      title,
      description: commandErrorMessage(refusal),
      tone: "danger",
    });

  const choose = async (stance: string) => {
    const refusal = refusalOf(
      await setStance({
        cpId,
        enemyId: front.enemy_id,
        stanceJs: { stance },
      }),
    );
    if (refusal !== null) {
      refused("Stance refused", refusal);
    }
  };

  const move = async (advance: boolean) => {
    const refusal = refusalOf(
      await moveFrontLine({
        cpId,
        enemyId: front.enemy_id,
        frontLineCheatJs: { advance },
      }),
    );
    if (refusal !== null) {
      refused("Cheat refused", refusal);
    }
  };

  return (
    <div className={styles.form}>
      <label className={styles.field}>
        Against {front.enemy}
        <select
          className={settings.select}
          value={front.stance}
          disabled={stanceState.isLoading}
          onChange={(event) => choose(event.target.value)}
        >
          {props.options.map((stance) => (
            <option key={stance} value={stance}>
              {stanceLabel(stance)}
            </option>
          ))}
        </select>
      </label>
      {props.cheats && (
        <div className={styles.actions}>
          <Button
            variant="danger"
            disabled={moveState.isLoading}
            aria-label={`Cheat: advance against ${front.enemy}`}
            onClick={() => move(true)}
          >
            Cheat: Advance
          </Button>
          <Button
            variant="danger"
            disabled={moveState.isLoading}
            aria-label={`Cheat: retreat against ${front.enemy}`}
            onClick={() => move(false)}
          >
            Cheat: Retreat
          </Button>
        </div>
      )}
    </div>
  );
}

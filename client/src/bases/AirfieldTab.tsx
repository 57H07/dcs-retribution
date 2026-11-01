// "Airfield command" tab (WEB-02.2), after mockups/Base.dc.html: the squadrons of
// the base with their orders, the summary of the order being prepared, and the
// creation of a squadron. The -/+ only prepare the order, within the limits each
// row gets from the server; the server applies it on confirm and answers with what
// it refuses (budget, parking and squadron limits across rows), shown as a toast.
import { commandErrorMessage } from "../api/commands";
import {
  Base,
  SquadronChoice,
  SquadronOrderRow,
  useCancelAircraftOrderMutation,
  useCreateSquadronMutation,
  useGetSquadronChoicesQuery,
  useOrderAircraftMutation,
} from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import { Button, IconButton, Modal, ModalClose, Table, useToast } from "../ui";
import styles from "./AirfieldTab.module.css";
import { money } from "./money";
import { refusalOf, signed } from "./orders";
import { useState } from "react";

function owned(row: SquadronOrderRow): string {
  return row.max_aircraft != null
    ? `${row.owned} / ${row.max_aircraft}`
    : `${row.owned}`;
}

export function AirfieldTab({ base }: { base: Base }) {
  const toast = useToast();
  const [orderAircraft, orderState] = useOrderAircraftMutation();
  const [cancelOrder, cancelState] = useCancelAircraftOrderMutation();
  const [draft, setDraft] = useState<Record<string, number>>({});
  const cpId = base.summary.id;
  const { squadrons, parking_after_delivery: parking, incoming } = base.airfield;
  const busy = orderState.isLoading || cancelState.isLoading;

  const quantityOf = (row: SquadronOrderRow) => draft[row.squadron_id] ?? 0;
  const change = (row: SquadronOrderRow, step: number) =>
    setDraft({ ...draft, [row.squadron_id]: quantityOf(row) + step });

  const lines = squadrons.filter((row) => quantityOf(row) !== 0);
  const total = lines.reduce(
    (sum, row) => sum + quantityOf(row) * row.unit_cost,
    0,
  );
  const budgetAfter = base.budget - total;
  const parkingAfter =
    parking.current + lines.reduce((sum, row) => sum + quantityOf(row), 0);

  const confirm = async () => {
    const refusal = refusalOf(
      await orderAircraft({
        cpId,
        aircraftOrdersJs: {
          orders: lines.map((row) => ({
            squadron_id: row.squadron_id,
            quantity: quantityOf(row),
          })),
        },
      }),
    );
    if (refusal !== null) {
      toast({
        title: "Order refused",
        description: commandErrorMessage(refusal),
        tone: "danger",
      });
    } else {
      setDraft({});
      toast({ title: "Order confirmed", tone: "success" });
    }
  };

  const cancelPending = async (row: SquadronOrderRow) => {
    const refusal = refusalOf(
      await cancelOrder({ cpId, squadronId: row.squadron_id }),
    );
    if (refusal !== null) {
      toast({
        title: "Cancellation refused",
        description: commandErrorMessage(refusal),
        tone: "danger",
      });
    } else {
      toast({ title: `Orders cancelled: ${row.squadron}`, tone: "success" });
    }
  };

  return (
    <div className={styles.layout}>
      <div className={styles.main}>
        <p className={styles.hint}>Aircraft ordered now arrive next turn.</p>
        <Table
          caption={`Squadrons at ${base.summary.name}`}
          columns={[
            { key: "squadron", header: "Squadron", cell: (r) => r.squadron },
            { key: "aircraft", header: "Aircraft", cell: (r) => r.aircraft },
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
              cell: owned,
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
                      aria-label={`Cancel pending order of ${r.squadron}`}
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
                    aria-label={`Remove one from ${r.squadron}`}
                    disabled={busy || quantityOf(r) <= -r.max_remove}
                    onClick={() => change(r, -1)}
                  >
                    −
                  </IconButton>
                  <span
                    className={styles.quantity}
                    aria-label={`Order for ${r.squadron}`}
                  >
                    {signed(quantityOf(r))}
                  </span>
                  <IconButton
                    variant="secondary"
                    aria-label={`Add one to ${r.squadron}`}
                    disabled={busy || quantityOf(r) >= r.max_add}
                    onClick={() => change(r, 1)}
                  >
                    +
                  </IconButton>
                </span>
              ),
            },
          ]}
          rows={squadrons}
          rowKey={(r) => r.squadron_id}
          emptyText="No squadron here yet: create one to buy aircraft."
        />
        <CreateSquadron cpId={cpId} baseName={base.summary.name} />
        {incoming.length > 0 && (
          <section className={styles.incoming} aria-label="Transferring here">
            <h3 className={styles.title}>Transferring here next turn</h3>
            <ul>
              {incoming.map((squadron) => (
                <li key={squadron.squadron}>
                  {squadron.squadron} ({squadron.aircraft}) ·{" "}
                  {squadron.owned} aircraft from {squadron.origin}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
      <aside className={styles.summary} aria-label="Order summary">
        <h3 className={styles.title}>Order summary</h3>
        {lines.length === 0 ? (
          <p className={styles.hint}>Use − and + to prepare an order.</p>
        ) : (
          lines.map((row) => (
            <div key={row.squadron_id} className={styles.line}>
              <span>
                {quantityOf(row)} × {row.aircraft}
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
        <div className={styles.line}>
          <span className={styles.hint}>Parking after delivery</span>
          <span
            className={parkingAfter > parking.total ? styles.over : styles.mono}
          >
            {parkingAfter} / {parking.total}
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
    </div>
  );
}

function CreateSquadron(props: { cpId: string; baseName: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Modal
      title={`New squadron at ${props.baseName}`}
      open={open}
      onOpenChange={setOpen}
      trigger={
        <Button className={styles.create}>
          + Create a squadron at {props.baseName}
        </Button>
      }
    >
      {open && (
        <SquadronForm cpId={props.cpId} onDone={() => setOpen(false)} />
      )}
    </Modal>
  );
}

function SquadronForm(props: { cpId: string; onDone: () => void }) {
  const toast = useToast();
  const { cpId } = props;
  const { data: choices, isLoading } = useGetSquadronChoicesQuery({ cpId });
  const [createSquadron, createState] = useCreateSquadronMutation();
  const [aircraftId, setAircraftId] = useState<string>();
  const [task, setTask] = useState<string>();
  const [preset, setPreset] = useState("");

  if (isLoading) {
    return <p className={styles.hint}>Loading the available aircraft…</p>;
  }
  if (!choices || choices.length === 0) {
    return (
      <p className={styles.hint}>No aircraft of your faction can use this base.</p>
    );
  }
  const choice: SquadronChoice =
    choices.find((c) => c.aircraft === aircraftId) ?? choices[0];
  const primaryTask = task !== undefined && choice.tasks.includes(task)
    ? task
    : choice.tasks[0];

  const create = async () => {
    const refusal = refusalOf(
      await createSquadron({
        cpId,
        newSquadronJs: {
          aircraft: choice.aircraft,
          primary_task: primaryTask,
          preset: preset === "" ? null : preset,
        },
      }),
    );
    if (refusal !== null) {
      toast({
        title: "Squadron refused",
        description: commandErrorMessage(refusal),
        tone: "danger",
      });
    } else {
      toast({ title: "Squadron created", tone: "success" });
      props.onDone();
    }
  };

  return (
    <div className={styles.form}>
      <label className={styles.field}>
        Aircraft
        <select
          className={settings.select}
          value={choice.aircraft}
          onChange={(event) => {
            setAircraftId(event.target.value);
            setPreset("");
          }}
        >
          {choices.map((c) => (
            <option key={c.aircraft} value={c.aircraft}>
              {c.display_name}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.field}>
        Primary task
        <select
          className={settings.select}
          value={primaryTask}
          onChange={(event) => setTask(event.target.value)}
        >
          {choice.tasks.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.field}>
        Preset
        <select
          className={settings.select}
          value={preset}
          onChange={(event) => setPreset(event.target.value)}
        >
          <option value="">None (random)</option>
          {choice.presets.map((p) => (
            <option key={p.name} value={p.name}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      <div className={styles.actions}>
        <ModalClose asChild>
          <Button>Cancel</Button>
        </ModalClose>
        <Button
          variant="primary"
          disabled={createState.isLoading || primaryTask === undefined}
          onClick={create}
        >
          Create squadron
        </Button>
      </div>
    </div>
  );
}

// New unit transfer (WEB-02.3): the Qt NewUnitTransferDialog. The server lists the
// destinations, the units and the squadrons of the chosen destination, and refuses
// what cannot be done (units, route, what a squadron can carry) with a toast.
import { commandErrorMessage } from "../api/commands";
import {
  TransferableUnit,
  useCreateTransferMutation,
  useGetTransferOptionsQuery,
} from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import { Button, IconButton, Modal, ModalClose, useToast } from "../ui";
import styles from "./AirfieldTab.module.css";
import { refusalOf } from "./orders";
import { useState } from "react";

export type TransferKind = "transfer" | "transport";

const AI_ASSIGNED = "";

export function TransferButton(props: {
  cpId: string;
  baseName: string;
  kind: TransferKind;
}) {
  const [open, setOpen] = useState(false);
  const { kind, baseName } = props;
  return (
    <Modal
      title={
        kind === "transport"
          ? `New Transport mission from ${baseName}`
          : `New unit transfer from ${baseName}`
      }
      open={open}
      onOpenChange={setOpen}
      trigger={
        <Button
          title={
            kind === "transport"
              ? "Airlift reserve ground units to another friendly base with a squadron of your choice, and fly it yourself."
              : undefined
          }
        >
          {kind === "transport" ? "Transport mission" : "Transfer units"}
        </Button>
      }
    >
      {open && (
        <TransferForm
          cpId={props.cpId}
          kind={kind}
          onDone={() => setOpen(false)}
        />
      )}
    </Modal>
  );
}

function TransferForm(props: {
  cpId: string;
  kind: TransferKind;
  onDone: () => void;
}) {
  const { cpId, kind } = props;
  const toast = useToast();
  const [destination, setDestination] = useState<string>();
  const [airlift, setAirlift] = useState(kind === "transport");
  // Undefined until the player chooses: a Transport mission starts on the first
  // squadron, a transfer on the AI.
  const [squadron, setSquadron] = useState<string>();
  const [counts, setCounts] = useState<Record<string, number>>({});
  const { data: options, isLoading } = useGetTransferOptionsQuery({
    cpId,
    destinationId: destination,
  });
  const [createTransfer, createState] = useCreateTransferMutation();

  if (isLoading) {
    return <p className={styles.hint}>Loading the options…</p>;
  }
  if (!options || options.destinations.length === 0) {
    return <p className={styles.hint}>No friendly base can receive units.</p>;
  }
  const destinationId = options.destination_id ?? options.destinations[0].id;
  const defaultSquadron =
    kind === "transport" ? (options.squadrons[0]?.id ?? AI_ASSIGNED) : AI_ASSIGNED;
  const chosen = options.squadrons.some((s) => s.id === squadron)
    ? (squadron as string)
    : squadron === AI_ASSIGNED
      ? AI_ASSIGNED
      : defaultSquadron;
  const squadronId = airlift && chosen !== AI_ASSIGNED ? chosen : null;

  const countOf = (unit: TransferableUnit) => counts[unit.unit_id] ?? 0;
  const change = (unit: TransferableUnit, step: number) =>
    setCounts({ ...counts, [unit.unit_id]: countOf(unit) + step });
  const selected = options.units.filter((unit) => countOf(unit) > 0);

  const submit = async () => {
    const refusal = refusalOf(
      await createTransfer({
        newTransferJs: {
          origin_id: cpId,
          destination_id: destinationId,
          units: selected.map((unit) => ({
            unit_id: unit.unit_id,
            count: countOf(unit),
          })),
          airlift,
          squadron_id: squadronId,
        },
      }),
    );
    if (refusal !== null) {
      toast({
        title: "Transfer refused",
        description: commandErrorMessage(refusal),
        tone: "danger",
      });
    } else {
      toast({ title: "Transfer ordered", tone: "success" });
      props.onDone();
    }
  };

  return (
    <div className={styles.form}>
      <label className={styles.field}>
        Destination
        <select
          className={settings.select}
          value={destinationId}
          onChange={(event) => setDestination(event.target.value)}
        >
          {options.destinations.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.field}>
        Requested transport type
        <select
          className={settings.select}
          value={airlift ? "airlift" : "auto"}
          onChange={(event) => setAirlift(event.target.value === "airlift")}
        >
          <option value="auto">Auto</option>
          <option value="airlift">Airlift</option>
        </select>
      </label>
      <label className={styles.field}>
        Transport squadron
        <select
          className={settings.select}
          value={airlift ? chosen : AI_ASSIGNED}
          disabled={!airlift}
          title="Pick a squadron to create a Transport mission you can fly. AI-assigned lets the AI plan the airlift with auto-assignable squadrons."
          onChange={(event) => setSquadron(event.target.value)}
        >
          <option value={AI_ASSIGNED}>AI-assigned</option>
          {options.squadrons.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label} (up to {s.capacity} units)
            </option>
          ))}
        </select>
      </label>
      {airlift && options.no_squadron_warning != null && (
        <p className={styles.warning} role="alert">
          {options.no_squadron_warning}
        </p>
      )}
      {options.units.length === 0 ? (
        <p className={styles.hint}>This base has no ground units to send.</p>
      ) : (
        options.units.map((unit) => (
          <div key={unit.unit_id} className={styles.line}>
            <span>
              {unit.name} <span className={styles.hint}>· {unit.available}</span>
            </span>
            <span className={styles.stepper}>
              <IconButton
                variant="secondary"
                aria-label={`Send one ${unit.name} less`}
                disabled={countOf(unit) <= 0}
                onClick={() => change(unit, -1)}
              >
                −
              </IconButton>
              <span
                className={styles.quantity}
                aria-label={`${unit.name} to send`}
              >
                {countOf(unit)}
              </span>
              <IconButton
                variant="secondary"
                aria-label={`Send one more ${unit.name}`}
                disabled={countOf(unit) >= unit.available}
                onClick={() => change(unit, 1)}
              >
                +
              </IconButton>
            </span>
          </div>
        ))
      )}
      <div className={styles.actions}>
        <ModalClose asChild>
          <Button>Cancel</Button>
        </ModalClose>
        <Button
          variant="primary"
          disabled={createState.isLoading || selected.length === 0}
          onClick={submit}
        >
          {squadronId !== null
            ? "Create Transport mission"
            : "Create transfer order"}
        </Button>
      </div>
    </div>
  );
}

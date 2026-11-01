// Squadron sheet of the air wing screen (WEB-03): the Qt SquadronDialog. Orders
// reuse the base screen's commands (WEB-02.2), so the same limits apply; the -/+
// stay within what the server says this squadron can order right now.
import {
  AirWingSquadron,
  SquadronOrderRow,
  useCancelAircraftOrderMutation,
  useCreatePlayerPilotMutation,
  useGetSquadronDestinationsQuery,
  useGetSquadronLiveriesQuery,
  useOrderAircraftMutation,
  useOrderRepairMutation,
  useSetSquadronAutoAssignMutation,
  useSetSquadronDestinationMutation,
  useSetSquadronLiveryMutation,
  useSetSquadronPrimaryTaskMutation,
} from "../api/liberationApi";
import { money } from "../bases/money";
import settings from "../settings/SettingsScreen.module.css";
import { Button, Gauge, IconButton, MilSymbol, Modal, TaskTag } from "../ui";
import styles from "./AirWing.module.css";
import { NameModal, PilotsTable } from "./PilotsTable";
import { useCommand } from "./useCommand";
import { useState } from "react";

function AircraftOrder({
  squadron,
  order,
}: {
  squadron: AirWingSquadron;
  order: SquadronOrderRow;
}) {
  const run = useCommand();
  const [orderAircraft, orderState] = useOrderAircraftMutation();
  const [cancelOrder, cancelState] = useCancelAircraftOrderMutation();
  const [quantity, setQuantity] = useState(0);
  const busy = orderState.isLoading || cancelState.isLoading;
  const cpId = squadron.base_id;
  const label =
    quantity < 0
      ? `Sell ${-quantity} aircraft · ${money(-quantity * order.unit_cost)}`
      : quantity > 0
        ? `Buy ${quantity} aircraft · ${money(quantity * order.unit_cost)}`
        : "Buy aircraft";

  const confirm = async () => {
    const done = await run(
      orderAircraft({
        cpId,
        aircraftOrdersJs: {
          orders: [{ squadron_id: squadron.id, quantity }],
        },
      }),
      "Order refused",
    );
    if (done) {
      setQuantity(0);
    }
  };

  return (
    <div className={styles.order} aria-label="Aircraft order" role="group">
      <span className={styles.stepper}>
        <IconButton
          variant="secondary"
          aria-label="One aircraft less"
          disabled={busy || quantity <= -order.max_remove}
          onClick={() => setQuantity(quantity - 1)}
        >
          −
        </IconButton>
        <span className={styles.quantity} aria-label="Quantity to order">
          {quantity}
        </span>
        <IconButton
          variant="secondary"
          aria-label="One aircraft more"
          disabled={busy || quantity >= order.max_add}
          onClick={() => setQuantity(quantity + 1)}
        >
          +
        </IconButton>
      </span>
      <Button
        variant="primary"
        disabled={busy || quantity === 0}
        onClick={confirm}
      >
        {label}
      </Button>
      {order.pending !== 0 && (
        <Button
          disabled={busy}
          onClick={() =>
            run(
              cancelOrder({ cpId, squadronId: squadron.id }),
              "Cancellation refused",
            )
          }
        >
          Cancel pending ({order.pending})
        </Button>
      )}
    </div>
  );
}

function TransferModal({
  squadron,
  onClose,
}: {
  squadron: AirWingSquadron;
  onClose: () => void;
}) {
  const run = useCommand();
  const { data, isLoading } = useGetSquadronDestinationsQuery(
    { squadronId: squadron.id },
    { refetchOnMountOrArgChange: true },
  );
  const [setDestination, state] = useSetSquadronDestinationMutation();
  const go = async (destinationId: string | null) => {
    const done = await run(
      setDestination({
        squadronId: squadron.id,
        setDestinationJs: { destination_id: destinationId },
      }),
      "Transfer refused",
    );
    if (done) {
      onClose();
    }
  };
  return (
    <Modal
      title={`Transfer ${squadron.name}`}
      open
      onOpenChange={(open) => !open && onClose()}
    >
      {isLoading || !data ? (
        <p className={styles.hint}>Looking for parking…</p>
      ) : (
        <ul className={styles.destinations}>
          <li className={styles.destination}>
            <span>
              Remain at {squadron.base}{" "}
              <span className={styles.hint}>
                room for {data.room_here} more aircraft
              </span>
            </span>
            <Button
              disabled={state.isLoading || squadron.destination == null}
              onClick={() => go(null)}
            >
              {squadron.destination == null ? "Current" : "Stay"}
            </Button>
          </li>
          {data.destinations.map((destination) => (
            <li key={destination.id} className={styles.destination}>
              <span>
                {destination.name}{" "}
                <span className={styles.hint}>
                  {destination.refusal ??
                    `room for ${destination.room} more aircraft`}
                </span>
                {destination.overflow.length > 0 && (
                  <span className={styles.warning}>
                    May start in the air: {destination.overflow.join(", ")}
                  </span>
                )}
              </span>
              <Button
                variant={destination.selected ? "secondary" : "primary"}
                disabled={
                  state.isLoading ||
                  destination.selected ||
                  destination.refusal != null
                }
                onClick={() => go(destination.id)}
              >
                {destination.selected ? "Ordered" : "Transfer"}
              </Button>
            </li>
          ))}
          {data.destinations.length === 0 && (
            <li className={styles.hint}>No other base can take this squadron.</li>
          )}
        </ul>
      )}
    </Modal>
  );
}

function LiverySelect({ squadron }: { squadron: AirWingSquadron }) {
  const run = useCommand();
  const { data: choices = [] } = useGetSquadronLiveriesQuery(
    { squadronId: squadron.id },
    { refetchOnMountOrArgChange: true },
  );
  const [setLivery, state] = useSetSquadronLiveryMutation();
  if (choices.length === 0) {
    return (
      <label className={styles.field}>
        Livery
        <select className={settings.select} disabled>
          <option>No available liveries (using DCS default)</option>
        </select>
      </label>
    );
  }
  const selected = Math.max(
    choices.findIndex((choice) => choice.selected),
    0,
  );
  return (
    <label className={styles.field}>
      Livery
      <select
        className={settings.select}
        value={selected}
        disabled={state.isLoading}
        onChange={(event) => {
          const choice = choices[Number(event.target.value)];
          run(
            setLivery({
              squadronId: squadron.id,
              setLiveryJs: {
                livery_id: choice.livery_id,
                use_livery_set: choice.use_livery_set,
              },
            }),
            "Could not change the livery",
          );
        }}
      >
        {choices.map((choice, index) => (
          <option key={choice.label} value={index}>
            {choice.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function Tasks({ squadron }: { squadron: AirWingSquadron }) {
  const run = useCommand();
  const [setPrimary, primaryState] = useSetSquadronPrimaryTaskMutation();
  const [setAutoAssign, autoState] = useSetSquadronAutoAssignMutation();
  return (
    <section className={styles.panel} aria-label="Tasks">
      <div className={styles.fields}>
        <label className={styles.field}>
          Primary task
          <select
            className={settings.select}
            value={squadron.primary_task}
            disabled={primaryState.isLoading}
            onChange={(event) =>
              run(
                setPrimary({
                  squadronId: squadron.id,
                  primaryTaskJs: { task: event.target.value },
                }),
                "Could not change the primary task",
              )
            }
          >
            {squadron.tasks.map(({ task }) => (
              <option key={task} value={task}>
                {task}
              </option>
            ))}
          </select>
        </label>
        <LiverySelect squadron={squadron} />
      </div>
      <fieldset className={styles.tasks}>
        <legend className={styles.label}>Auto-assignable tasks</legend>
        {squadron.tasks.map(({ task, auto_assign }) => (
          <label key={task} className={styles.task}>
            <input
              type="checkbox"
              checked={auto_assign}
              disabled={autoState.isLoading}
              onChange={(event) =>
                run(
                  setAutoAssign({
                    squadronId: squadron.id,
                    autoAssignJs: { task, enabled: event.target.checked },
                  }),
                  "Could not change the tasks",
                )
              }
            />
            <TaskTag task={task} />
          </label>
        ))}
      </fieldset>
    </section>
  );
}

function Figures({ squadron }: { squadron: AirWingSquadron }) {
  const run = useCommand();
  const [orderRepair, repairState] = useOrderRepairMutation();
  const max = squadron.max_aircraft ?? squadron.owned;
  const { repair } = squadron;
  return (
    <div className={styles.figures}>
      <div className={styles.figure}>
        <span className={styles.label}>Aircraft</span>
        <span className={styles.big}>
          {squadron.owned}
          {squadron.max_aircraft != null && (
            <span className={styles.small}> / {squadron.max_aircraft}</span>
          )}
        </span>
        <Gauge
          label="Aircraft"
          hideLabel
          value={squadron.owned}
          max={max}
          valueText={null}
        />
        <span className={styles.hint}>
          {squadron.initial} initial · {squadron.purchased} purchased ·{" "}
          {squadron.available} available · {squadron.untasked_crewed} crewed
          unassigned
        </span>
        {squadron.in_maintenance > 0 && (
          <span className={styles.hint}>{squadron.maintenance_text}</span>
        )}
        {repair != null && (
          <Button
            disabled={repairState.isLoading || !repair.affordable}
            onClick={() =>
              run(
                orderRepair({
                  cpId: squadron.base_id,
                  repairId: repair.repair_id,
                }),
                "Repair refused",
              )
            }
          >
            Repair {squadron.in_maintenance} aircraft · {money(repair.cost)}
          </Button>
        )}
      </div>
      <div className={styles.figure}>
        <span className={styles.label}>Pilots ready</span>
        <span className={styles.big}>
          {squadron.pilots_ready}
          <span className={styles.small}> / {squadron.pilots_alive}</span>
        </span>
        <Gauge
          label="Pilots ready"
          hideLabel
          tone="success"
          value={squadron.pilots_ready}
          max={squadron.pilots_alive}
          valueText={null}
        />
      </div>
      <div className={styles.figure}>
        <span className={styles.label}>Sorties · kills</span>
        <span className={styles.big}>
          {squadron.sorties}
          <span className={styles.small}> · {squadron.kills}</span>
        </span>
        <span className={styles.hint}>
          {squadron.destroyed} aircraft lost this campaign
        </span>
      </div>
      <div className={styles.figure}>
        <span className={styles.label}>Next turn</span>
        {squadron.next_turn.length === 0 ? (
          <span className={styles.hint}>Nothing arriving</span>
        ) : (
          squadron.next_turn.map((line) => (
            <span key={line} className={styles.nextTurn}>
              {line}
            </span>
          ))
        )}
      </div>
    </div>
  );
}

export function SquadronSheet({ squadron }: { squadron: AirWingSquadron }) {
  const run = useCommand();
  const [transferring, setTransferring] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createPilot] = useCreatePlayerPilotMutation();
  const hasFallen = squadron.pilots.some((pilot) => !pilot.alive);
  return (
    <main className={styles.sheet} aria-label={squadron.name}>
      <header className={styles.sheetHeader}>
        <MilSymbol sidc={squadron.sidc} size={44} label={squadron.primary_task} />
        <div className={styles.identity}>
          <h2 className={styles.sheetTitle}>{squadron.name}</h2>
          <span className={styles.hint}>
            {squadron.aircraft} · based at {squadron.base}
            {squadron.destination != null &&
              ` · transfer ordered to ${squadron.destination}`}
          </span>
        </div>
        <div className={styles.sheetActions}>
          <Button onClick={() => setTransferring(true)}>Transfer</Button>
          {squadron.order != null && (
            <AircraftOrder squadron={squadron} order={squadron.order} />
          )}
        </div>
      </header>
      {squadron.order != null && (
        <span className={styles.hint}>
          {squadron.parking_room} more parking slots at {squadron.base}.{" "}
          Aircraft ordered now arrive next turn.
        </span>
      )}
      <Figures squadron={squadron} />
      <Tasks squadron={squadron} />
      <section className={styles.panel} aria-label="Pilots">
        <div className={styles.panelHeader}>
          <h3 className={styles.panelTitle}>Pilots</h3>
          <Button
            title={squadron.new_pilot_refusal ?? undefined}
            disabled={squadron.new_pilot_refusal != null}
            onClick={() => setCreating(true)}
          >
            New player pilot
          </Button>
        </div>
        <PilotsTable
          caption="Pilots"
          squadrons={[squadron]}
          filter={(pilot) => pilot.alive}
          emptyText="No pilot left in this squadron."
        />
      </section>
      {hasFallen && (
        <section className={styles.panel} aria-label="Killed in action">
          <h3 className={styles.panelTitle}>Killed in action</h3>
          <PilotsTable
            caption="Killed in action"
            squadrons={[squadron]}
            filter={(pilot) => !pilot.alive}
            emptyText=""
          />
        </section>
      )}
      {transferring && (
        <TransferModal
          squadron={squadron}
          onClose={() => setTransferring(false)}
        />
      )}
      {creating && (
        <NameModal
          title={`New player pilot in ${squadron.name}`}
          label="Pilot name"
          submit="Add pilot"
          open
          onOpenChange={setCreating}
          onSubmit={(name) =>
            run(
              createPilot({ squadronId: squadron.id, newPilotJs: { name } }),
              "Could not add the pilot",
            )
          }
        />
      )}
    </main>
  );
}

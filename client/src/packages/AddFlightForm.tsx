// "+ Flight" of the package editor: the minimum of QFlightCreator (task, aircraft,
// squadron, size, start type). The server lists what is possible and has the last
// word; the rest of a flight comes with its tabs (WEB-04.2 to 04.5).
import { commandErrorMessage } from "../api/commands";
import {
  FlightOptions,
  StartType,
  useAddPackageFlightMutation,
  useGetFlightOptionsQuery,
} from "../api/liberationApi";
import {
  AircraftOptions,
  NoModulesHint,
} from "../preferences/AircraftOptions";
import settings from "../settings/SettingsScreen.module.css";
import { Button, Modal, ModalClose, NumberField, useToast } from "../ui";
import styles from "./PackageEditor.module.css";
import { useState } from "react";

export interface AddFlightButtonProps {
  packageId: string;
  onAdded: (flightId: string) => void;
}

export function AddFlightButton({ packageId, onAdded }: AddFlightButtonProps) {
  const [open, setOpen] = useState(false);
  return (
    <Modal
      title="Add flight"
      open={open}
      onOpenChange={setOpen}
      trigger={<Button variant="primary">+ Flight</Button>}
    >
      <AddFlightLoader
        packageId={packageId}
        onAdded={(flightId) => {
          setOpen(false);
          onAdded(flightId);
        }}
      />
    </Modal>
  );
}

function AddFlightLoader({ packageId, onAdded }: AddFlightButtonProps) {
  // Aircraft come and go with the other screens: never trust an older answer.
  const { data } = useGetFlightOptionsQuery(
    { packageId },
    { refetchOnMountOrArgChange: true },
  );
  if (data == null) {
    return <p className={styles.hint}>Loading…</p>;
  }
  return (
    <AddFlightForm packageId={packageId} options={data} onAdded={onAdded} />
  );
}

function AddFlightForm({
  packageId,
  options,
  onAdded,
}: AddFlightButtonProps & { options: FlightOptions }) {
  const toast = useToast();
  const [addFlight, addState] = useAddPackageFlightMutation();
  const [taskName, setTaskName] = useState<string>();
  const [aircraftId, setAircraftId] = useState<string>();
  const [squadronId, setSquadronId] = useState<string>();
  const [size, setSize] = useState<number>();
  const [startType, setStartType] = useState<StartType | "">("");

  // A choice that the previous field no longer offers falls back to the first.
  const task =
    options.tasks.find((t) => t.task === taskName) ?? options.tasks[0];
  const aircraft =
    task?.aircraft.find((a) => a.id === aircraftId) ?? task?.aircraft[0];
  const squadron =
    aircraft?.squadrons.find((s) => s.id === squadronId) ??
    aircraft?.squadrons[0];
  const flightSize =
    squadron && Math.min(size ?? squadron.max_size, squadron.max_size);
  const required = squadron?.required_start_type;

  const submit = async () => {
    if (!task || !squadron || flightSize === undefined) {
      return;
    }
    const result = await addFlight({
      packageId,
      newFlightJs: {
        task: task.task,
        squadron_id: squadron.id,
        size: flightSize,
        start_type: startType === "" ? undefined : startType,
      },
    });
    if ("error" in result) {
      toast({
        title: "Could not add the flight",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    } else {
      onAdded(result.data.flights[result.data.flights.length - 1].id);
    }
  };

  return (
    <div className={styles.form}>
      <label className={styles.field}>
        Task
        <select
          className={settings.select}
          value={task?.task ?? ""}
          onChange={(event) => setTaskName(event.target.value)}
        >
          {options.tasks.map((t) => (
            <option key={t.task} value={t.task}>
              {t.task}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.field}>
        Aircraft
        <select
          className={settings.select}
          value={aircraft?.id ?? ""}
          disabled={!aircraft}
          onChange={(event) => setAircraftId(event.target.value)}
        >
          {!aircraft && <option value="">No capable aircraft available</option>}
          {task && (
            <AircraftOptions
              options={task.aircraft.map((a) => ({
                id: a.id,
                name: a.name,
                playerModule: a.player_module,
              }))}
            />
          )}
        </select>
      </label>
      {task && !task.aircraft.some((a) => a.player_module) && <NoModulesHint />}
      <label className={styles.field}>
        Squadron
        <select
          className={settings.select}
          value={squadron?.id ?? ""}
          disabled={!squadron}
          onChange={(event) => setSquadronId(event.target.value)}
        >
          {aircraft?.squadrons.map((s) => (
            <option key={s.id} value={s.id}>
              {s.base}: {s.name} ({s.available} available)
            </option>
          ))}
        </select>
      </label>
      <NumberField
        label="Size"
        value={flightSize ?? 0}
        min={1}
        max={squadron?.max_size ?? 0}
        disabled={!squadron}
        onValueChange={setSize}
      />
      <label className={styles.field}>
        Start type
        <select
          className={settings.select}
          value={required ?? startType}
          disabled={required != null}
          onChange={(event) =>
            setStartType(event.target.value as StartType | "")
          }
        >
          {required == null && <option value="">Default for the task</option>}
          {options.start_types.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <p className={styles.hint}>
        Any start other than Cold makes this flight non-targetable by
        OCA/Aircraft missions, which affects game balance.
      </p>
      <div className={styles.formActions}>
        <ModalClose asChild>
          <Button>Cancel</Button>
        </ModalClose>
        <Button
          variant="primary"
          disabled={!squadron || addState.isLoading}
          onClick={submit}
        >
          Add flight
        </Button>
      </div>
    </div>
  );
}

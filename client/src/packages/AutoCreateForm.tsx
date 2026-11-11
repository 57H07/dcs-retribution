// "Auto-create" of the package editor, after QAutoCreateDialog: a main flight and
// optional ones, planned by the engine. The form and its limits come from the server.
import { commandErrorMessage } from "../api/commands";
import {
  AutoCreateFlight,
  AutoCreateOptions,
  AutoCreateTask,
  useAutoCreatePackageMutation,
  useGetAutoCreateOptionsQuery,
} from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import { Button, Modal, ModalClose, NumberField, useToast } from "../ui";
import styles from "./PackageEditor.module.css";
import { useState } from "react";

export function AutoCreateButton({ packageId }: { packageId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Modal
      title="Auto-create"
      description="Plans the flights with the aircraft and pilots available."
      open={open}
      onOpenChange={setOpen}
      size="lg"
      trigger={<Button>Auto-create</Button>}
    >
      <AutoCreateLoader packageId={packageId} onDone={() => setOpen(false)} />
    </Modal>
  );
}

interface LoaderProps {
  packageId: string;
  onDone: () => void;
}

function AutoCreateLoader({ packageId, onDone }: LoaderProps) {
  const { data } = useGetAutoCreateOptionsQuery(
    { packageId },
    { refetchOnMountOrArgChange: true },
  );
  if (data == null) {
    return <p className={styles.hint}>Loading…</p>;
  }
  if (data.primary.length === 0) {
    return (
      <p className={styles.hint}>
        Nothing can be auto-created against this target: add flights instead.
      </p>
    );
  }
  return (
    <AutoCreateFields packageId={packageId} options={data} onDone={onDone} />
  );
}

/** A task's row of the form; its aircraft may be empty (the planner chooses). */
interface Row {
  count: number;
  aircraft?: string;
}

/** The largest flight the planner can fill with this aircraft of the task. */
function maxCountOf(task: AutoCreateTask, aircraft?: string): number {
  return task.aircraft.find((a) => a.id === aircraft)?.max_count ?? Infinity;
}

function rowOf(rows: Record<string, Row>, task: AutoCreateTask): Row {
  const aircraft = task.aircraft[0]?.id;
  return (
    rows[task.task] ?? {
      count: Math.min(task.default_count, maxCountOf(task, aircraft)),
      aircraft,
    }
  );
}

function AutoCreateFields({
  packageId,
  options,
  onDone,
}: LoaderProps & { options: AutoCreateOptions }) {
  const toast = useToast();
  const [autoCreate, createState] = useAutoCreatePackageMutation();
  const [primaryTask, setPrimaryTask] = useState(options.primary[0].task);
  const [rows, setRows] = useState<Record<string, Row>>({});
  const [checked, setChecked] = useState<string[]>([]);

  const primary =
    options.primary.find((t) => t.task === primaryTask) ?? options.primary[0];
  const excluded = (task: string) =>
    primary.task === "CAS" && options.excluded_with_cas.includes(task);
  const setRow = (task: AutoCreateTask, change: Partial<Row>) =>
    setRows({ ...rows, [task.task]: { ...rowOf(rows, task), ...change } });

  // Without aircraft the planner has nothing to plan the task with.
  const unavailable = (task: AutoCreateTask) => task.aircraft.length === 0;
  const selectAircraft = (task: AutoCreateTask, aircraft: string) =>
    setRow(task, {
      aircraft,
      count: Math.min(rowOf(rows, task).count, maxCountOf(task, aircraft)),
    });

  const flight = (task: AutoCreateTask): AutoCreateFlight => ({
    task: task.task,
    ...rowOf(rows, task),
  });

  const submit = async () => {
    const support = options.support.filter(
      (task) =>
        checked.includes(task.task) &&
        !excluded(task.task) &&
        !unavailable(task),
    );
    const result = await autoCreate({
      packageId,
      autoCreateRequestJs: {
        flights: [flight(primary), ...support.map(flight)],
      },
    });
    if ("error" in result) {
      toast({
        title: "Could not auto-create the package",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    } else {
      onDone();
    }
  };

  const rowFields = (task: AutoCreateTask, disabled: boolean) => (
    <>
      <NumberField
        label={`${task.task} aircraft`}
        hideLabel
        value={rowOf(rows, task).count}
        min={options.min_count}
        max={Math.min(
          options.max_count,
          maxCountOf(task, rowOf(rows, task).aircraft),
        )}
        disabled={disabled}
        onValueChange={(count) => setRow(task, { count })}
      />
      <select
        className={settings.select}
        aria-label={`${task.task} aircraft type`}
        value={rowOf(rows, task).aircraft ?? ""}
        disabled={disabled || unavailable(task)}
        onChange={(event) => selectAircraft(task, event.target.value)}
      >
        {unavailable(task) && <option value="">None available</option>}
        {task.aircraft.map((aircraft) => (
          <option key={aircraft.id} value={aircraft.id}>
            {aircraft.name}
            {aircraft.max_count < options.max_count &&
              ` (${aircraft.max_count} at most)`}
          </option>
        ))}
      </select>
    </>
  );

  return (
    <div className={styles.form}>
      <div className={styles.autoRows}>
        <select
          className={settings.select}
          aria-label="Main task"
          value={primary.task}
          onChange={(event) => setPrimaryTask(event.target.value)}
        >
          {options.primary.map((task) => (
            <option key={task.task} value={task.task}>
              {task.task}
            </option>
          ))}
        </select>
        {rowFields(primary, false)}
        {options.support.map((task) => {
          const disabled = excluded(task.task) || unavailable(task);
          return (
            <div key={task.task} className={styles.autoRow}>
              <label className={styles.autoCheck}>
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={!disabled && checked.includes(task.task)}
                  onChange={(event) =>
                    setChecked(
                      event.target.checked
                        ? [...checked, task.task]
                        : checked.filter((t) => t !== task.task),
                    )
                  }
                />
                {task.task}
              </label>
              {rowFields(task, disabled || !checked.includes(task.task))}
            </div>
          );
        })}
      </div>
      <div className={styles.formActions}>
        <ModalClose asChild>
          <Button>Cancel</Button>
        </ModalClose>
        <Button
          variant="primary"
          disabled={createState.isLoading || unavailable(primary)}
          onClick={submit}
        >
          Create
        </Button>
      </div>
    </div>
  );
}

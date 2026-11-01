// "Add waypoint" of the Route tab: a front line, target or base the engine offers.
import { commandErrorMessage } from "../../api/commands";
import {
  useAddPredefinedWaypointMutation,
  useListPredefinedWaypointsQuery,
} from "../../api/liberationApi";
import settings from "../../settings/SettingsScreen.module.css";
import { Button, Modal, ModalClose, Switch, useToast } from "../../ui";
import editor from "../PackageEditor.module.css";
import styles from "./RouteTab.module.css";
import { useState } from "react";

export function AddWaypointButton({ flightId }: { flightId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Modal
      title="Add waypoint"
      open={open}
      onOpenChange={setOpen}
      trigger={<Button>Add waypoint</Button>}
    >
      <AddWaypointForm flightId={flightId} onAdded={() => setOpen(false)} />
    </Modal>
  );
}

function AddWaypointForm({
  flightId,
  onAdded,
}: {
  flightId: string;
  onAdded: () => void;
}) {
  const toast = useToast();
  const { data } = useListPredefinedWaypointsQuery(
    { flightId },
    { refetchOnMountOrArgChange: true },
  );
  const [add, addState] = useAddPredefinedWaypointMutation();
  const [filter, setFilter] = useState("");
  const [name, setName] = useState<string>();
  const [sameLocation, setSameLocation] = useState(true);

  if (data == null) {
    return <p className={editor.hint}>Loading…</p>;
  }

  const needle = filter.trim().toLowerCase();
  const shown = data.filter((w) => w.name.toLowerCase().includes(needle));
  const selected = shown.find((w) => w.name === name) ?? shown[0];

  const submit = async () => {
    if (selected === undefined) {
      return;
    }
    const result = await add({
      flightId,
      newPredefinedWaypointJs: {
        name: selected.name,
        same_location: sameLocation,
      },
    });
    if ("error" in result) {
      toast({
        title: "Could not add the waypoint",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    } else {
      onAdded();
    }
  };

  return (
    <div className={editor.form}>
      <label className={editor.field}>
        Filter
        <input
          className={styles.name}
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        />
      </label>
      <label className={editor.field}>
        Waypoint
        <select
          className={settings.select}
          size={8}
          value={selected?.name ?? ""}
          onChange={(event) => setName(event.target.value)}
        >
          {shown.map((w) => (
            <option key={w.name} value={w.name}>
              {w.name}
            </option>
          ))}
        </select>
      </label>
      {selected !== undefined && (
        <p className={editor.hint}>{selected.description}</p>
      )}
      {selected?.has_siblings && (
        <Switch
          label="Include all objects from the same location"
          checked={sameLocation}
          onCheckedChange={setSameLocation}
        />
      )}
      <div className={editor.formActions}>
        <ModalClose asChild>
          <Button variant="ghost">Cancel</Button>
        </ModalClose>
        <Button
          variant="primary"
          disabled={selected === undefined || addState.isLoading}
          onClick={submit}
        >
          Add
        </Button>
      </div>
    </div>
  );
}

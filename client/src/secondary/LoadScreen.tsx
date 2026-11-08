// File → Load… (#190): the autosaves and manual saves of the running campaign,
// newest first. GET /saves lists them; loading one (POST /saves/{id}/load) asks
// first, since what was played since the last save is lost. The new campaign
// then arrives as events, as with File → Open.
import { commandErrorMessage } from "../api/commands";
import {
  Save,
  Saves,
  useListSavesQuery,
  useLoadSaveMutation,
} from "../api/liberationApi";
import { Button, Modal, ModalClose, Table, useToast } from "../ui";
import type { TableColumn } from "../ui";
import { QueryBody, ScreenFrame } from "./ScreenFrame";
import styles from "./Secondary.module.css";
import { useState } from "react";

const KIND_LABELS: Record<Save["kind"], string> = {
  turn: "Start of turn",
  takeoff: "Before take off",
  manual: "Saved by you",
};

function savedAt(iso: string): string {
  return iso.replace("T", " ").slice(0, 16);
}

function describe(save: Save): string {
  return `${KIND_LABELS[save.kind]}, turn ${save.turn} (${save.game_date})`;
}

function SavesTable({
  saves,
  onLoad,
  busy,
}: {
  saves: Saves;
  onLoad: (save: Save) => void;
  /** A load is under way: no second one. */
  busy: boolean;
}) {
  const columns: TableColumn<Save>[] = [
    { key: "turn", header: "Turn", cell: (s) => s.turn, align: "end" },
    { key: "date", header: "Date in game", cell: (s) => s.game_date },
    { key: "kind", header: "Save", cell: (s) => KIND_LABELS[s.kind] },
    {
      key: "saved",
      header: "Saved at",
      cell: (s) => savedAt(s.saved_at),
      mono: true,
    },
    { key: "file", header: "File", cell: (s) => s.file_name, mono: true },
    {
      key: "load",
      header: "",
      align: "end",
      cell: (s) => (
        <Button disabled={busy} onClick={() => onLoad(s)}>
          Load
        </Button>
      ),
    },
  ];
  return (
    <>
      <p className={styles.help}>
        Each turn is autosaved at its start and before take off. Choose how many
        turns are kept in File → Preferences.
      </p>
      <Table
        caption="Saves"
        hideCaption
        columns={columns}
        rows={saves.saves}
        rowKey={(s) => s.id}
        emptyText="No saves yet: the first autosave comes with the next turn."
      />
    </>
  );
}

export function LoadScreen() {
  const toast = useToast();
  const query = useListSavesQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  const [loadSave, { isLoading }] = useLoadSaveMutation();
  const [pending, setPending] = useState<Save | null>(null);

  const previous =
    query.data?.saves.find((s) => s.id === query.data?.previous_turn_id) ??
    null;

  const confirm = async () => {
    if (pending === null) return;
    const save = pending;
    setPending(null);
    const result = await loadSave({ saveId: save.id });
    if ("error" in result) {
      toast({
        title: "Could not load the save",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
      return;
    }
    toast({ title: "Campaign loaded", description: describe(save) });
  };

  return (
    <ScreenFrame
      title="Load"
      actions={
        <Button
          disabled={previous === null || isLoading}
          onClick={() => setPending(previous)}
        >
          Restore the previous turn
        </Button>
      }
    >
      <QueryBody query={query} name="saves">
        {(saves) => (
          <SavesTable saves={saves} onLoad={setPending} busy={isLoading} />
        )}
      </QueryBody>
      <Modal
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title="Load this save?"
        description={
          pending === null
            ? undefined
            : `${describe(pending)}. Progress since your last save is lost.`
        }
        footer={
          <>
            <ModalClose asChild>
              <Button>Cancel</Button>
            </ModalClose>
            <Button variant="danger" onClick={confirm}>
              Load this save
            </Button>
          </>
        }
      />
    </ScreenFrame>
  );
}

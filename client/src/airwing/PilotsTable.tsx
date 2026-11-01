// Pilot roster of the air wing screen (WEB-03): one squadron's on its sheet, or
// every squadron's in the Pilots view. The player box and the buttons are locked
// by the refusals the engine sends with each pilot.
import {
  AirWingPilot,
  AirWingSquadron,
  useUpdatePilotMutation,
} from "../api/liberationApi";
import { PATHS } from "../shell/paths";
import { Button, Modal, ModalClose, Table, TableColumn } from "../ui";
import styles from "./AirWing.module.css";
import { useCommand } from "./useCommand";
import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

interface Row {
  pilot: AirWingPilot;
  squadron: AirWingSquadron;
}

export interface NameModalProps {
  title: string;
  label: string;
  submit: string;
  initial?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (name: string) => Promise<boolean>;
}

/** Asks for a pilot's name; stays open when the server refuses it. */
export function NameModal(props: NameModalProps) {
  const [name, setName] = useState(props.initial ?? "");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    const done = await props.onSubmit(name);
    setBusy(false);
    if (done) {
      props.onOpenChange(false);
    }
  };
  return (
    <Modal
      title={props.title}
      open={props.open}
      onOpenChange={props.onOpenChange}
    >
      <form className={styles.form} onSubmit={submit}>
        <label className={styles.field}>
          {props.label}
          <input
            className={styles.input}
            value={name}
            autoFocus
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <div className={styles.formActions}>
          <ModalClose asChild>
            <Button type="button">Cancel</Button>
          </ModalClose>
          <Button type="submit" variant="primary" disabled={busy}>
            {props.submit}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function PilotName({ pilot }: { pilot: AirWingPilot }) {
  // Only player pilots have a career (PER-03.4).
  return pilot.player ? (
    <Link
      className={styles.pilotLink}
      to={`${PATHS.career}?pilot=${pilot.id}`}
      aria-label={`Career of ${pilot.name}`}
    >
      {pilot.name}
    </Link>
  ) : (
    <span className={styles.pilotName}>{pilot.name}</span>
  );
}

export interface PilotsTableProps {
  caption: string;
  squadrons: AirWingSquadron[];
  /** Keeps only the living, or only the fallen. */
  filter?: (pilot: AirWingPilot) => boolean;
  showSquadron?: boolean;
  emptyText: string;
}

export function PilotsTable({
  caption,
  squadrons,
  filter,
  showSquadron,
  emptyText,
}: PilotsTableProps) {
  const [update, { isLoading }] = useUpdatePilotMutation();
  const run = useCommand();
  const [renaming, setRenaming] = useState<Row | null>(null);
  const rows: Row[] = squadrons.flatMap((squadron) =>
    squadron.pilots
      .filter((pilot) => filter?.(pilot) ?? true)
      .map((pilot) => ({ pilot, squadron })),
  );

  const change = (row: Row, pilotUpdateJs: object, failure: string) =>
    run(
      update({
        squadronId: row.squadron.id,
        pilotId: row.pilot.id,
        pilotUpdateJs,
      }),
      failure,
    );

  const columns: TableColumn<Row>[] = [
    {
      key: "pilot",
      header: "Pilot",
      cell: ({ pilot }) => <PilotName pilot={pilot} />,
      sortValue: ({ pilot }) => pilot.name,
    },
    ...(showSquadron
      ? [
          {
            key: "squadron",
            header: "Squadron",
            cell: ({ squadron }: Row) => squadron.name,
            sortValue: ({ squadron }: Row) => squadron.name,
          },
          {
            key: "base",
            header: "Base",
            cell: ({ squadron }: Row) => squadron.base,
            sortValue: ({ squadron }: Row) => squadron.base,
          },
        ]
      : []),
    {
      key: "status",
      header: "Status",
      cell: ({ pilot }) => (
        <span className={styles.status} data-status={pilot.status}>
          ● {pilot.status_text}
        </span>
      ),
      sortValue: ({ pilot }) => pilot.status_text,
    },
    {
      key: "player",
      header: "Player",
      cell: (row) => (
        <input
          type="checkbox"
          aria-label={`Player pilot: ${row.pilot.name}`}
          title={row.pilot.player_refusal ?? undefined}
          checked={row.pilot.player}
          disabled={isLoading || row.pilot.player_refusal != null}
          onChange={(event) =>
            change(
              row,
              { player: event.target.checked },
              "Could not change the pilot",
            )
          }
        />
      ),
    },
    {
      key: "skill",
      header: "Skill",
      cell: ({ pilot }) => pilot.skill,
      sortValue: ({ pilot }) => pilot.skill,
    },
    {
      key: "sorties",
      header: "Sorties",
      cell: ({ pilot }) => pilot.sorties,
      align: "end",
      mono: true,
      sortValue: ({ pilot }) => pilot.sorties,
    },
    {
      key: "kills",
      header: "Kills",
      cell: ({ pilot }) => pilot.kills,
      align: "end",
      mono: true,
      sortValue: ({ pilot }) => pilot.kills,
    },
    { key: "note", header: "Notes", cell: ({ pilot }) => pilot.note },
    {
      key: "actions",
      header: "",
      align: "end",
      cell: (row) =>
        row.pilot.alive && (
          <span className={styles.rowActions}>
            <Button
              aria-label={`Rename ${row.pilot.name}`}
              onClick={() => setRenaming(row)}
            >
              Rename
            </Button>
            <Button
              title={row.pilot.leave_refusal ?? undefined}
              disabled={isLoading || row.pilot.leave_refusal != null}
              aria-label={
                row.pilot.on_leave
                  ? `Return ${row.pilot.name} from leave`
                  : `Send ${row.pilot.name} on leave`
              }
              onClick={() =>
                change(
                  row,
                  { on_leave: !row.pilot.on_leave },
                  "Could not change the pilot",
                )
              }
            >
              {row.pilot.on_leave ? "Return" : "Leave"}
            </Button>
          </span>
        ),
    },
  ];

  return (
    <>
      <Table
        caption={caption}
        hideCaption
        columns={columns}
        rows={rows}
        rowKey={({ pilot }) => pilot.id}
        emptyText={emptyText}
      />
      {renaming && (
        <NameModal
          key={renaming.pilot.id}
          title={`Rename ${renaming.pilot.name}`}
          label="New name"
          submit="Rename"
          initial={renaming.pilot.name}
          open
          onOpenChange={(open) => !open && setRenaming(null)}
          onSubmit={(name) =>
            change(renaming, { name }, "Could not rename the pilot")
          }
        />
      )}
    </>
  );
}

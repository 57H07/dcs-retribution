// Campaign notes (WEB-08.2): the Qt notes window. GET /notes fills the editor,
// Save sends PUT /notes; the notes are saved with the campaign and printed as a
// kneeboard page.
import { commandErrorMessage } from "../api/commands";
import { useGetNotesQuery, useSetNotesMutation } from "../api/liberationApi";
import { Button, useToast } from "../ui";
import { QueryBody, ScreenFrame } from "./ScreenFrame";
import styles from "./Secondary.module.css";
import { useState } from "react";

function NotesEditor({ saved }: { saved: string }) {
  const toast = useToast();
  const [text, setText] = useState(saved);
  const [lastSaved, setLastSaved] = useState(saved);
  const [save, { isLoading }] = useSetNotesMutation();
  const dirty = text !== lastSaved;

  const onSave = async () => {
    const result = await save({ notesJs: { text } });
    if (!("data" in result)) {
      toast({
        title: "Could not save the notes",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
      return;
    }
    setLastSaved(result.data.text);
    toast({ title: "Notes saved", tone: "success" });
  };

  return (
    <>
      <p className={styles.help}>
        Saved notes are available as a page in your kneeboard, and saved with
        the campaign.
      </p>
      <textarea
        className={styles.textarea}
        aria-label="Notes"
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <div className={styles.actions}>
        <Button variant="ghost" onClick={() => setText("")} disabled={!text}>
          Clear
        </Button>
        <Button
          variant="primary"
          onClick={onSave}
          disabled={!dirty || isLoading}
        >
          {dirty ? "Save" : "Saved"}
        </Button>
      </div>
    </>
  );
}

export function NotesScreen() {
  const query = useGetNotesQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  return (
    <ScreenFrame title="Notes">
      {/* The editor starts from its first value: wait for fresh notes, not the
          ones cached before the last save. */}
      <QueryBody
        query={{ ...query, isLoading: query.isFetching }}
        name="notes"
      >
        {(notes) => <NotesEditor saved={notes.text} />}
      </QueryBody>
    </ScreenFrame>
  );
}

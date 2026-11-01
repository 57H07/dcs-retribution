// Info panel (WEB-08.2): the campaign messages of the Qt QInfoPanel (captures,
// budget, losses...), newest first, from GET /informations.
import { InformationJs, useListInformationsQuery } from "../api/liberationApi";
import { Table, TableColumn } from "../ui";
import { QueryBody, ScreenFrame } from "./ScreenFrame";

function formatTimestamp(value?: string | null): string {
  // ISO date and time to the minute, as the Qt list showed it.
  return value != null ? value.slice(0, 16).replace("T", " ") : "";
}

const COLUMNS: TableColumn<InformationJs>[] = [
  {
    key: "turn",
    header: "Turn",
    cell: (i) => i.turn,
    align: "end",
    mono: true,
    sortValue: (i) => i.turn,
  },
  { key: "title", header: "Event", cell: (i) => i.title },
  { key: "text", header: "Details", cell: (i) => i.text },
  {
    key: "time",
    header: "Logged",
    cell: (i) => formatTimestamp(i.timestamp),
    mono: true,
  },
];

export function InfoPanelScreen() {
  const query = useListInformationsQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  return (
    <ScreenFrame title="Info panel">
      <QueryBody query={query} name="messages">
        {(informations) => (
          <Table
            caption="Campaign messages"
            hideCaption
            columns={COLUMNS}
            rows={informations}
            rowKey={(i) => `${i.turn}-${i.timestamp}-${i.title}-${i.text}`}
            emptyText="No message yet."
          />
        )}
      </QueryBody>
    </ScreenFrame>
  );
}

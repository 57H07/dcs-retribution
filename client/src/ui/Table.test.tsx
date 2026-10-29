import { Table, TableColumn } from "./Table";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

interface Row {
  id: string;
  name: string;
  pilots: number;
}

const ROWS: Row[] = [
  { id: "a", name: "Bravo", pilots: 4 },
  { id: "b", name: "Alpha", pilots: 12 },
  { id: "c", name: "Charlie", pilots: 9 },
];

const COLUMNS: TableColumn<Row>[] = [
  {
    key: "name",
    header: "Squadron",
    cell: (r) => r.name,
    sortValue: (r) => r.name,
  },
  {
    key: "pilots",
    header: "Pilots",
    cell: (r) => r.pilots,
    align: "end",
    mono: true,
    sortValue: (r) => r.pilots,
  },
];

function names(): string[] {
  const [, ...bodyRows] = screen.getAllByRole("row");
  return bodyRows.map(
    (row) => within(row).getAllByRole("cell")[0].textContent ?? "",
  );
}

describe("Table", () => {
  it("renders a captioned table with column headers", () => {
    render(
      <Table
        caption="Squadrons"
        columns={COLUMNS}
        rows={ROWS}
        rowKey={(r) => r.id}
      />,
    );
    expect(
      screen.getByRole("table", { name: "Squadrons" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader")).toHaveLength(2);
    expect(names()).toEqual(["Bravo", "Alpha", "Charlie"]);
  });

  it("sorts by a column and announces the order", async () => {
    render(
      <Table
        caption="Squadrons"
        columns={COLUMNS}
        rows={ROWS}
        rowKey={(r) => r.id}
      />,
    );
    const pilots = screen.getByRole("button", { name: /Pilots/ });
    await userEvent.click(pilots);
    expect(names()).toEqual(["Bravo", "Charlie", "Alpha"]);
    expect(
      screen.getByRole("columnheader", { name: /Pilots/ }),
    ).toHaveAttribute("aria-sort", "ascending");
    await userEvent.click(pilots);
    expect(names()).toEqual(["Alpha", "Charlie", "Bravo"]);
    expect(
      screen.getByRole("columnheader", { name: /Pilots/ }),
    ).toHaveAttribute("aria-sort", "descending");
  });

  it("activates rows with the mouse and the keyboard and marks the selection", async () => {
    const onRowClick = vi.fn();
    render(
      <Table
        caption="Squadrons"
        columns={COLUMNS}
        rows={ROWS}
        rowKey={(r) => r.id}
        onRowClick={onRowClick}
        selectedKey="b"
      />,
    );
    const [, first, second] = screen.getAllByRole("row");
    expect(second).toHaveAttribute("aria-current", "true");
    expect(first).not.toHaveAttribute("aria-current");
    await userEvent.click(first);
    expect(onRowClick).toHaveBeenLastCalledWith(ROWS[0]);
    second.focus();
    await userEvent.keyboard("{Enter}");
    expect(onRowClick).toHaveBeenLastCalledWith(ROWS[1]);
  });

  it("shows the empty text without rows", () => {
    render(
      <Table
        caption="Squadrons"
        columns={COLUMNS}
        rows={[]}
        rowKey={(r) => r.id}
        emptyText="None here"
      />,
    );
    expect(screen.getByRole("cell", { name: "None here" })).toBeInTheDocument();
  });
});

import styles from "./Table.module.css";
import { cx } from "./cx";
import { KeyboardEvent, ReactNode, useMemo, useState } from "react";

// Plain semantic table (Radix has no table primitive). Sorting is a display
// convenience over rows the engine already sent: no game rule here.

export interface TableColumn<Row> {
  key: string;
  header: string;
  cell: (row: Row) => ReactNode;
  align?: "start" | "end";
  /** Figures, times, coordinates. */
  mono?: boolean;
  /** Makes the header a sort button. */
  sortValue?: (row: Row) => string | number;
}

export interface TableProps<Row> {
  caption: string;
  /** Keeps the caption for assistive technology only. */
  hideCaption?: boolean;
  columns: TableColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  /** Makes rows focusable and activable with click, Enter or Space. */
  onRowClick?: (row: Row) => void;
  selectedKey?: string;
  emptyText?: string;
  className?: string;
}

type Sort = { key: string; direction: "ascending" | "descending" };

export function Table<Row>({
  caption,
  hideCaption,
  columns,
  rows,
  rowKey,
  onRowClick,
  selectedKey,
  emptyText = "Nothing to show",
  className,
}: TableProps<Row>) {
  const [sort, setSort] = useState<Sort | null>(null);

  const sortedRows = useMemo(() => {
    const column = columns.find((c) => c.key === sort?.key);
    if (!sort || !column?.sortValue) {
      return rows;
    }
    const value = column.sortValue;
    const sign = sort.direction === "ascending" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const left = value(a);
      const right = value(b);
      if (typeof left === "number" && typeof right === "number") {
        return (left - right) * sign;
      }
      return String(left).localeCompare(String(right)) * sign;
    });
  }, [columns, rows, sort]);

  const toggleSort = (key: string) =>
    setSort((current) =>
      current?.key === key && current.direction === "ascending"
        ? { key, direction: "descending" }
        : { key, direction: "ascending" },
    );

  const onRowKeyDown = (event: KeyboardEvent, row: Row) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onRowClick?.(row);
    }
  };

  return (
    <div className={cx(styles.wrapper, className)}>
      <table className={styles.table}>
        <caption
          className={hideCaption ? "ui-visually-hidden" : styles.caption}
        >
          {caption}
        </caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={cx(styles.th, column.align === "end" && styles.end)}
                aria-sort={
                  sort?.key === column.key ? sort.direction : undefined
                }
              >
                {column.sortValue ? (
                  <button
                    type="button"
                    className={styles.sort}
                    onClick={() => toggleSort(column.key)}
                  >
                    {column.header}
                    <span aria-hidden="true">
                      {sort?.key !== column.key
                        ? "↕"
                        : sort.direction === "ascending"
                          ? "▲"
                          : "▼"}
                    </span>
                  </button>
                ) : (
                  column.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedRows.length === 0 && (
            <tr>
              <td className={styles.empty} colSpan={columns.length}>
                {emptyText}
              </td>
            </tr>
          )}
          {sortedRows.map((row) => {
            const key = rowKey(row);
            return (
              <tr
                key={key}
                className={styles.row}
                data-clickable={onRowClick ? "" : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                // aria-selected belongs to grids: a plain table marks the
                // selected row as current.
                aria-current={selectedKey === key ? "true" : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={
                  onRowClick ? (event) => onRowKeyDown(event, row) : undefined
                }
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cx(
                      styles.td,
                      column.align === "end" && styles.end,
                      column.mono && styles.mono,
                    )}
                  >
                    {column.cell(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

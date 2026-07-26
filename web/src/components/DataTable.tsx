import { useMemo, useState } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => string | number;
  sortValue?: (row: T) => string | number;
}

interface Props<T> {
  caption: string;
  columns: Column<T>[];
  rows: T[];
  emptyMessage: string;
  filterPlaceholder?: string;
  getRowKey: (row: T, index: number) => string;
}

export default function DataTable<T>({ caption, columns, rows, emptyMessage, filterPlaceholder, getRowKey }: Props<T>) {
  const [filter, setFilter] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<1 | -1>(1);

  const filtered = useMemo(() => {
    if (!filter.trim()) return rows;
    const needle = filter.toLowerCase();
    return rows.filter((row) => columns.some((c) => String(c.render(row)).toLowerCase().includes(needle)));
  }, [rows, filter, columns]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    const col = columns.find((c) => c.key === sortKey);
    if (!col) return filtered;
    const getVal = col.sortValue ?? col.render;
    return [...filtered].sort((a, b) => {
      const av = getVal(a);
      const bv = getVal(b);
      if (av < bv) return -1 * sortDir;
      if (av > bv) return 1 * sortDir;
      return 0;
    });
  }, [filtered, sortKey, sortDir, columns]);

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 1 ? -1 : 1));
    } else {
      setSortKey(key);
      setSortDir(1);
    }
  };

  return (
    <div className="data-table">
      <div className="data-table__controls">
        <label>
          Filter
          <input
            type="search"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder={filterPlaceholder ?? "Filter rows…"}
          />
        </label>
        <span aria-live="polite">{sorted.length.toLocaleString()} rows</span>
      </div>
      <div className="table-scroll">
        <table>
          <caption className="visually-hidden">{caption}</caption>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} scope="col">
                  <button
                    type="button"
                    className="sort-button"
                    onClick={() => toggleSort(c.key)}
                    aria-label={`Sort by ${c.header}`}
                  >
                    {c.header}
                    {sortKey === c.key ? (sortDir === 1 ? " ▲" : " ▼") : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="empty-state">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              sorted.map((row, i) => (
                <tr key={getRowKey(row, i)}>
                  {columns.map((c) => (
                    <td key={c.key}>{c.render(row)}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

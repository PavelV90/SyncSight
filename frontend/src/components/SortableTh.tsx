import type { SortDir } from "../lib/useSort";

type Props<K extends string> = {
  sortKey: K;
  label: string;
  active: K;
  dir: SortDir;
  onSort: (key: K) => void;
  help?: string; // definition for ambiguous headers
  className?: string;
};

/** Column header that sorts the table; announces the sort state via aria-sort. */
export function SortableTh<K extends string>({
  sortKey,
  label,
  active,
  dir,
  onSort,
  help,
  className,
}: Props<K>) {
  const isActive = sortKey === active;
  const ariaSort = isActive ? (dir === "asc" ? "ascending" : "descending") : "none";
  return (
    <th scope="col" aria-sort={ariaSort} title={help} className={className}>
      <button type="button" className="th-sort" onClick={() => onSort(sortKey)}>
        {label}
        <span aria-hidden="true" className="sort-arrow">
          {isActive ? (dir === "asc" ? " ▲" : " ▼") : " ↕"}
        </span>
      </button>
      {help && <span className="sr-only">: {help}</span>}
    </th>
  );
}

/** Plain header with an optional definition (tooltip + screen-reader text). */
export function Th({
  label,
  help,
  className,
}: {
  label: string;
  help?: string;
  className?: string;
}) {
  return (
    <th scope="col" title={help} className={className}>
      {label}
      {help && <span className="sr-only">: {help}</span>}
    </th>
  );
}

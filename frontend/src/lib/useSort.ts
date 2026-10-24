import { useMemo, useState } from "react";

export type SortDir = "asc" | "desc";
type Value = string | number | null | undefined;

const collator = new Intl.Collator("de-CH", { numeric: true, sensitivity: "base" });

/** Client-side sorting of already loaded rows; missing values always sort last. */
export function useSort<T, A extends Record<string, (row: T) => Value>>(
  rows: T[],
  accessors: A,
  initial: { key: keyof A & string; dir: SortDir },
) {
  type Key = keyof A & string;
  const [sort, setSort] = useState<{ key: Key; dir: SortDir }>(initial);
  const sorted = useMemo(() => {
    const get = accessors[sort.key];
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = get(a);
      const y = get(b);
      if (x === null || x === undefined || x === "") return y === null || y === undefined ? 0 : 1;
      if (y === null || y === undefined || y === "") return -1;
      const order =
        typeof x === "number" && typeof y === "number" ? x - y : collator.compare(`${x}`, `${y}`);
      return order * factor;
    });
    // accessors are recreated each render but only read rows; rows and sort drive the result
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, sort]);
  const toggle = (key: Key) =>
    setSort((s) => ({
      key,
      dir:
        s.key === key
          ? s.dir === "asc"
            ? "desc"
            : "asc"
          : key === initial.key
            ? initial.dir
            : "asc",
    }));
  const reset = () => setSort(initial);
  return { sorted, sortKey: sort.key, sortDir: sort.dir, toggle, reset };
}

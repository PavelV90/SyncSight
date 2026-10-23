import { useId, useState } from "react";

import { BASEL_REGION, CANTON_CODES, CANTONS } from "../lib/labels";

type Props = {
  label: string;
  selected: string[];
  onChange: (cantons: string[]) => void;
  emptyLabel: string; // shown when nothing is selected, e.g. "All cantons"
};

const NAMES = Object.fromEntries(CANTONS);

/** Multi-select of the 26 cantons: removable chips plus a searchable checklist. */
export function CantonPicker({ label, selected, onChange, emptyLabel }: Props) {
  const [filter, setFilter] = useState("");
  const id = useId();
  const term = filter.trim().toLowerCase();
  const visible = CANTONS.filter(
    ([code, name]) =>
      !term || code.toLowerCase().includes(term) || name.toLowerCase().includes(term),
  );
  const toggle = (code: string) =>
    onChange(
      selected.includes(code)
        ? selected.filter((c) => c !== code)
        : CANTON_CODES.filter((c) => c === code || selected.includes(c)),
    );

  return (
    <fieldset className="canton-picker">
      <legend>{label}</legend>
      <div className="chips">
        {selected.length === 0 && <span className="muted">{emptyLabel}</span>}
        {selected.map((code) => (
          <span key={code} className="chip" title={NAMES[code]}>
            {code}
            <button
              type="button"
              className="chip-remove"
              aria-label={`Remove ${NAMES[code]}`}
              onClick={() => toggle(code)}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <details className="picker">
        <summary>Choose cantons</summary>
        <div className="picker-panel">
          <label htmlFor={`${id}-filter`} className="sr-only">
            Filter cantons
          </label>
          <input
            id={`${id}-filter`}
            type="search"
            placeholder="Filter cantons"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <div className="picker-actions">
            <button type="button" onClick={() => onChange(BASEL_REGION)}>
              Basel region
            </button>
            <button type="button" onClick={() => onChange(CANTON_CODES)}>
              All
            </button>
            <button type="button" onClick={() => onChange([])}>
              Clear
            </button>
          </div>
          <ul className="picker-list">
            {visible.map(([code, name]) => (
              <li key={code}>
                <label>
                  <input
                    type="checkbox"
                    checked={selected.includes(code)}
                    onChange={() => toggle(code)}
                  />{" "}
                  {code} – {name}
                </label>
              </li>
            ))}
          </ul>
        </div>
      </details>
    </fieldset>
  );
}

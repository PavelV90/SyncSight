import { type FormEvent, useMemo, useState } from "react";

import { type Company, getJson } from "../api";
import { Chips } from "../components/Chips";
import { ResultBar } from "../components/ResultBar";
import { SearchSyntaxHint } from "../components/SearchSyntaxHint";
import { SortableTh } from "../components/SortableTh";
import { Status } from "../components/Status";
import { toCsv } from "../lib/csv";
import { CANTONS } from "../lib/labels";
import type { ListViewProps } from "../lib/navigation";
import { useQuery } from "../lib/useQuery";
import { useSort } from "../lib/useSort";

const LIMIT = 100;

/** Find a company by name, purpose keywords or UID (entry point for use case 3). */
export function CompanySearch({ onOpenCompany, openedUid }: ListViewProps) {
  const [q, setQ] = useState("");
  const [canton, setCanton] = useState("");
  const [tooShort, setTooShort] = useState(false);
  const [{ data, meta, loading, error }, run, retry] = useQuery<
    Company[],
    { q: string; canton: string }
  >();
  const submitted = meta ?? { q: "", canton: "" };

  function submit(event: FormEvent) {
    event.preventDefault();
    if (q.trim().length < 2) {
      setTooShort(true);
      return;
    }
    setTooShort(false);
    run(
      (signal) =>
        getJson<Company[]>(
          "/api/companies",
          { q, limit: LIMIT, ...(canton ? { canton } : {}) },
          signal,
        ),
      { q, canton },
    );
  }

  const companies = useMemo(() => data ?? [], [data]);
  const {
    sorted,
    sortKey,
    sortDir,
    toggle,
    reset: resetSort,
  } = useSort(
    companies,
    {
      relevance: (c: Company) => companies.indexOf(c),
      name: (c: Company) => c.name,
      legal: (c: Company) => c.legal_form,
      seat: (c: Company) => c.seat,
      canton: (c: Company) => c.canton,
      status: (c: Company) => c.status,
    },
    { key: "relevance", dir: "asc" },
  );
  const where = submitted.canton ? ` in ${submitted.canton}` : "";
  const order = sortKey === "relevance" ? "best match first" : "re-sorted";
  const summary =
    companies.length >= LIMIT
      ? `First ${LIMIT} matches for '${submitted.q}'${where} (${order}). Refine to see others.`
      : `${companies.length} companies for '${submitted.q}'${where} (${order})`;

  return (
    <section aria-labelledby="company-heading">
      <h2 id="company-heading">Company check</h2>
      <form onSubmit={submit} className="filters" noValidate>
        <div className="field">
          <label htmlFor="company-q">Company name, keywords or UID</label>
          <input
            id="company-q"
            value={q}
            minLength={2}
            placeholder="e.g. Lonza or CHE-105.815.381"
            aria-invalid={tooShort ? true : undefined}
            aria-describedby="company-syntax company-error"
            onChange={(e) => setQ(e.target.value)}
          />
          <SearchSyntaxHint id="company-syntax" />
          {tooShort && (
            <span id="company-error" role="alert" className="field-error">
              Enter at least 2 characters.
            </span>
          )}
        </div>
        <label>
          Canton
          <select value={canton} onChange={(e) => setCanton(e.target.value)}>
            <option value="">All cantons</option>
            {CANTONS.map(([code, name]) => (
              <option key={code} value={code}>
                {code} – {name}
              </option>
            ))}
          </select>
        </label>
        <div className="form-actions">
          <button type="submit" className="primary" disabled={loading} aria-busy={loading}>
            Search
          </button>
          <button
            type="button"
            onClick={() => {
              setQ("");
              setCanton("");
              setTooShort(false);
            }}
          >
            Reset
          </button>
        </div>
      </form>

      <Status
        loading={loading}
        error={error}
        empty={data !== null && companies.length === 0}
        onRetry={retry}
        emptyText="No company found. Try fewer words or another spelling."
      />
      {sortKey !== "relevance" && companies.length > 0 && (
        <button type="button" className="link small" onClick={resetSort}>
          Back to best-match order
        </button>
      )}
      {
        <ResultBar
          summary={data !== null ? summary : ""}
          uids={sorted.map((c) => c.uid)}
          csv={() => ({
            filename: "syncsight-companies.csv",
            content: toCsv(sorted, [
              { header: "Company", value: (c) => c.name },
              { header: "UID", value: (c) => c.uid },
              { header: "Legal form", value: (c) => c.legal_form },
              { header: "Seat", value: (c) => c.seat },
              { header: "Canton", value: (c) => c.canton },
              { header: "Status", value: (c) => c.status },
            ]),
          })}
        />
      }
      {sorted.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Companies</caption>
            <thead>
              <tr>
                <SortableTh
                  sortKey="name"
                  label="Company"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                />
                <th scope="col">UID</th>
                <SortableTh
                  sortKey="legal"
                  label="Legal form"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                />
                <SortableTh
                  sortKey="seat"
                  label="Seat"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                />
                <SortableTh
                  sortKey="canton"
                  label="Canton"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                />
                <SortableTh
                  sortKey="status"
                  label="Status"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                />
              </tr>
            </thead>
            <tbody>
              {sorted.map((c) => (
                <tr key={c.uid} className={c.uid === openedUid ? "row--opened" : undefined}>
                  <td>
                    <button
                      type="button"
                      className="link"
                      data-uid={c.uid}
                      onClick={() => onOpenCompany(c.uid)}
                    >
                      {c.name}
                    </button>
                  </td>
                  <td className="nowrap muted">{c.uid}</td>
                  <td>{c.legal_form}</td>
                  <td>{c.seat}</td>
                  <td>{c.canton}</td>
                  <td>
                    <Chips items={c.status ? [c.status] : []} warn={(s) => s !== "active"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

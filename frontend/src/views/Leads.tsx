import { type FormEvent, useEffect, useMemo, useState } from "react";

import { formatDate, formatRelative, getJson, type Lead } from "../api";
import { CantonPicker } from "../components/CantonPicker";
import { Chips } from "../components/Chips";
import { Clamp } from "../components/Clamp";
import { PeriodSelect, periodLabel } from "../components/PeriodSelect";
import { ResultBar } from "../components/ResultBar";
import { SortableTh, Th } from "../components/SortableTh";
import { Status } from "../components/Status";
import { toCsv } from "../lib/csv";
import {
  ACTIVITIES,
  BASEL_REGION,
  CANTON_CODES,
  CHANGES,
  changeLabel,
  visibleChanges,
  WARNINGS,
} from "../lib/labels";
import type { ListViewProps } from "../lib/navigation";
import { useQuery } from "../lib/useQuery";
import { useSort } from "../lib/useSort";

type Filters = { cantons: string[]; days: number; activities: number[]; changes: string[] };
const DEFAULTS: Filters = {
  cantons: BASEL_REGION,
  days: 90,
  activities: [1],
  changes: ["board", "management"],
};
const LEAD_CHANGES = CHANGES.filter(([key]) => key !== "other");
const activityName = (code: number) => ACTIVITIES.find(([c]) => c === code)?.[1] ?? String(code);
const leadChanges = (lead: Lead) =>
  visibleChanges([...new Set(lead.notices.flatMap((n) => n.changes))]);

/** Use case 1: licensed pharma companies with recent register changes (default: board or management). */
export function Leads({ onOpenCompany, openedUid }: ListViewProps) {
  const [filters, setFilters] = useState(DEFAULTS);
  const [formError, setFormError] = useState<string | null>(null);
  const [{ data, meta, loading, error }, run, retry] = useQuery<Lead[], Filters>();
  const submitted = meta ?? DEFAULTS;

  const load = (f: Filters) =>
    run(
      (signal) =>
        getJson<Lead[]>(
          "/api/leads",
          {
            // always explicit: the API falls back to BS, BL, AG when no canton is sent
            cantons: f.cantons.length ? f.cantons : CANTON_CODES,
            days: f.days,
            activity: f.activities,
            changes: f.changes,
          },
          signal,
        ),
      f,
    );
  const search = load;
  useEffect(() => load(DEFAULTS), []); // eslint-disable-line react-hooks/exhaustive-deps

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!filters.activities.length || !filters.changes.length) {
      setFormError("Choose at least one activity and one change type.");
      return;
    }
    setFormError(null);
    search(filters);
  }

  function reset() {
    setFilters(DEFAULTS);
    setFormError(null);
    search(DEFAULTS);
  }

  const toggleIn = <T,>(list: T[], item: T) =>
    list.includes(item) ? list.filter((x) => x !== item) : [...list, item];

  const leads = useMemo(() => data ?? [], [data]);
  const { sorted, sortKey, sortDir, toggle } = useSort(
    leads,
    { company: (l: Lead) => l.company.name, last: (l: Lead) => l.last_change },
    { key: "last", dir: "desc" },
  );
  const describe = (f: Filters) =>
    `${f.activities.map(activityName).join(" or ")} licence holders with ` +
    `${f.changes.map(changeLabel).join(" or ").toLowerCase()} changes`;
  const summary =
    `${leads.length} companies · ${submitted.cantons.length ? submitted.cantons.join(", ") : "all cantons"} · ` +
    `${periodLabel(submitted.days)} · ${describe(submitted)}`;

  return (
    <section aria-labelledby="leads-heading">
      <h2 id="leads-heading">Leads</h2>
      <p className="hint">{describe(filters)} at licence sites in the chosen cantons.</p>
      <form onSubmit={submit} className="filters" noValidate>
        <CantonPicker
          label="Licence sites in"
          selected={filters.cantons}
          onChange={(cantons) => setFilters({ ...filters, cantons })}
          emptyLabel="All cantons"
        />
        <PeriodSelect
          value={filters.days}
          onChange={(days) => setFilters({ ...filters, days })}
          options={[30, 90, 182, 365, 730]}
        />
        <fieldset className="checks">
          <legend>Licence activity</legend>
          {ACTIVITIES.map(([code, name]) => (
            <label key={code}>
              <input
                type="checkbox"
                checked={filters.activities.includes(code)}
                onChange={() =>
                  setFilters({ ...filters, activities: toggleIn(filters.activities, code) })
                }
              />{" "}
              {name}
            </label>
          ))}
        </fieldset>
        <fieldset className="checks checks--2">
          <legend>Register change</legend>
          {LEAD_CHANGES.map(([key, name]) => (
            <label key={key}>
              <input
                type="checkbox"
                checked={filters.changes.includes(key)}
                onChange={() => setFilters({ ...filters, changes: toggleIn(filters.changes, key) })}
              />{" "}
              {name}
            </label>
          ))}
        </fieldset>
        <div className="form-actions">
          <button type="submit" className="primary" disabled={loading} aria-busy={loading}>
            Find leads
          </button>
          <button type="button" onClick={reset}>
            Reset
          </button>
          {formError && (
            <span role="alert" className="field-error">
              {formError}
            </span>
          )}
        </div>
      </form>

      <Status
        loading={loading}
        error={error}
        empty={data !== null && leads.length === 0}
        onRetry={retry}
        emptyText="No company matches these filters."
      />
      {data !== null && (
        <ResultBar
          summary={summary}
          uids={sorted.map((l) => l.company.uid)}
          csv={() => ({
            filename: "syncsight-leads.csv",
            content: toCsv(sorted, [
              { header: "Company", value: (l) => l.company.name },
              { header: "UID", value: (l) => l.company.uid },
              { header: "Seat", value: (l) => l.company.seat },
              { header: "Status", value: (l) => l.company.status },
              { header: "Licence sites in", value: (l) => l.site_cantons.join(", ") },
              { header: "Activities", value: (l) => l.activities.join(", ") },
              { header: "Last change", value: (l) => l.last_change },
              { header: "Changes", value: (l) => leadChanges(l).map(changeLabel).join(", ") },
              { header: "SHAB notices", value: (l) => l.notices.map((n) => n.url).join(" ") },
            ]),
          })}
        />
      )}
      {sorted.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Leads</caption>
            <thead>
              <tr>
                <SortableTh
                  sortKey="company"
                  label="Company"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                />
                <Th
                  label="Licence sites in"
                  help="Cantons of the company's Swissmedic licence sites; may differ from the registered seat"
                />
                <Th label="Activities" />
                <SortableTh
                  sortKey="last"
                  label="Last change"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                  help="Publication date of the newest matching SHAB notice"
                />
                <Th label="Changes" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((lead) => (
                <tr
                  key={lead.company.uid}
                  className={lead.company.uid === openedUid ? "row--opened" : undefined}
                >
                  <td>
                    <button
                      type="button"
                      className="link"
                      data-uid={lead.company.uid}
                      onClick={() =>
                        onOpenCompany(lead.company.uid, {
                          healthOnly: false,
                          noticeId: lead.notices[0]?.id,
                        })
                      }
                    >
                      {lead.company.name}
                    </button>
                    {lead.company.status && lead.company.status !== "active" && (
                      <span className="badge badge--warning">{lead.company.status}</span>
                    )}
                    {lead.company.seat && <div className="muted small">{lead.company.seat}</div>}
                  </td>
                  <td>
                    <Chips items={lead.site_cantons} />
                  </td>
                  <td>{lead.activities.join(", ")}</td>
                  <td className="nowrap">
                    <a href={lead.notices[0]?.url} target="_blank" rel="noreferrer">
                      <time dateTime={lead.last_change}>{formatDate(lead.last_change)}</time>
                    </a>
                    <div className="muted small">{formatRelative(lead.last_change)}</div>
                  </td>
                  <td>
                    <details>
                      <summary>
                        <Chips
                          items={leadChanges(lead)}
                          label={changeLabel}
                          warn={(c) => WARNINGS.has(c)}
                        />{" "}
                        <span className="muted small">
                          {lead.notices.length} notice{lead.notices.length === 1 ? "" : "s"}
                        </span>
                      </summary>
                      <ul className="evidence">
                        {lead.notices.map((n) => (
                          <li key={n.id}>
                            <a href={n.url} target="_blank" rel="noreferrer" className="nowrap">
                              {formatDate(n.publication_date)}
                            </a>{" "}
                            <Chips
                              items={visibleChanges(n.changes)}
                              label={changeLabel}
                              warn={(c) => WARNINGS.has(c)}
                            />
                            <Clamp text={n.text} lines={2} className="notice-text" />
                          </li>
                        ))}
                      </ul>
                    </details>
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

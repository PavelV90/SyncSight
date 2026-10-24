import { type FormEvent, useEffect, useMemo, useState } from "react";

import { daysAgo, formatDate, formatRelative, getJson, type MesLead } from "../api";
import { CantonPicker } from "../components/CantonPicker";
import { EvidenceList } from "../components/EvidenceList";
import { Chips } from "../components/Chips";
import { PeriodSelect, periodLabel } from "../components/PeriodSelect";
import { ResultBar } from "../components/ResultBar";
import { ScoringRules } from "../components/ScoringRules";
import { SortableTh, Th } from "../components/SortableTh";
import { Status } from "../components/Status";
import { toCsv } from "../lib/csv";
import { breakdownText, KINDS, kindLabel } from "../lib/kinds";
import type { ListViewProps } from "../lib/navigation";
import { useQuery } from "../lib/useQuery";
import { useSort } from "../lib/useSort";

const kindsOf = (lead: MesLead) => [...new Set(lead.evidence.map((e) => e.kind))];
const latest = (lead: MesLead) => lead.evidence.find((e) => e.on) ?? null;

type Filters = { days: number; cantons: string[]; minScore: number };
const DEFAULTS: Filters = { days: 730, cantons: [], minScore: 3 };

/** Licensed pharma manufacturers ranked by MES signals, with the evidence behind each score. */
export function MesLeads({ onOpenCompany, openedUid }: ListViewProps) {
  const [filters, setFilters] = useState(DEFAULTS);
  const [mustHave, setMustHave] = useState<string[]>([]);
  const [{ data, meta, loading, error }, run, retry] = useQuery<MesLead[], Filters>();
  const submitted = meta ?? DEFAULTS;

  const load = (f: Filters) =>
    run(
      (signal) =>
        getJson<MesLead[]>(
          "/api/mes-leads",
          {
            months: Math.max(1, Math.round(f.days / 30.44)),
            cantons: f.cantons,
            min_score: f.minScore,
          },
          signal,
        ),
      f,
    );
  const search = load;
  useEffect(() => load(DEFAULTS), []); // eslint-disable-line react-hooks/exhaustive-deps

  function submit(event: FormEvent) {
    event.preventDefault();
    search(filters);
  }

  function reset() {
    setFilters(DEFAULTS);
    setMustHave([]);
    search(DEFAULTS);
  }

  const leads = useMemo(() => data ?? [], [data]);
  const kindCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const lead of leads)
      for (const kind of kindsOf(lead)) counts[kind] = (counts[kind] ?? 0) + 1;
    return counts;
  }, [leads]);
  const filtered = useMemo(
    () => leads.filter((lead) => mustHave.every((kind) => kindsOf(lead).includes(kind))),
    [leads, mustHave],
  );
  const { sorted, sortKey, sortDir, toggle } = useSort(
    filtered,
    {
      score: (l: MesLead) => l.score,
      company: (l: MesLead) => l.company.name,
      latest: (l: MesLead) => latest(l)?.on ?? null,
    },
    { key: "score", dir: "desc" },
  );

  const summary =
    `${mustHave.length ? `${filtered.length} of ` : ""}${leads.length} MES leads · ` +
    `${periodLabel(submitted.days)} · ` +
    `${submitted.cantons.length ? submitted.cantons.join(", ") : "all cantons"} · ` +
    `score ≥ ${submitted.minScore}`;

  return (
    <section aria-labelledby="mes-heading">
      <h2 id="mes-heading">MES leads</h2>
      <p className="hint">
        Swissmedic-licensed manufacturers ranked by signals of MES need: production building
        permits, MES or vendor mentions on their websites and career pages, licence changes, and
        management changes. Open a row's evidence to see why it scores.
      </p>
      <ScoringRules />
      <form onSubmit={submit} className="filters" noValidate>
        <PeriodSelect
          value={filters.days}
          onChange={(days) => setFilters({ ...filters, days })}
          options={[182, 365, 730, 1096, 1826]}
        />
        <CantonPicker
          label="Licence sites in"
          selected={filters.cantons}
          onChange={(cantons) => setFilters({ ...filters, cantons })}
          emptyLabel="All cantons"
        />
        <label>
          Minimum score
          <select
            value={filters.minScore}
            onChange={(e) => setFilters({ ...filters, minScore: Number(e.target.value) })}
          >
            {[1, 3, 5, 8].map((n) => (
              <option key={n} value={n}>
                {n === 1 ? "Any signal (≥ 1)" : `≥ ${n}`}
              </option>
            ))}
          </select>
        </label>
        <div className="form-actions">
          <button type="submit" className="primary" disabled={loading} aria-busy={loading}>
            Rank MES leads
          </button>
          <button type="button" onClick={reset}>
            Reset
          </button>
        </div>
      </form>

      {leads.length > 0 && (
        <div className="kind-filter" role="group" aria-label="Must include signal">
          <span className="muted small">Must include:</span>
          {Object.entries(KINDS).map(([kind, label]) => {
            const pressed = mustHave.includes(kind);
            return (
              <button
                key={kind}
                type="button"
                className="chip chip--toggle"
                aria-pressed={pressed}
                disabled={!kindCounts[kind] && !pressed}
                onClick={() =>
                  setMustHave(pressed ? mustHave.filter((k) => k !== kind) : [...mustHave, kind])
                }
              >
                {label} ({kindCounts[kind] ?? 0})
              </button>
            );
          })}
        </div>
      )}

      <Status
        loading={loading}
        error={error}
        empty={data !== null && filtered.length === 0}
        onRetry={retry}
        emptyText={
          mustHave.length ? "No lead has all selected signals." : "No leads match these filters."
        }
      />
      {data !== null && (
        <ResultBar
          summary={summary}
          uids={sorted.map((l) => l.company.uid)}
          csv={() => ({
            filename: "syncsight-mes-leads.csv",
            content: toCsv(sorted, [
              { header: "Score", value: (l) => l.score },
              { header: "Score breakdown", value: (l) => breakdownText(l.breakdown, l.score) },
              { header: "Company", value: (l) => l.company.name },
              { header: "UID", value: (l) => l.company.uid },
              { header: "Licence sites in", value: (l) => l.site_cantons.join(", ") },
              { header: "Activities", value: (l) => l.activities.join(", ") },
              { header: "MES vendors", value: (l) => l.vendors.join(", ") },
              { header: "Signals", value: (l) => kindsOf(l).map(kindLabel).join(", ") },
              { header: "Latest signal", value: (l) => latest(l)?.on ?? "" },
              {
                header: "Evidence links",
                value: (l) => l.evidence.flatMap((e) => (e.url ? [e.url] : [])).join(" "),
              },
            ]),
          })}
        />
      )}
      {sorted.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">MES leads</caption>
            <thead>
              <tr>
                <SortableTh
                  sortKey="score"
                  label="Score"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                  className="num"
                />
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
                <SortableTh
                  sortKey="latest"
                  label="Latest signal"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                  help="Date and type of the newest dated evidence"
                />
                <Th label="Evidence" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((lead) => {
                const newest = latest(lead);
                return (
                  <tr
                    key={lead.company.uid}
                    className={lead.company.uid === openedUid ? "row--opened" : undefined}
                  >
                    <td className="num">
                      <span className="score" title={breakdownText(lead.breakdown, lead.score)}>
                        {lead.score}
                      </span>
                      <span className="sr-only">: {breakdownText(lead.breakdown, lead.score)}</span>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="link"
                        data-uid={lead.company.uid}
                        onClick={() => onOpenCompany(lead.company.uid)}
                      >
                        {lead.company.name}
                      </button>
                      {lead.vendors.length > 0 && (
                        <span className="badge" title="MES vendors named on the company's website">
                          {lead.vendors.join(", ")}
                        </span>
                      )}
                      <div className="muted small">{lead.activities.join(", ")}</div>
                    </td>
                    <td>
                      <Chips items={lead.site_cantons} />
                    </td>
                    <td className="nowrap">
                      {newest?.on ? (
                        <>
                          <time dateTime={newest.on}>{formatDate(newest.on)}</time>
                          {daysAgo(newest.on) <= 30 && (
                            <span className="badge badge--new">new</span>
                          )}
                          <div className="muted small">
                            {kindLabel(newest.kind)} · {formatRelative(newest.on)}
                          </div>
                        </>
                      ) : (
                        <span className="muted">undated</span>
                      )}
                    </td>
                    <td>
                      <details>
                        <summary>
                          <span className="chips">
                            {lead.breakdown.map((k) => (
                              <span key={k.kind} className="chip">
                                {kindLabel(k.kind)}{" "}
                                <span className="muted">
                                  {k.counted}×{k.points_each}
                                </span>
                              </span>
                            ))}
                          </span>
                        </summary>
                        <EvidenceList evidence={lead.evidence} breakdown={lead.breakdown} />
                      </details>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

import { type FormEvent, useEffect, useMemo, useState } from "react";

import { formatChf, formatDate, getJson, type Target } from "../api";
import { Highlight } from "../components/Highlight";
import { PeriodSelect, periodLabel } from "../components/PeriodSelect";
import { ResultBar } from "../components/ResultBar";
import { SearchSyntaxHint } from "../components/SearchSyntaxHint";
import { SortableTh } from "../components/SortableTh";
import { Status } from "../components/Status";
import { toCsv } from "../lib/csv";
import type { ListViewProps } from "../lib/navigation";
import { useQuery } from "../lib/useQuery";
import { useSort } from "../lib/useSort";

type Filters = { q: string; foundedSince: string; days: number };
const DEFAULTS: Filters = { q: "medtech", foundedSince: "2020-01-01", days: 365 };
const isoDay = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const today = () => isoDay(new Date());
const yearsAgo = (years: number) => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - years);
  return isoDay(d);
};
// capital is in CHF with rappen; round the difference to avoid float artefacts (26833.320000000007)
const increase = (t: Target) => Math.round((t.capital_after - t.capital_before) * 100) / 100;
const increasePct = (t: Target) =>
  t.capital_before ? (increase(t) / t.capital_before) * 100 : null;
const formatIncrease = (t: Target) => {
  const pct = increasePct(t);
  return `+${formatChf(increase(t))}${pct === null ? "" : ` (+${pct < 1 ? pct.toFixed(1) : Math.round(pct)} %)`}`;
};

/** Use case 2: young companies in a field that recently raised capital. */
export function Targets({ onOpenCompany, openedUid }: ListViewProps) {
  const [filters, setFilters] = useState(DEFAULTS);
  const [minIncrease, setMinIncrease] = useState("");
  const [errors, setErrors] = useState<{ q?: string; date?: string }>({});
  const [{ data, meta, loading, error }, run, retry] = useQuery<Target[], Filters>();
  const submitted = meta ?? DEFAULTS;

  const load = (f: Filters) =>
    run(
      (signal) =>
        getJson<Target[]>(
          "/api/targets",
          { q: f.q, founded_since: f.foundedSince, raised_within_days: f.days },
          signal,
        ),
      f,
    );
  const search = load;
  useEffect(() => load(DEFAULTS), []); // eslint-disable-line react-hooks/exhaustive-deps

  function submit(event: FormEvent) {
    event.preventDefault();
    const found: typeof errors = {};
    if (filters.q.trim().length < 2) found.q = "Enter at least 2 characters.";
    if (!filters.foundedSince || filters.foundedSince > today())
      found.date = "Choose a date that is not in the future.";
    setErrors(found);
    if (!found.q && !found.date) search(filters);
  }

  function reset() {
    setFilters(DEFAULTS);
    setMinIncrease("");
    setErrors({});
    search(DEFAULTS);
  }

  const minimum = Number(minIncrease) || 0;
  const targets = useMemo(
    () => (data ?? []).filter((t) => increase(t) >= minimum),
    [data, minimum],
  );
  const { sorted, sortKey, sortDir, toggle } = useSort(
    targets,
    {
      company: (t: Target) => t.company.name,
      founded: (t: Target) => t.founded_on,
      raised: (t: Target) => t.raised_on,
      before: (t: Target) => t.capital_before,
      after: (t: Target) => t.capital_after,
      increase: (t: Target) => increase(t),
    },
    { key: "increase", dir: "desc" },
  );
  const total = data?.length ?? 0;
  const summary =
    `${minimum ? `${targets.length} of ` : ""}${total} companies · '${submitted.q}' · ` +
    `founded since ${formatDate(submitted.foundedSince)} · raised capital ${periodLabel(submitted.days)}`;

  return (
    <section aria-labelledby="targets-heading">
      <h2 id="targets-heading">Investment targets</h2>
      <p className="hint">
        Companies whose purpose matches the keywords, registered since the date, that increased
        their capital in the chosen period.
      </p>
      <form onSubmit={submit} className="filters" noValidate>
        <label>
          Keywords
          <input
            value={filters.q}
            placeholder="e.g. medtech or diagnostics"
            aria-invalid={errors.q ? true : undefined}
            aria-describedby={errors.q ? "targets-q-error targets-syntax" : "targets-syntax"}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
          />
          {errors.q && (
            <span id="targets-q-error" className="field-error">
              {errors.q}
            </span>
          )}
          <SearchSyntaxHint id="targets-syntax" />
        </label>
        <label>
          Founded since
          <input
            type="date"
            required
            max={today()}
            value={filters.foundedSince}
            aria-invalid={errors.date ? true : undefined}
            aria-describedby={errors.date ? "targets-date-error" : undefined}
            onChange={(e) => setFilters({ ...filters, foundedSince: e.target.value })}
          />
          {errors.date && (
            <span id="targets-date-error" className="field-error">
              {errors.date}
            </span>
          )}
          <span className="quick-picks">
            {[3, 5, 10].map((years) => (
              <button
                key={years}
                type="button"
                className="link small"
                onClick={() => setFilters({ ...filters, foundedSince: yearsAgo(years) })}
              >
                last {years} years
              </button>
            ))}
          </span>
        </label>
        <PeriodSelect
          label="Capital raised in"
          value={filters.days}
          onChange={(days) => setFilters({ ...filters, days })}
          options={[90, 182, 365, 730, 1096]}
        />
        <label>
          Min. increase (CHF)
          <input
            type="number"
            inputMode="numeric"
            min={0}
            step={1000}
            value={minIncrease}
            placeholder="any"
            onChange={(e) => setMinIncrease(e.target.value)}
          />
          <span className="hint small">Filters the loaded results</span>
        </label>
        <div className="form-actions">
          <button type="submit" className="primary" disabled={loading} aria-busy={loading}>
            Find targets
          </button>
          <button type="button" onClick={reset}>
            Reset
          </button>
        </div>
      </form>

      <Status
        loading={loading}
        error={error}
        empty={data !== null && targets.length === 0}
        onRetry={retry}
        emptyText="No company matches these filters."
      />
      {data !== null && (
        <ResultBar
          summary={summary}
          uids={sorted.map((t) => t.company.uid)}
          csv={() => ({
            filename: "syncsight-investment-targets.csv",
            content: toCsv(sorted, [
              { header: "Company", value: (t) => t.company.name },
              { header: "UID", value: (t) => t.company.uid },
              { header: "Legal form", value: (t) => t.company.legal_form },
              { header: "Seat", value: (t) => t.company.seat },
              { header: "Canton", value: (t) => t.company.canton },
              { header: "Purpose match", value: (t) => t.purpose_excerpt?.replace(/[⟦⟧]/g, "") },
              { header: "Founded", value: (t) => t.founded_on },
              { header: "Capital raised on", value: (t) => t.raised_on },
              { header: "Capital before (CHF)", value: (t) => t.capital_before },
              { header: "Capital after (CHF)", value: (t) => t.capital_after },
              { header: "Increase (CHF)", value: (t) => increase(t) },
              { header: "SHAB notice", value: (t) => t.notice_url },
            ]),
          })}
        />
      )}
      {sorted.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Investment targets</caption>
            <thead>
              <tr>
                <SortableTh
                  sortKey="company"
                  label="Company"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                />
                <SortableTh
                  sortKey="founded"
                  label="Founded"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                  help="Date of the company's registration notice in SHAB"
                />
                <SortableTh
                  sortKey="raised"
                  label="Raised on"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                  help="SHAB notice stating the higher capital"
                />
                <SortableTh
                  sortKey="before"
                  label="Before"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                  className="num"
                />
                <SortableTh
                  sortKey="after"
                  label="After"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                  className="num"
                />
                <SortableTh
                  sortKey="increase"
                  label="Increase"
                  active={sortKey}
                  dir={sortDir}
                  onSort={toggle}
                  className="num"
                />
              </tr>
            </thead>
            <tbody>
              {sorted.map((t) => (
                <tr
                  key={t.company.uid}
                  className={t.company.uid === openedUid ? "row--opened" : undefined}
                >
                  <td>
                    <button
                      type="button"
                      className="link"
                      data-uid={t.company.uid}
                      onClick={() => onOpenCompany(t.company.uid)}
                    >
                      {t.company.name}
                    </button>
                    <div className="muted small">
                      {[t.company.legal_form, t.company.seat, t.company.canton]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                    {t.purpose_excerpt?.includes("⟦") && (
                      <div className="notice-text">
                        <Highlight text={t.purpose_excerpt} />
                      </div>
                    )}
                  </td>
                  <td className="nowrap">
                    <time dateTime={t.founded_on}>{formatDate(t.founded_on)}</time>
                  </td>
                  <td className="nowrap">
                    <a href={t.notice_url} target="_blank" rel="noreferrer">
                      <time dateTime={t.raised_on}>{formatDate(t.raised_on)}</time>
                    </a>
                  </td>
                  <td className="num">{formatChf(t.capital_before)}</td>
                  <td className="num">{formatChf(t.capital_after)}</td>
                  <td className="num">{formatIncrease(t)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

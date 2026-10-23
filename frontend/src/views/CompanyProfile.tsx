import { useEffect, useMemo, useRef, useState } from "react";

import {
  type CompanyProfile as Profile,
  formatChf,
  formatDate,
  getJson,
  type Notice,
} from "../api";
import { Chips } from "../components/Chips";
import { Clamp } from "../components/Clamp";
import { PeriodSelect } from "../components/PeriodSelect";
import { Status } from "../components/Status";
import { Th } from "../components/SortableTh";
import { changeLabel, HEALTH_CHANGES, RUBRICS, visibleChanges, WARNINGS } from "../lib/labels";
import type { OpenOptions } from "../lib/navigation";
import { useQuery } from "../lib/useQuery";

type Props = { uid: string; options: OpenOptions; from: string; onBack: () => void };

const isHealth = (n: Notice) => n.changes.some((c) => HEALTH_CHANGES.has(c));

/** Use case 3: company profile with its register timeline. */
export function CompanyProfile({ uid, options, from, onBack }: Props) {
  const [healthOnly, setHealthOnly] = useState(options.healthOnly ?? true);
  const [days, setDays] = useState(1826);
  const [{ data, loading, error }, run, retry] = useQuery<Profile>();
  const heading = useRef<HTMLHeadingElement>(null);
  const focusedNotice = useRef<HTMLTableRowElement>(null);

  useEffect(() => {
    // all notices of the period; the health filter is applied here so counts stay honest
    run((signal) =>
      getJson<Profile>(
        `/api/companies/${encodeURIComponent(uid)}`,
        { years: Math.round(days / 365.25), health_only: false },
        signal,
      ),
    );
  }, [uid, days, run]);

  useEffect(() => {
    if (!data) return;
    if (options.noticeId && focusedNotice.current) {
      focusedNotice.current.scrollIntoView?.({ block: "center" });
      focusedNotice.current.focus();
    } else {
      heading.current?.focus();
    }
  }, [data, options.noticeId]);

  const timeline = useMemo(() => data?.timeline ?? [], [data]);
  const healthCount = useMemo(() => timeline.filter(isHealth).length, [timeline]);
  const shown = healthOnly ? timeline.filter(isHealth) : timeline;

  return (
    <section aria-labelledby="profile-heading">
      <nav aria-label="Breadcrumb" className="breadcrumb">
        <button type="button" className="link" onClick={onBack}>
          ← Back to {from}
        </button>
        {data && (
          <span className="muted">
            {" "}
            {from} › {data.name}
          </span>
        )}
      </nav>
      <Status loading={loading && !data} error={error} empty={false} onRetry={retry} />
      {data && (
        <>
          <h2 id="profile-heading" ref={heading} tabIndex={-1}>
            {data.name}
            {data.status !== "active" && (
              <span className="badge badge--warning">{data.status}</span>
            )}
          </h2>
          <p className="muted">
            {data.uid} · {data.legal_form} · {data.address ?? data.seat}
          </p>
          <Clamp text={data.purpose} lines={3} minLength={300} className="purpose" />

          {data.sites.length > 0 && (
            <>
              <h3>Swissmedic licence sites</h3>
              <ul className="results">
                {data.sites.map((s) => (
                  <li key={`${s.licence_number}-${s.site_name}`}>
                    {s.site_name}, {s.site_locality} ({s.site_canton}): {s.activities.join(", ")}
                    <span className="muted">
                      {" "}
                      · last inspection {formatDate(s.last_inspection)} · {s.compliance_status}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}

          <h3>Register timeline</h3>
          <div className="filters">
            <label className="inline">
              <input
                type="checkbox"
                checked={healthOnly}
                onChange={(e) => setHealthOnly(e.target.checked)}
              />{" "}
              Health events only
              <span className="hint small">
                {" "}
                (capital, auditor, seat, liquidation, bankruptcy, deletion)
              </span>
            </label>
            <PeriodSelect value={days} onChange={setDays} options={[365, 730, 1826, 3652, 7305]} />
          </div>
          <p role="status" className="result-summary">
            {loading
              ? "Loading…"
              : `${timeline.length} notices · ${healthCount} health event${healthCount === 1 ? "" : "s"}` +
                (healthOnly && healthCount < timeline.length
                  ? ` · ${timeline.length - healthCount} other notices hidden`
                  : "")}
          </p>
          {shown.length === 0 ? (
            <p className="status">
              {timeline.length === 0 ? (
                "No register notices in this period (history may not be loaded yet)."
              ) : (
                <>
                  No health events in this period.{" "}
                  <button type="button" className="link" onClick={() => setHealthOnly(false)}>
                    Show all {timeline.length} notices
                  </button>
                </>
              )}
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <caption className="sr-only">Register timeline</caption>
                <thead>
                  <tr>
                    <Th label="Date" />
                    <Th label="Type" help="Registration, change or deletion notice in SHAB" />
                    <Th label="Changes" />
                    <Th label="Capital" className="num" />
                    <Th label="Notice" />
                  </tr>
                </thead>
                <tbody>
                  {shown.map((n) => (
                    <TimelineRow
                      key={n.id}
                      notice={n}
                      focused={n.id === options.noticeId}
                      rowRef={n.id === options.noticeId ? focusedNotice : undefined}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

type RowProps = {
  notice: Notice;
  focused: boolean;
  rowRef?: React.Ref<HTMLTableRowElement>;
};

function TimelineRow({ notice: n, focused, rowRef }: RowProps) {
  const capitalChanged = n.previous_capital !== null && n.capital !== n.previous_capital;
  const warning = n.changes.some((c) => WARNINGS.has(c));
  const classes = [warning ? "warning" : "", focused ? "row--focus" : ""].filter(Boolean).join(" ");
  return (
    <tr
      ref={rowRef}
      className={classes || undefined}
      aria-current={focused ? "true" : undefined}
      tabIndex={focused ? -1 : undefined}
    >
      <td className="nowrap">
        <a href={n.url} target="_blank" rel="noreferrer">
          <time dateTime={n.publication_date}>{formatDate(n.publication_date)}</time>
        </a>
      </td>
      <td>{RUBRICS[n.sub_rubric] ?? n.sub_rubric}</td>
      <td>
        <Chips
          items={visibleChanges(n.changes)}
          label={changeLabel}
          warn={(c) => WARNINGS.has(c)}
        />
      </td>
      <td className="num nowrap">
        {capitalChanged
          ? `${formatChf(n.previous_capital)} → ${formatChf(n.capital)}`
          : formatChf(n.capital)}
      </td>
      <td>
        <Clamp text={n.text} lines={2} minLength={160} className="notice-text" />
      </td>
    </tr>
  );
}

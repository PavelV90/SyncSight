import { useEffect, useState } from "react";

import { type CompanyProfile as Profile, formatChf, getJson, type Notice } from "../api";
import { Status } from "./Status";
import { useQuery } from "./useQuery";

const RUBRICS: Record<string, string> = {
  HR01: "Registration",
  HR02: "Change",
  HR03: "Deletion",
};
// Labels that signal financial health (use case 3); highlighted in the timeline.
const WARNINGS = new Set(["bankruptcy", "liquidation", "deletion"]);

type Props = { uid: string; onBack: () => void };

/** Use case 3: company profile with its register timeline. */
export function CompanyProfile({ uid, onBack }: Props) {
  const [healthOnly, setHealthOnly] = useState(true);
  const [years, setYears] = useState(5);
  const [{ data, loading, error }, run] = useQuery<Profile>();

  useEffect(() => {
    run(() =>
      getJson<Profile>(`/api/companies/${encodeURIComponent(uid)}`, {
        years,
        health_only: healthOnly,
      }),
    );
  }, [uid, years, healthOnly, run]);

  return (
    <section>
      <button className="link" onClick={onBack}>
        ← Back
      </button>
      <Status loading={loading} error={error} empty={false} />
      {data && (
        <>
          <h2>{data.name}</h2>
          <p className="muted">
            {data.uid} · {data.legal_form} · {data.address ?? data.seat}
            {data.status !== "active" && ` · ${data.status}`}
          </p>
          {data.purpose && <p className="purpose">{data.purpose}</p>}

          {data.sites.length > 0 && (
            <>
              <h3>Swissmedic licence sites</h3>
              <ul className="results">
                {data.sites.map((s) => (
                  <li key={`${s.licence_number}-${s.site_name}`}>
                    {s.site_name}, {s.site_locality} ({s.site_canton}): {s.activities.join(", ")}
                    <span className="muted">
                      {" "}
                      · last inspection {s.last_inspection ?? "–"} · {s.compliance_status}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}

          <h3>Register timeline</h3>
          <div className="filters">
            <label>
              <input
                type="checkbox"
                checked={healthOnly}
                onChange={(e) => setHealthOnly(e.target.checked)}
              />{" "}
              Health events only (capital, auditor, seat, liquidation, bankruptcy, deletion)
            </label>
            <label>
              Years{" "}
              <select value={years} onChange={(e) => setYears(Number(e.target.value))}>
                {[1, 2, 5, 10].map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {data.timeline.length === 0 ? (
            <p role="status">No notices in this period (history may not be loaded yet).</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Changes</th>
                  <th>Capital</th>
                  <th>Notice</th>
                </tr>
              </thead>
              <tbody>
                {data.timeline.map((n) => (
                  <TimelineRow key={n.id} notice={n} />
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}

function TimelineRow({ notice: n }: { notice: Notice }) {
  const capitalChanged = n.previous_capital !== null && n.capital !== n.previous_capital;
  return (
    <tr className={n.changes.some((c) => WARNINGS.has(c)) ? "warning" : undefined}>
      <td>
        <a href={n.url} target="_blank" rel="noreferrer">
          {n.publication_date}
        </a>
      </td>
      <td>{RUBRICS[n.sub_rubric] ?? n.sub_rubric}</td>
      <td>{n.changes.join(", ")}</td>
      <td>
        {capitalChanged
          ? `${formatChf(n.previous_capital)} → ${formatChf(n.capital)}`
          : formatChf(n.capital)}
      </td>
      <td className="notice-text">{n.text}</td>
    </tr>
  );
}

import { useEffect, useState } from "react";

import { formatDate, formatRelative, getJson, type SourceStatus } from "../api";

/** Header chip: when each source was last loaded, flagging stale or missing data. */
export function DataFreshness() {
  const [sources, setSources] = useState<SourceStatus[] | null>(null);
  useEffect(() => {
    getJson<SourceStatus[]>("/api/status")
      .then(setSources)
      .catch(() => setSources(null));
  }, []);
  if (!sources?.length) return null;
  const stale = sources.filter((s) => s.stale);
  const loads = sources.flatMap((s) => (s.last_loaded_at ? [s.last_loaded_at] : [])).sort();
  const oldest = loads[0];
  return (
    <details className="freshness">
      <summary className={stale.length ? "chip chip--warning" : "chip"}>
        {stale.length
          ? `⚠ ${stale.length} source${stale.length === 1 ? "" : "s"} stale`
          : "Data up to date"}
        {oldest && <span className="muted"> · oldest load {formatDate(oldest)}</span>}
      </summary>
      <div className="freshness-panel">
        <table className="compact">
          <caption className="sr-only">Data sources</caption>
          <thead>
            <tr>
              <th scope="col">Source</th>
              <th scope="col" className="num">
                Rows
              </th>
              <th scope="col">Last loaded</th>
              <th scope="col">Newest record</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.key} className={s.stale ? "warning" : undefined}>
                <td>{s.label}</td>
                <td className="num">{s.rows.toLocaleString("de-CH")}</td>
                <td className="nowrap">
                  {s.last_loaded_at ? (
                    <>
                      {formatDate(s.last_loaded_at)}{" "}
                      <span className="muted small">{formatRelative(s.last_loaded_at)}</span>
                    </>
                  ) : (
                    "never"
                  )}
                </td>
                <td className="nowrap">{formatDate(s.newest_record)}</td>
                <td>
                  {s.stale ? (
                    <>
                      {s.last_loaded_at ? "stale" : "not loaded"} – run{" "}
                      <code>syncsight-ingest {s.command}</code>
                    </>
                  ) : (
                    "ok"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

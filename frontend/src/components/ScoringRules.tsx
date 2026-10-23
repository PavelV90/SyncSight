import { useEffect, useState } from "react";

import { getJson, type ScoringRule } from "../api";
import { kindLabel } from "../lib/kinds";

/** "How scores work": the scoring rules as served by the API. */
export function ScoringRules() {
  const [rules, setRules] = useState<ScoringRule[] | null>(null);
  useEffect(() => {
    getJson<ScoringRule[]>("/api/mes-scoring")
      .then(setRules)
      .catch(() => setRules([]));
  }, []);
  if (!rules?.length) return null;
  return (
    <details className="scoring-rules">
      <summary>How scores work</summary>
      <p className="small">
        Each signal kind adds points per item, up to a maximum number of items (newest first).
        Building permits, licence changes, medicines and website hits count within the chosen
        period; management changes within 12 months.
      </p>
      <table className="compact">
        <thead>
          <tr>
            <th scope="col">Signal</th>
            <th scope="col" className="num">
              Points each
            </th>
            <th scope="col" className="num">
              Counted up to
            </th>
          </tr>
        </thead>
        <tbody>
          {rules.map((r) => (
            <tr key={r.kind}>
              <td>{kindLabel(r.kind)}</td>
              <td className="num">{r.points}</td>
              <td className="num">{r.max_items}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

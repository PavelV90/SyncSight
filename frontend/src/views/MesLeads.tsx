import { type FormEvent, useState } from "react";

import { getJson, type MesLead } from "../api";
import { Status } from "./Status";
import { useQuery } from "./useQuery";

// Evidence kinds as shown to users (backend: syncsight/db/mes.py)
const KINDS: Record<string, string> = {
  web_mes: "MES on website",
  web_hiring: "Hiring for MES",
  web_vendor: "MES vendor named",
  permit_production: "Production building permit",
  permit_other: "Building permit",
  licence_change: "Licence change",
  web_expansion: "Expansion news",
  web_digital: "Digitalisation news",
  management_change: "Management change",
  capital_raise: "Capital increase",
  new_medicine: "New medicines",
};

type Props = { onOpenCompany: (uid: string) => void };

/** Licensed pharma manufacturers ranked by MES signals, with the evidence behind each score. */
export function MesLeads({ onOpenCompany }: Props) {
  const [months, setMonths] = useState(24);
  const [cantons, setCantons] = useState("");
  const [minScore, setMinScore] = useState(3);
  const [{ data, loading, error }, run] = useQuery<MesLead[]>();

  function submit(event: FormEvent) {
    event.preventDefault();
    const list = cantons
      .split(/[\s,]+/)
      .map((c) => c.trim().toUpperCase())
      .filter(Boolean);
    run(() => getJson<MesLead[]>("/api/mes-leads", { months, cantons: list, min_score: minScore }));
  }

  return (
    <section>
      <p className="hint">
        Swissmedic-licensed manufacturers ranked by signals of MES need: production building
        permits, MES or vendor mentions on their websites and career pages, licence changes, and
        management changes. Open a row to see the evidence.
      </p>
      <form onSubmit={submit} className="filters">
        <label>
          Last months{" "}
          <input
            type="number"
            min={1}
            value={months}
            onChange={(e) => setMonths(Number(e.target.value))}
          />
        </label>
        <label>
          Site cantons (optional){" "}
          <input
            value={cantons}
            onChange={(e) => setCantons(e.target.value)}
            placeholder="BS, BL, AG"
          />
        </label>
        <label>
          Minimum score{" "}
          <input
            type="number"
            min={0}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
          />
        </label>
        <button type="submit">Rank MES leads</button>
      </form>
      <Status loading={loading} error={error} empty={data?.length === 0} />
      {data && data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Score</th>
              <th>Company</th>
              <th>Sites in</th>
              <th>MES vendors named</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {data.map((lead) => (
              <tr key={lead.company.uid}>
                <td className="score">{lead.score}</td>
                <td>
                  <button className="link" onClick={() => onOpenCompany(lead.company.uid)}>
                    {lead.company.name}
                  </button>
                  <div className="muted">{lead.activities.join(", ")}</div>
                </td>
                <td>{lead.site_cantons.join(", ")}</td>
                <td>{lead.vendors.join(", ") || "–"}</td>
                <td>
                  <details>
                    <summary>
                      {[...new Set(lead.evidence.map((e) => KINDS[e.kind] ?? e.kind))].join(" · ")}
                    </summary>
                    <ul className="evidence">
                      {lead.evidence.map((e, i) => (
                        <li key={i}>
                          <span className="muted">{e.on ?? "current"}</span>{" "}
                          {e.url ? (
                            <a href={e.url} target="_blank" rel="noreferrer">
                              {e.title}
                            </a>
                          ) : (
                            e.title
                          )}
                          {e.detail && <div className="notice-text">{e.detail}</div>}
                        </li>
                      ))}
                    </ul>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

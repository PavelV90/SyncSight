import { type FormEvent, useState } from "react";

import { getJson, type Lead } from "../api";
import { Status } from "./Status";
import { useQuery } from "./useQuery";

const ACTIVITIES = [
  [1, "Manufacturing"],
  [3, "API manufacturing"],
  [2, "Import"],
  [4, "Wholesale"],
] as const;

type Props = { onOpenCompany: (uid: string) => void };

/** Use case 1: licensed pharma companies with recent board or management changes. */
export function Leads({ onOpenCompany }: Props) {
  const [cantons, setCantons] = useState("BS, BL, AG");
  const [days, setDays] = useState(90);
  const [activity, setActivity] = useState(1);
  const [{ data, loading, error }, run] = useQuery<Lead[]>();

  function submit(event: FormEvent) {
    event.preventDefault();
    const list = cantons
      .split(/[\s,]+/)
      .map((c) => c.trim().toUpperCase())
      .filter(Boolean);
    run(() => getJson<Lead[]>("/api/leads", { cantons: list, days, activity }));
  }

  return (
    <section>
      <p className="hint">
        Swissmedic-licensed companies with sites in these cantons whose board or management changed
        recently.
      </p>
      <form onSubmit={submit} className="filters">
        <label>
          Cantons <input value={cantons} onChange={(e) => setCantons(e.target.value)} />
        </label>
        <label>
          Last days{" "}
          <input
            type="number"
            min={1}
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          />
        </label>
        <label>
          Activity{" "}
          <select value={activity} onChange={(e) => setActivity(Number(e.target.value))}>
            {ACTIVITIES.map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <button type="submit">Find leads</button>
      </form>
      <Status loading={loading} error={error} empty={data?.length === 0} />
      {data && data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Sites in</th>
              <th>Activities</th>
              <th>Last change</th>
              <th>Changes</th>
            </tr>
          </thead>
          <tbody>
            {data.map((lead) => (
              <tr key={lead.company.uid}>
                <td>
                  <button className="link" onClick={() => onOpenCompany(lead.company.uid)}>
                    {lead.company.name}
                  </button>
                </td>
                <td>{lead.site_cantons.join(", ")}</td>
                <td>{lead.activities.join(", ")}</td>
                <td>
                  <a href={lead.notices[0].url} target="_blank" rel="noreferrer">
                    {lead.last_change}
                  </a>
                </td>
                <td>{[...new Set(lead.notices.flatMap((n) => n.changes))].join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

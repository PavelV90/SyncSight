import { type FormEvent, useState } from "react";

import { type Company, getJson } from "../api";
import { Status } from "./Status";
import { useQuery } from "./useQuery";

type Props = { onOpenCompany: (uid: string) => void };

/** Find a company by name, purpose keywords or UID (entry point for use case 3). */
export function CompanySearch({ onOpenCompany }: Props) {
  const [q, setQ] = useState("");
  const [{ data, loading, error }, run] = useQuery<Company[]>();

  function submit(event: FormEvent) {
    event.preventDefault();
    if (q.trim().length >= 2) run(() => getJson<Company[]>("/api/companies", { q }));
  }

  return (
    <section>
      <form onSubmit={submit} className="filters">
        <label>
          Company name, keywords or UID{" "}
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="CHE-…" />
        </label>
        <button type="submit">Search</button>
      </form>
      <Status loading={loading} error={error} empty={data?.length === 0} />
      {data && data.length > 0 && (
        <ul className="results">
          {data.map((c) => (
            <li key={c.uid}>
              <button className="link" onClick={() => onOpenCompany(c.uid)}>
                {c.name}
              </button>{" "}
              <span className="muted">
                {c.uid} · {c.seat} {c.canton && `(${c.canton})`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

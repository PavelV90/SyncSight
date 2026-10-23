import { type FormEvent, useState } from "react";

import { formatChf, getJson, type Target } from "../api";
import { Status } from "./Status";
import { useQuery } from "./useQuery";

type Props = { onOpenCompany: (uid: string) => void };

/** Use case 2: young companies in a field that recently raised capital. */
export function Targets({ onOpenCompany }: Props) {
  const [q, setQ] = useState("medtech");
  const [foundedSince, setFoundedSince] = useState("2020-01-01");
  const [days, setDays] = useState(365);
  const [{ data, loading, error }, run] = useQuery<Target[]>();

  function submit(event: FormEvent) {
    event.preventDefault();
    run(() =>
      getJson<Target[]>("/api/targets", {
        q,
        founded_since: foundedSince,
        raised_within_days: days,
      }),
    );
  }

  return (
    <section>
      <p className="hint">
        Companies whose purpose matches the keywords, registered since the date, that increased
        their capital recently. Keywords support <code>or</code> and quotes.
      </p>
      <form onSubmit={submit} className="filters">
        <label>
          Keywords <input value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <label>
          Founded since{" "}
          <input
            type="date"
            value={foundedSince}
            onChange={(e) => setFoundedSince(e.target.value)}
          />
        </label>
        <label>
          Raised in last days{" "}
          <input
            type="number"
            min={1}
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          />
        </label>
        <button type="submit">Find targets</button>
      </form>
      <Status loading={loading} error={error} empty={data?.length === 0} />
      {data && data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Canton</th>
              <th>Founded</th>
              <th>Capital raised</th>
              <th>Capital</th>
            </tr>
          </thead>
          <tbody>
            {data.map((t) => (
              <tr key={t.company.uid}>
                <td>
                  <button className="link" onClick={() => onOpenCompany(t.company.uid)}>
                    {t.company.name}
                  </button>
                </td>
                <td>{t.company.canton}</td>
                <td>{t.founded_on}</td>
                <td>
                  <a href={t.notice_url} target="_blank" rel="noreferrer">
                    {t.raised_on}
                  </a>
                </td>
                <td>{`${formatChf(t.capital_before)} → ${formatChf(t.capital_after)}`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

import { type Evidence, formatDate, type KindScore } from "../api";
import { kindLabel } from "../lib/kinds";

type Props = { evidence: Evidence[]; breakdown: KindScore[] };

/** Evidence grouped by signal kind; items over a kind's cap are collapsed as "not counted". */
export function EvidenceList({ evidence, breakdown }: Props) {
  return (
    <div className="evidence-groups">
      {breakdown.map((group) => {
        const items = evidence.filter((e) => e.kind === group.kind);
        const counted = items.filter((e) => e.points > 0);
        const extra = items.filter((e) => e.points === 0);
        return (
          <section key={group.kind} className="evidence-group">
            <h4>
              {kindLabel(group.kind)}{" "}
              <span className="muted small">
                {group.counted} × {group.points_each} = {group.points} pt
                {group.points === 1 ? "" : "s"}
                {group.items > group.counted && ` · ${group.items} found`}
              </span>
            </h4>
            <ul className="evidence">
              {counted.map((e, i) => (
                <EvidenceItem key={i} item={e} />
              ))}
            </ul>
            {extra.length > 0 && (
              <details>
                <summary className="muted small">
                  {extra.length} more, not counted (cap reached)
                </summary>
                <ul className="evidence">
                  {extra.map((e, i) => (
                    <EvidenceItem key={i} item={e} />
                  ))}
                </ul>
              </details>
            )}
          </section>
        );
      })}
    </div>
  );
}

function EvidenceItem({ item: e }: { item: Evidence }) {
  return (
    <li>
      <span className="muted nowrap">{e.on ? formatDate(e.on) : "current"}</span>{" "}
      {e.url ? (
        <a href={e.url} target="_blank" rel="noreferrer">
          {e.title}
        </a>
      ) : (
        e.title
      )}
      {e.detail && <div className="notice-text">{e.detail}</div>}
    </li>
  );
}

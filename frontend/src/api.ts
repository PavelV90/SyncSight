// Typed client for the SyncSight API (see backend/src/syncsight/api/schemas.py).

export type Company = {
  uid: string;
  name: string;
  legal_form: string | null;
  seat: string | null;
  canton: string | null;
  status: string | null;
};

export type Notice = {
  id: string;
  publication_date: string;
  sub_rubric: string;
  changes: string[];
  capital: number | null;
  previous_capital: number | null;
  text: string | null;
  url: string;
};

export type Site = {
  licence_number: string;
  site_name: string | null;
  site_locality: string | null;
  site_canton: string | null;
  activities: string[];
  last_inspection: string | null;
  compliance_status: string | null;
};

export type CompanyProfile = Company & {
  purpose: string | null;
  address: string | null;
  website: string | null;
  history_fetched_at: string | null;
  notice_count: number;
  earliest_notice: string | null;
  sites: Site[];
  timeline: Notice[];
  mes: MesLead | null;
};

export type Lead = {
  company: Company;
  site_cantons: string[];
  activities: string[];
  last_change: string;
  notices: Notice[];
};

export type Target = {
  company: Company;
  founded_on: string;
  raised_on: string;
  capital_before: number;
  capital_after: number;
  notice_url: string;
  purpose_excerpt: string | null; // matched words wrapped in ⟦ ⟧
};

export type Evidence = {
  kind: string;
  on: string | null;
  title: string;
  detail: string | null;
  url: string | null;
  points: number;
};

export type KindScore = {
  kind: string;
  items: number;
  counted: number;
  points_each: number;
  points: number;
};

export type ScoringRule = { kind: string; points: number; max_items: number };

export type SourceStatus = {
  key: string;
  label: string;
  rows: number;
  last_loaded_at: string | null;
  newest_record: string | null;
  stale: boolean;
  command: string;
};

export type MesLead = {
  company: Company;
  score: number;
  breakdown: KindScore[];
  site_cantons: string[];
  activities: string[];
  vendors: string[];
  evidence: Evidence[];
};

type Params = Record<string, string | number | boolean | Array<string | number>>;

/** An API failure with a message fit for users (FastAPI `detail` when available). */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function getJson<T>(
  path: string,
  params: Params = {},
  signal?: AbortSignal,
): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    for (const item of Array.isArray(value) ? value : [value]) query.append(key, String(item));
  }
  const url = query.size ? `${path}?${query}` : path;
  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Backend not reachable. Is SyncSight running (start.command)?", 0);
  }
  if (!response.ok) throw new ApiError(await errorMessage(response), response.status);
  return (await response.json()) as T;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((d: { loc?: unknown[]; msg?: string }) => `${String(d.loc?.at(-1) ?? "")}: ${d.msg}`)
        .join("; ");
    }
  } catch {
    // body was not JSON
  }
  return `Request failed (HTTP ${response.status})`;
}

const chf = new Intl.NumberFormat("de-CH", {
  style: "currency",
  currency: "CHF",
  maximumFractionDigits: 0,
});
const dateFormat = new Intl.DateTimeFormat("de-CH", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});
const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

export function formatChf(value: number | null): string {
  return value === null ? "–" : chf.format(value);
}

/** "2026-10-20" -> "20.10.2026"; "–" when missing. */
export function formatDate(iso: string | null): string {
  return iso ? dateFormat.format(new Date(`${iso.slice(0, 10)}T00:00:00`)) : "–";
}

/** Whole days between an ISO date and today (positive = past). */
export function daysAgo(iso: string, today: Date = new Date()): number {
  const then = new Date(`${iso.slice(0, 10)}T00:00:00`);
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((start.getTime() - then.getTime()) / 86_400_000);
}

/** "today", "3 days ago", "2 months ago". */
export function formatRelative(iso: string, today: Date = new Date()): string {
  const days = daysAgo(iso, today);
  if (Math.abs(days) < 45) return relative.format(-days, "day");
  if (Math.abs(days) < 548) return relative.format(-Math.round(days / 30.44), "month");
  return relative.format(-Math.round(days / 365.25), "year");
}

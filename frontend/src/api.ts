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
  sites: Site[];
  timeline: Notice[];
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
};

type Params = Record<string, string | number | boolean | Array<string | number>>;

export async function getJson<T>(path: string, params: Params = {}): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    for (const item of Array.isArray(value) ? value : [value]) query.append(key, String(item));
  }
  const url = query.size ? `${path}?${query}` : path;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as T;
}

const chf = new Intl.NumberFormat("de-CH", {
  style: "currency",
  currency: "CHF",
  maximumFractionDigits: 0,
});

export function formatChf(value: number | null): string {
  return value === null ? "–" : chf.format(value);
}

import { type Mock, vi } from "vitest";

import { formatChf } from "./api";

/** Stub fetch: answer each request with the body registered for its path. */
export function mockApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((url: string) => {
    const path = url.split("?")[0];
    if (!(path in routes)) return Promise.resolve(new Response("", { status: 404 }));
    return Promise.resolve(new Response(JSON.stringify(routes[path]), { status: 200 }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** URLs fetched so far (first argument of each call). */
export const fetchedUrls = (fetchMock: Mock) => fetchMock.mock.calls.map((call) => String(call[0]));

export const company = {
  uid: "CHE-000.000.001",
  name: "Alpenpharma AG",
  legal_form: "Aktiengesellschaft",
  seat: "Basel",
  canton: "BS",
  status: "active",
};

export const notice = {
  id: "n1",
  publication_date: "2026-10-12",
  sub_rubric: "HR02",
  changes: ["board"],
  capital: 500000,
  previous_capital: 100000,
  text: "Mitglied des Verwaltungsrates neu.",
  url: "https://www.shab.ch/#!/search/publications/detail/n1",
};

export const mesLead = {
  company,
  score: 5,
  breakdown: [
    { kind: "permit_production", items: 1, counted: 1, points_each: 3, points: 3 },
    { kind: "web_hiring", items: 1, counted: 1, points_each: 2, points: 2 },
  ],
  site_cantons: ["BS"],
  activities: ["Manufacturing"],
  vendors: ["PharmaSuite"],
  evidence: [
    {
      kind: "permit_production",
      on: "2026-09-02",
      title: "Building permit: Neubau Produktionsgebäude",
      detail: "Werkstrasse 1, Basel",
      url: "https://www.shab.ch/#!/search/publications/detail/p1",
      points: 3,
    },
    {
      kind: "web_hiring",
      on: null,
      title: "MES Engineer",
      detail: null,
      url: "https://a.ch/jobs/1",
      points: 2,
    },
  ],
};

/** Capital change as rendered; Testing Library collapses Intl's non-breaking spaces. */
export function capitalChange(before: number, after: number): string {
  return `${formatChf(before)} → ${formatChf(after)}`.replace(/\s+/g, " ");
}

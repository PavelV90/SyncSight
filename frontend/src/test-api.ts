import { vi } from "vitest";

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

/** Capital change as rendered; Testing Library collapses Intl's non-breaking spaces. */
export function capitalChange(before: number, after: number): string {
  return `${formatChf(before)} → ${formatChf(after)}`.replace(/\s+/g, " ");
}

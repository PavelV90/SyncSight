import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { company, fetchedUrls, mesLead, mockApi } from "../test-api";
import { MesLeads } from "./MesLeads";

afterEach(() => vi.unstubAllGlobals());

const other = {
  ...mesLead,
  company: { ...company, uid: "CHE-000.000.002", name: "Rheinchemie AG" },
  score: 1,
  vendors: [],
  breakdown: [{ kind: "management_change", items: 1, counted: 1, points_each: 1, points: 1 }],
  evidence: [
    {
      kind: "management_change",
      on: "2026-10-01",
      title: "Register: management change",
      detail: null,
      url: null,
      points: 1,
    },
  ],
};

it("loads ranked leads on open and explains them with evidence", async () => {
  const fetchMock = mockApi({ "/api/mes-leads": [mesLead, other] });
  render(<MesLeads onOpenCompany={() => {}} openedUid={null} />);

  expect(await screen.findByRole("button", { name: "Alpenpharma AG" })).toBeInTheDocument();
  expect(fetchedUrls(fetchMock).filter((u) => u.startsWith("/api/mes-leads"))).toEqual([
    "/api/mes-leads?months=24&min_score=3",
  ]);
  expect(
    screen.getByText(/2 MES leads · last 2 years · all cantons · score ≥ 3/),
  ).toBeInTheDocument();
  expect(screen.getByText("PharmaSuite")).toHaveClass("badge");
  expect(
    screen.getByRole("link", { name: "Building permit: Neubau Produktionsgebäude" }),
  ).toHaveAttribute("href", "https://www.shab.ch/#!/search/publications/detail/p1");
});

it("filters loaded leads by required signal kinds", async () => {
  mockApi({ "/api/mes-leads": [mesLead, other] });
  render(<MesLeads onOpenCompany={() => {}} openedUid={null} />);
  await screen.findByRole("button", { name: "Rheinchemie AG" });

  fireEvent.click(screen.getByRole("button", { name: "Production building permit (1)" }));

  expect(screen.queryByRole("button", { name: "Rheinchemie AG" })).not.toBeInTheDocument();
  expect(screen.getByText(/1 of 2 MES leads/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Production building permit (1)" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

it("explains each score with its breakdown and the scoring rules", async () => {
  mockApi({
    "/api/mes-leads": [mesLead],
    "/api/mes-scoring": [{ kind: "permit_production", points: 3, max_items: 2 }],
  });
  render(<MesLeads onOpenCompany={() => {}} openedUid={null} />);

  const score = await screen.findByTitle("Production building permit 1×3 · Hiring for MES 1×2 = 5");
  expect(score).toHaveTextContent("5");
  expect(await screen.findByText("How scores work")).toBeInTheDocument();
  expect(screen.getAllByText("1 × 3 = 3 pts")[0]).toBeInTheDocument();
});

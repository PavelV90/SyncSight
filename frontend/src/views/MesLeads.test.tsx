import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { company, fetchedUrls, mesLead, mockApi } from "../test-api";
import { MesLeads } from "./MesLeads";

afterEach(() => vi.unstubAllGlobals());

const other = {
  ...mesLead,
  company: { ...company, uid: "CHE-000.000.002", name: "Rheinchemie AG" },
  score: 4,
  vendors: [],
  evidence: [
    {
      kind: "management_change",
      on: "2026-10-01",
      title: "Register: management change",
      detail: null,
      url: null,
    },
  ],
};

it("loads ranked leads on open and explains them with evidence", async () => {
  const fetchMock = mockApi({ "/api/mes-leads": [mesLead, other] });
  render(<MesLeads onOpenCompany={() => {}} openedUid={null} />);

  expect(await screen.findByRole("button", { name: "Alpenpharma AG" })).toBeInTheDocument();
  expect(fetchedUrls(fetchMock)).toEqual(["/api/mes-leads?months=24&min_score=3"]);
  expect(
    screen.getByText(/2 MES leads · last 2 years · all cantons · score ≥ 3/),
  ).toBeInTheDocument();
  expect(screen.getByText("PharmaSuite")).toBeInTheDocument();
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

it("rejects an invalid minimum score without querying", async () => {
  const fetchMock = mockApi({ "/api/mes-leads": [] });
  render(<MesLeads onOpenCompany={() => {}} openedUid={null} />);
  await screen.findByText("No leads match these filters.");

  fireEvent.change(screen.getByLabelText(/Minimum score/), { target: { value: "-1" } });
  fireEvent.click(screen.getByRole("button", { name: "Rank MES leads" }));

  expect(screen.getByText("Enter a whole number from 0 to 30.")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

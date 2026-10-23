import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { company, mockApi } from "../test-api";
import { MesLeads } from "./MesLeads";

afterEach(() => vi.unstubAllGlobals());

it("ranks leads and shows the evidence behind the score", async () => {
  const fetchMock = mockApi({
    "/api/mes-leads": [
      {
        company,
        score: 9,
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
          },
          {
            kind: "web_hiring",
            on: null,
            title: "MES Engineer",
            detail: null,
            url: "https://a.ch/jobs/1",
          },
        ],
      },
    ],
  });
  render(<MesLeads onOpenCompany={() => {}} />);

  fireEvent.click(screen.getByRole("button", { name: "Rank MES leads" }));

  expect(await screen.findByText("9")).toBeInTheDocument();
  expect(screen.getByText("PharmaSuite")).toBeInTheDocument();
  expect(screen.getByText("Production building permit · Hiring for MES")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Building permit: Neubau Produktionsgebäude" }),
  ).toHaveAttribute("href", "https://www.shab.ch/#!/search/publications/detail/p1");
  expect(fetchMock).toHaveBeenCalledWith("/api/mes-leads?months=24&min_score=3");
});

import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { capitalChange, company, mockApi } from "../test-api";
import { Targets } from "./Targets";

afterEach(() => vi.unstubAllGlobals());

it("lists targets with their capital increase", async () => {
  const fetchMock = mockApi({
    "/api/targets": [
      {
        company,
        founded_on: "2021-03-01",
        raised_on: "2026-09-20",
        capital_before: 100000,
        capital_after: 250000,
        notice_url: "https://www.shab.ch/#!/search/publications/detail/n2",
      },
    ],
  });
  render(<Targets onOpenCompany={() => {}} />);

  fireEvent.click(screen.getByRole("button", { name: "Find targets" }));

  expect(await screen.findByText(capitalChange(100000, 250000))).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/targets?q=medtech&founded_since=2020-01-01&raised_within_days=365",
  );
});

it("shows when nothing matches", async () => {
  mockApi({ "/api/targets": [] });
  render(<Targets onOpenCompany={() => {}} />);

  fireEvent.click(screen.getByRole("button", { name: "Find targets" }));

  expect(await screen.findByText("No results.")).toBeInTheDocument();
});

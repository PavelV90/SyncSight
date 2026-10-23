import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { capitalChange, company, mockApi, notice } from "../test-api";
import { CompanyProfile } from "./CompanyProfile";

afterEach(() => vi.unstubAllGlobals());

const profile = {
  ...company,
  purpose: "Herstellung von Arzneimitteln.",
  address: "Hauptstrasse 1, 4051 Basel",
  sites: [],
  timeline: [{ ...notice, changes: ["capital"] }],
};

it("shows health events first and all events on request", async () => {
  const fetchMock = mockApi({ "/api/companies/CHE-000.000.001": profile });
  render(<CompanyProfile uid="CHE-000.000.001" onBack={() => {}} />);

  expect(await screen.findByRole("heading", { name: "Alpenpharma AG" })).toBeInTheDocument();
  expect(screen.getByText(capitalChange(100000, 500000))).toBeInTheDocument();
  expect(fetchMock).toHaveBeenLastCalledWith(
    "/api/companies/CHE-000.000.001?years=5&health_only=true",
  );

  fireEvent.click(screen.getByRole("checkbox"));

  await screen.findByRole("heading", { name: "Alpenpharma AG" });
  expect(fetchMock).toHaveBeenLastCalledWith(
    "/api/companies/CHE-000.000.001?years=5&health_only=false",
  );
});

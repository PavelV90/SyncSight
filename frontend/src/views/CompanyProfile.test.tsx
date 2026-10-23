import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { capitalChange, company, fetchedUrls, mockApi, notice } from "../test-api";
import { CompanyProfile } from "./CompanyProfile";

afterEach(() => vi.unstubAllGlobals());

const profile = {
  ...company,
  purpose: "Herstellung von Arzneimitteln.",
  address: "Hauptstrasse 1, 4051 Basel",
  sites: [],
  timeline: [
    { ...notice, id: "n1", changes: ["capital"] },
    { ...notice, id: "n2", changes: ["board"], capital: 100000, previous_capital: 100000 },
  ],
};

it("filters health events locally and keeps honest counts", async () => {
  const fetchMock = mockApi({ "/api/companies/CHE-000.000.001": profile });
  render(<CompanyProfile uid="CHE-000.000.001" options={{}} from="MES leads" onBack={() => {}} />);

  expect(await screen.findByRole("heading", { name: "Alpenpharma AG" })).toBeInTheDocument();
  expect(screen.getByText(capitalChange(100000, 500000))).toBeInTheDocument();
  expect(
    screen.getByText("2 notices · 1 health event · 1 other notices hidden"),
  ).toBeInTheDocument();
  expect(fetchedUrls(fetchMock)).toEqual([
    "/api/companies/CHE-000.000.001?years=5&health_only=false",
  ]);

  fireEvent.click(screen.getByRole("checkbox"));

  expect(screen.getAllByRole("row")).toHaveLength(3);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("offers all notices when the period has no health event", async () => {
  mockApi({ "/api/companies/CHE-000.000.001": { ...profile, timeline: [profile.timeline[1]] } });
  render(<CompanyProfile uid="CHE-000.000.001" options={{}} from="Leads" onBack={() => {}} />);

  fireEvent.click(await screen.findByRole("button", { name: "Show all 1 notices" }));

  expect(screen.getByText("Board")).toBeInTheDocument();
});

it("highlights the notice that opened the profile", async () => {
  mockApi({ "/api/companies/CHE-000.000.001": profile });
  render(
    <CompanyProfile
      uid="CHE-000.000.001"
      options={{ healthOnly: false, noticeId: "n2" }}
      from="Leads"
      onBack={() => {}}
    />,
  );

  const row = (await screen.findByText("Board")).closest("tr");
  expect(row).toHaveAttribute("aria-current", "true");
  expect(row).toHaveFocus();
});

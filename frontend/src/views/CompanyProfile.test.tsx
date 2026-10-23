import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { capitalChange, company, fetchedUrls, mesLead, mockApi, notice } from "../test-api";
import { CompanyProfile } from "./CompanyProfile";

afterEach(() => vi.unstubAllGlobals());

const profile = {
  ...company,
  purpose: "Herstellung von Arzneimitteln.",
  address: "Hauptstrasse 1, 4051 Basel",
  website: "https://www.alpenpharma.ch",
  history_fetched_at: "2026-10-23T07:10:00Z",
  notice_count: 12,
  earliest_notice: "2019-11-22",
  mes: null,
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

it("shows links, history coverage and MES signals", async () => {
  mockApi({ "/api/companies/CHE-000.000.001": { ...profile, mes: mesLead } });
  render(<CompanyProfile uid="CHE-000.000.001" options={{}} from="MES leads" onBack={() => {}} />);

  expect(await screen.findByRole("link", { name: "Zefix ↗" })).toHaveAttribute(
    "href",
    "https://www.zefix.admin.ch/en/search/entity/list?mainSearch=CHE-000.000.001",
  );
  expect(screen.getByRole("link", { name: "Website ↗" })).toHaveAttribute(
    "href",
    "https://www.alpenpharma.ch",
  );
  expect(
    screen.getByText(/Full SHAB history loaded 23.10.2026 · 12 notices back to 22.11.2019/),
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /MES signals/ })).toHaveTextContent("5");
  expect(screen.getByRole("link", { name: "MES Engineer" })).toBeInTheDocument();
});

it("tells how to load a missing history", async () => {
  mockApi({
    "/api/companies/CHE-000.000.001": {
      ...profile,
      history_fetched_at: null,
      notice_count: 0,
      earliest_notice: null,
      timeline: [],
    },
  });
  render(<CompanyProfile uid="CHE-000.000.001" options={{}} from="Leads" onBack={() => {}} />);

  expect(
    await screen.findByText("uv run syncsight-ingest shab --uid CHE-000.000.001"),
  ).toBeInTheDocument();
  expect(
    screen.getByText("No register notices loaded for this company yet (see above)."),
  ).toBeInTheDocument();
});

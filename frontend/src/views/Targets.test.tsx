import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { company, fetchedUrls, mockApi } from "../test-api";
import { Targets } from "./Targets";

afterEach(() => vi.unstubAllGlobals());

const target = (name: string, before: number, after: number) => ({
  company: { ...company, uid: `uid-${name}`, name },
  founded_on: "2021-03-01",
  raised_on: "2026-09-20",
  capital_before: before,
  capital_after: after,
  notice_url: "https://www.shab.ch/#!/search/publications/detail/n2",
  purpose_excerpt: "Entwicklung von ⟦Medtech⟧-Geräten",
});

it("loads on open and sorts by capital increase", async () => {
  const fetchMock = mockApi({
    "/api/targets": [target("Small AG", 100000, 101000), target("Big AG", 100000, 600000)],
  });
  render(<Targets onOpenCompany={() => {}} openedUid={null} />);

  await screen.findByRole("button", { name: "Big AG" });
  const rows = screen.getAllByRole("row").slice(1);

  expect(within(rows[0]).getByRole("button")).toHaveTextContent("Big AG");
  expect(within(rows[0]).getByText(/\+CHF.*500.000 \(\+500 %\)/)).toBeInTheDocument();
  expect(fetchedUrls(fetchMock)[0]).toBe(
    "/api/targets?q=medtech&founded_since=2020-01-01&raised_within_days=365",
  );
});

it("filters by minimum increase and reports the count", async () => {
  mockApi({
    "/api/targets": [target("Small AG", 100000, 101000), target("Big AG", 100000, 600000)],
  });
  render(<Targets onOpenCompany={() => {}} openedUid={null} />);
  await screen.findByRole("button", { name: "Small AG" });

  fireEvent.change(screen.getByLabelText(/Min. increase/), { target: { value: "50000" } });

  expect(screen.queryByRole("button", { name: "Small AG" })).not.toBeInTheDocument();
  expect(screen.getByText(/1 of 2 companies/)).toBeInTheDocument();
});

it("highlights where the purpose matched", async () => {
  mockApi({ "/api/targets": [target("Big AG", 100000, 600000)] });
  render(<Targets onOpenCompany={() => {}} openedUid={null} />);

  const mark = await screen.findByText("Medtech", { selector: "mark" });
  expect(mark.parentElement).toHaveTextContent("Entwicklung von Medtech-Geräten");
});

it("exports the increase without float artefacts and with the seat", async () => {
  mockApi({ "/api/targets": [target("Odd AG", 160825.0, 187658.32)] });
  const csv: string[] = [];
  vi.stubGlobal("URL", {
    ...URL,
    createObjectURL: (blob: Blob) => {
      void blob.text().then((text) => csv.push(text));
      return "blob:x";
    },
    revokeObjectURL: () => {},
  });
  render(<Targets onOpenCompany={() => {}} openedUid={null} />);

  fireEvent.click(await screen.findByRole("button", { name: /Export CSV/ }));
  await vi.waitFor(() => expect(csv).toHaveLength(1));

  const [header, row] = csv[0].replace("﻿", "").split("\r\n");
  expect(header).toContain("Seat;Canton");
  expect(row).toContain(";26833.32;");
});

import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { company, fetchedUrls, mockApi, notice } from "../test-api";
import { Leads } from "./Leads";

afterEach(() => vi.unstubAllGlobals());

const lead = {
  company,
  site_cantons: ["BS"],
  activities: ["Manufacturing"],
  last_change: "2026-10-12",
  notices: [notice, { ...notice, id: "n2", changes: ["other"] }],
};

it("loads with Basel-region defaults and opens the profile at the triggering notice", async () => {
  const fetchMock = mockApi({ "/api/leads": [lead] });
  const onOpen = vi.fn();
  render(<Leads onOpenCompany={onOpen} openedUid={null} />);

  fireEvent.click(await screen.findByRole("button", { name: "Alpenpharma AG" }));

  expect(fetchedUrls(fetchMock)[0]).toBe(
    "/api/leads?cantons=BS&cantons=BL&cantons=AG&days=90&activity=1&changes=board&changes=management",
  );
  expect(onOpen).toHaveBeenCalledWith("CHE-000.000.001", { healthOnly: false, noticeId: "n1" });
  expect(screen.getAllByRole("link", { name: "12.10.2026" })[0]).toHaveAttribute(
    "href",
    notice.url,
  );
});

it("sends no canton filter when none is selected (all cantons)", async () => {
  const fetchMock = mockApi({ "/api/leads": [] });
  render(<Leads onOpenCompany={() => {}} openedUid={null} />);
  await screen.findByText("No company matches these filters.");

  for (const name of ["Basel-Stadt", "Basel-Landschaft", "Aargau"]) {
    fireEvent.click(screen.getByRole("button", { name: `Remove ${name}` }));
  }
  fireEvent.click(screen.getByRole("button", { name: "Find leads" }));

  const url = new URL(fetchedUrls(fetchMock).at(-1)!, "http://x");
  expect(url.searchParams.getAll("cantons")).toEqual([]);
});

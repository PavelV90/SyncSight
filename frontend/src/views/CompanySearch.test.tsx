import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { company, fetchedUrls, mockApi } from "../test-api";
import { CompanySearch } from "./CompanySearch";

afterEach(() => vi.unstubAllGlobals());

it("explains short queries instead of ignoring them", () => {
  const fetchMock = mockApi({ "/api/companies": [] });
  render(<CompanySearch onOpenCompany={() => {}} openedUid={null} />);

  fireEvent.change(screen.getByLabelText(/Company name, keywords or UID/), {
    target: { value: "L" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));

  expect(screen.getByText("Enter at least 2 characters.")).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

it("searches with canton and limit and lists companies in a table", async () => {
  const fetchMock = mockApi({
    "/api/companies": [company, { ...company, uid: "u2", name: "Lonza AG", status: "inactive" }],
  });
  render(<CompanySearch onOpenCompany={() => {}} openedUid={null} />);

  fireEvent.change(screen.getByLabelText(/Company name, keywords or UID/), {
    target: { value: "pharma" },
  });
  fireEvent.change(screen.getByLabelText("Canton"), { target: { value: "BS" } });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));

  expect(await screen.findByRole("button", { name: "Lonza AG" })).toBeInTheDocument();
  expect(fetchedUrls(fetchMock)[0]).toBe("/api/companies?q=pharma&limit=100&canton=BS");
  expect(screen.getByText("2 companies for 'pharma' in BS")).toBeInTheDocument();
  expect(screen.getByText("inactive")).toHaveClass("chip--warning");
});

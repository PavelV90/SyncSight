import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { company, mesLead, mockApi } from "./test-api";

afterEach(() => vi.unstubAllGlobals());

const routes = {
  "/api/health": { status: "ok", version: "0.1.0" },
  "/api/mes-leads": [mesLead],
  "/api/leads": [],
  "/api/targets": [],
  [`/api/companies/${company.uid}`]: {
    ...company,
    purpose: null,
    address: null,
    sites: [],
    timeline: [],
  },
};

describe("App", () => {
  it("shows tabs with the MES leads tab selected", async () => {
    mockApi(routes);
    render(<App />);

    expect(await screen.findByText("v0.1.0")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "MES leads" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Leads" })).toHaveAttribute("aria-selected", "false");
  });

  it("returns from a profile to the same list without reloading it", async () => {
    const fetchMock = mockApi(routes);
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Alpenpharma AG" }));

    expect(await screen.findByRole("heading", { name: "Alpenpharma AG" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "← Back to MES leads" }));

    const link = screen.getByRole("button", { name: "Alpenpharma AG" });
    expect(link.closest("tr")).toHaveClass("row--opened");
    await vi.waitFor(() => expect(link).toHaveFocus());
    const mesCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).startsWith("/api/mes-leads"),
    );
    expect(mesCalls).toHaveLength(1);
  });

  it("moves between tabs with the arrow keys", async () => {
    mockApi(routes);
    render(<App />);
    const mes = await screen.findByRole("tab", { name: "MES leads" });

    fireEvent.keyDown(mes, { key: "ArrowRight" });

    const leads = screen.getByRole("tab", { name: "Leads" });
    expect(leads).toHaveAttribute("aria-selected", "true");
    expect(leads).toHaveFocus();
    expect(mes).toHaveAttribute("tabindex", "-1");
  });

  it("reports an unreachable backend with a retry", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<App />);

    expect(await screen.findByText(/Backend not reachable. Start SyncSight/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Retry" }).length).toBeGreaterThan(0);
  });
});

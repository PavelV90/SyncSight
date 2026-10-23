import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { mockApi } from "../test-api";
import { DataFreshness } from "./DataFreshness";

afterEach(() => vi.unstubAllGlobals());

it("flags stale and missing sources with the command that refreshes them", async () => {
  mockApi({
    "/api/status": [
      {
        key: "shab",
        label: "Register notices (SHAB)",
        rows: 12513,
        last_loaded_at: "2026-10-23T07:10:00Z",
        newest_record: "2026-10-23",
        stale: false,
        command: "shab",
      },
      {
        key: "permits",
        label: "Building permits",
        rows: 0,
        last_loaded_at: null,
        newest_record: null,
        stale: true,
        command: "permits",
      },
    ],
  });
  render(<DataFreshness />);

  fireEvent.click(await screen.findByText(/1 source stale/));

  expect(screen.getByText((12513).toLocaleString("de-CH"))).toBeInTheDocument();
  expect(screen.getByText("syncsight-ingest permits")).toBeInTheDocument();
  expect(screen.getByText("Building permits").closest("tr")).toHaveClass("warning");
});

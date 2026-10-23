import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { company, mockApi, notice } from "../test-api";
import { Leads } from "./Leads";

afterEach(() => vi.unstubAllGlobals());

it("queries leads with the default filters and opens a company", async () => {
  const fetchMock = mockApi({
    "/api/leads": [
      {
        company,
        site_cantons: ["BS"],
        activities: ["Manufacturing"],
        last_change: "2026-10-12",
        notices: [notice],
      },
    ],
  });
  const onOpen = vi.fn();
  render(<Leads onOpenCompany={onOpen} />);

  fireEvent.click(screen.getByRole("button", { name: "Find leads" }));
  fireEvent.click(await screen.findByRole("button", { name: "Alpenpharma AG" }));

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/leads?cantons=BS&cantons=BL&cantons=AG&days=90&activity=1",
  );
  expect(screen.getByRole("link", { name: "2026-10-12" })).toHaveAttribute("href", notice.url);
  expect(onOpen).toHaveBeenCalledWith("CHE-000.000.001");
});

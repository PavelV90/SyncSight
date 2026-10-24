import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { EvidenceList } from "./EvidenceList";

const permit = (n: number, points: number) => ({
  kind: "permit_other",
  on: `2026-0${n}-01`,
  title: `Permit ${n}`,
  detail: null,
  url: null,
  points,
});

it("lists counted items and collapses those over the cap", () => {
  render(
    <EvidenceList
      evidence={[permit(3, 1), permit(2, 0), permit(1, 0)]}
      breakdown={[{ kind: "permit_other", items: 3, counted: 1, points_each: 1, points: 1 }]}
    />,
  );

  expect(screen.getByText(/1 × 1 = 1 pt · 3 found/)).toBeInTheDocument();
  expect(screen.getByText("Permit 3")).toBeVisible();
  fireEvent.click(screen.getByText("2 more, not counted (cap reached)"));
  expect(screen.getByText("Permit 1")).toBeVisible();
});

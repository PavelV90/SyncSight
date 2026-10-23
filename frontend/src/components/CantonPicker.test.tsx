import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, it } from "vitest";

import { CantonPicker } from "./CantonPicker";

function Harness() {
  const [selected, setSelected] = useState<string[]>([]);
  return (
    <>
      <CantonPicker
        label="Cantons"
        selected={selected}
        onChange={setSelected}
        emptyLabel="All cantons"
      />
      <output>{selected.join(",")}</output>
    </>
  );
}

it("selects from the checklist, applies presets and removes chips", () => {
  render(<Harness />);
  expect(screen.getByText("All cantons")).toBeInTheDocument();

  fireEvent.click(screen.getByLabelText("ZG – Zug"));
  fireEvent.click(screen.getByLabelText("BS – Basel-Stadt"));
  expect(screen.getByText("BS,ZG", { selector: "output" })).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Filter cantons"), { target: { value: "gen" } });
  expect(screen.getByLabelText("GE – Genève")).toBeInTheDocument();
  expect(screen.queryByLabelText("ZH – Zürich")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Basel region" }));
  expect(screen.getByText("BS,BL,AG", { selector: "output" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Remove Basel-Landschaft" }));
  expect(screen.getByText("BS,AG", { selector: "output" })).toBeInTheDocument();
});

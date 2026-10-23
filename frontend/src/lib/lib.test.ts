import { describe, expect, it } from "vitest";

import { formatDate, formatRelative } from "../api";
import { toCsv } from "./csv";

describe("toCsv", () => {
  it("writes a BOM, semicolons and quotes only where needed", () => {
    const csv = toCsv(
      [{ name: 'Alpen "Pharma"; AG', n: 3 }],
      [
        { header: "Name", value: (r) => r.name },
        { header: "Count", value: (r) => r.n },
      ],
    );
    expect(csv).toBe('﻿Name;Count\r\n"Alpen ""Pharma""; AG";3\r\n');
  });
});

describe("dates", () => {
  it("formats Swiss dates and relative ages", () => {
    const today = new Date(2026, 9, 23);
    expect(formatDate("2026-10-20")).toBe("20.10.2026");
    expect(formatDate(null)).toBe("–");
    expect(formatRelative("2026-10-20", today)).toBe("3 days ago");
    expect(formatRelative("2026-04-23", today)).toBe("6 months ago");
  });
});

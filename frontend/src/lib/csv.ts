export type CsvColumn<T> = {
  header: string;
  value: (row: T) => string | number | null | undefined;
};

/** Semicolon-separated CSV with a UTF-8 BOM, so Excel (de-CH) opens it correctly. */
export function toCsv<T>(rows: T[], columns: CsvColumn<T>[]): string {
  const cell = (value: string | number | null | undefined) => {
    let text = value === null || value === undefined ? "" : String(value);
    // text starting with = + - @ would run as a formula in Excel
    if (typeof value === "string" && /^[=+\-@\t\r]/.test(text)) text = `'${text}`;
    return /[;"\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  const lines = [
    columns.map((c) => cell(c.header)).join(";"),
    ...rows.map((row) => columns.map((c) => cell(c.value(row))).join(";")),
  ];
  return "﻿" + lines.join("\r\n") + "\r\n";
}

export function downloadCsv(filename: string, content: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

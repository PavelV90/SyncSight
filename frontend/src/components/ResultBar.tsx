import { useState } from "react";

import { downloadCsv } from "../lib/csv";

type Props = {
  summary: string; // empty until the first result; the live region exists from the start
  csv?: () => { filename: string; content: string };
  uids?: string[];
};

/** Result summary (announced to screen readers) with export actions. */
export function ResultBar({ summary, csv, uids }: Props) {
  const [copy, setCopy] = useState<"idle" | "copied" | "failed">("idle");
  const copyUids = () => {
    if (!uids?.length) return;
    navigator.clipboard
      .writeText(uids.join("\n"))
      .then(() => setCopy("copied"))
      .catch(() => setCopy("failed"))
      .finally(() => window.setTimeout(() => setCopy("idle"), 2500));
  };
  const hasRows = Boolean(uids?.length);
  return (
    <div className="result-bar">
      <p role="status" className="result-summary">
        {summary}
      </p>
      <span role="status" className="sr-only">
        {copy === "copied" ? "UIDs copied" : copy === "failed" ? "Copying UIDs failed" : ""}
      </span>
      {hasRows && (
        <div className="toolbar">
          {csv && (
            <button
              type="button"
              onClick={() => {
                const { filename, content } = csv();
                downloadCsv(filename, content);
              }}
            >
              Export CSV ({uids?.length} rows)
            </button>
          )}
          <button type="button" onClick={copyUids}>
            {copy === "copied" ? "Copied ✓" : copy === "failed" ? "Copy failed" : "Copy UIDs"}
          </button>
        </div>
      )}
    </div>
  );
}

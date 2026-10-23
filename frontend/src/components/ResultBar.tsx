import { useState } from "react";

import { downloadCsv } from "../lib/csv";

type Props = {
  summary: string;
  csv?: () => { filename: string; content: string };
  uids?: string[];
};

/** Result summary (announced to screen readers) with export actions. */
export function ResultBar({ summary, csv, uids }: Props) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    if (!uids?.length) return;
    void navigator.clipboard.writeText(uids.join("\n")).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <div className="result-bar">
      <p role="status" className="result-summary">
        {summary}
      </p>
      <div className="toolbar">
        {csv && (
          <button
            type="button"
            disabled={!uids?.length}
            onClick={() => {
              const { filename, content } = csv();
              downloadCsv(filename, content);
            }}
          >
            Export CSV{uids?.length ? ` (${uids.length})` : ""}
          </button>
        )}
        {uids && (
          <button type="button" disabled={!uids.length} onClick={copy}>
            {copied ? "Copied ✓" : "Copy UIDs"}
          </button>
        )}
      </div>
    </div>
  );
}

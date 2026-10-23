import { useState } from "react";

type Props = { text: string | null; lines?: 2 | 3; minLength?: number; className?: string };

/** Long text cut to a few lines with a "Show more" toggle. */
export function Clamp({ text, lines = 3, minLength = 220, className = "" }: Props) {
  const [open, setOpen] = useState(false);
  if (!text) return null;
  if (text.length <= minLength) return <div className={className}>{text}</div>;
  return (
    <div className={className}>
      <div className={open ? "" : `clamp clamp--${lines}`}>{text}</div>
      <button
        type="button"
        className="link small"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {open ? "Show less" : "Show more"}
      </button>
    </div>
  );
}

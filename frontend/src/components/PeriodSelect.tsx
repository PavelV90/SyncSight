import { useId } from "react";

export const PERIODS: Array<[number, string]> = [
  [30, "Last 30 days"],
  [90, "Last 90 days"],
  [182, "Last 6 months"],
  [365, "Last year"],
  [730, "Last 2 years"],
  [1096, "Last 3 years"],
  [1826, "Last 5 years"],
  [3652, "Last 10 years"],
  [7305, "Last 20 years"],
];

type Props = {
  value: number; // days
  onChange: (days: number) => void;
  options?: number[]; // subset of PERIODS (days)
  label?: string;
};

/** One look-back control for all views; each view converts days to its API unit. */
export function PeriodSelect({ value, onChange, options, label = "Period" }: Props) {
  const id = useId();
  const periods = options ? PERIODS.filter(([days]) => options.includes(days)) : PERIODS;
  return (
    <label htmlFor={id}>
      {label}
      <select id={id} value={value} onChange={(e) => onChange(Number(e.target.value))}>
        {periods.map(([days, text]) => (
          <option key={days} value={days}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

export const periodLabel = (days: number) =>
  (PERIODS.find(([d]) => d === days)?.[1] ?? `Last ${days} days`).toLowerCase();

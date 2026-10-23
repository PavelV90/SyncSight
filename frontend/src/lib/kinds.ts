import type { KindScore } from "../api";

// MES evidence kinds as shown to users (backend: syncsight/db/mes.py)
export const KINDS: Record<string, string> = {
  web_mes: "MES on website",
  web_hiring: "Hiring for MES",
  web_vendor: "MES vendor named",
  permit_production: "Production building permit",
  permit_other: "Building permit",
  licence_change: "Licence change",
  web_expansion: "Expansion news",
  web_digital: "Digitalisation news",
  management_change: "Management change",
  capital_raise: "Capital increase",
  new_medicine: "New medicines",
};
export const kindLabel = (kind: string) => KINDS[kind] ?? kind;

/** "Production building permit 2×3 · Management change 1×1 = 7" */
export function breakdownText(breakdown: KindScore[], score: number): string {
  const parts = breakdown
    .filter((k) => k.points > 0)
    .map((k) => `${kindLabel(k.kind)} ${k.counted}×${k.points_each}`);
  return `${parts.join(" · ")} = ${score}`;
}

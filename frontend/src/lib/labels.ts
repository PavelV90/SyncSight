// Display labels shared by views. Keys mirror the backend (shab.py change labels, mes.py kinds).

export const CANTONS: Array<[string, string]> = [
  ["AG", "Aargau"],
  ["AI", "Appenzell Innerrhoden"],
  ["AR", "Appenzell Ausserrhoden"],
  ["BE", "Bern"],
  ["BL", "Basel-Landschaft"],
  ["BS", "Basel-Stadt"],
  ["FR", "Fribourg"],
  ["GE", "Genève"],
  ["GL", "Glarus"],
  ["GR", "Graubünden"],
  ["JU", "Jura"],
  ["LU", "Luzern"],
  ["NE", "Neuchâtel"],
  ["NW", "Nidwalden"],
  ["OW", "Obwalden"],
  ["SG", "St. Gallen"],
  ["SH", "Schaffhausen"],
  ["SO", "Solothurn"],
  ["SZ", "Schwyz"],
  ["TG", "Thurgau"],
  ["TI", "Ticino"],
  ["UR", "Uri"],
  ["VD", "Vaud"],
  ["VS", "Valais"],
  ["ZG", "Zug"],
  ["ZH", "Zürich"],
];
export const CANTON_CODES = CANTONS.map(([code]) => code);
export const BASEL_REGION = ["BS", "BL", "AG"];

// Swissmedic licence activities (backend: ingestion/swissmedic.py ACTIVITIES)
export const ACTIVITIES: Array<[number, string]> = [
  [1, "Manufacturing"],
  [3, "API manufacturing"],
  [2, "Import"],
  [4, "Wholesale"],
  [5, "Export"],
  [6, "Trade abroad"],
  [7, "Broker or agent"],
  [8, "Blood products"],
];

// SHAB change labels (backend: ingestion/shab.py)
export const CHANGES: Array<[string, string]> = [
  ["board", "Board"],
  ["management", "Management"],
  ["auditor", "Auditor"],
  ["capital", "Capital"],
  ["seat", "Seat"],
  ["address", "Address"],
  ["name", "Name"],
  ["purpose", "Purpose"],
  ["legal_form", "Legal form"],
  ["liquidation", "Liquidation"],
  ["bankruptcy", "Bankruptcy"],
  ["registration", "Registration"],
  ["deletion", "Deletion"],
  ["other", "Other"],
];
const CHANGE_LABELS = Object.fromEntries(CHANGES);
export const changeLabel = (key: string) => CHANGE_LABELS[key] ?? key;

// Register events that signal financial health (backend: db/queries.py HEALTH_CHANGES)
export const HEALTH_CHANGES = new Set([
  "capital",
  "auditor",
  "seat",
  "liquidation",
  "bankruptcy",
  "deletion",
]);
export const WARNINGS = new Set(["bankruptcy", "liquidation", "deletion"]);

/** Change chips to show: "other" only when it is the only change. */
export function visibleChanges(changes: string[]): string[] {
  const specific = changes.filter((c) => c !== "other");
  return specific.length ? specific : changes;
}

export const RUBRICS: Record<string, string> = {
  HR01: "Registration",
  HR02: "Change",
  HR03: "Deletion",
};

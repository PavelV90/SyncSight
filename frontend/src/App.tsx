import { useEffect, useState } from "react";

import { getJson } from "./api";
import { CompanyProfile } from "./views/CompanyProfile";
import { CompanySearch } from "./views/CompanySearch";
import { Leads } from "./views/Leads";
import { Targets } from "./views/Targets";

type Health = { status: string; version: string };
type Tab = "leads" | "targets" | "company";

const TABS: Array<[Tab, string]> = [
  ["leads", "Leads"],
  ["targets", "Investment targets"],
  ["company", "Company check"],
];

export default function App() {
  const [tab, setTab] = useState<Tab>("leads");
  const [openUid, setOpenUid] = useState<string | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getJson<Health>("/api/health")
      .then(setHealth)
      .catch(() => setFailed(true));
  }, []);

  let status = "Checking API…";
  if (failed) status = "API unreachable";
  else if (health) status = `API ${health.status} (v${health.version})`;

  return (
    <div className="app">
      <header>
        <h1>SyncSight</h1>
        <span className="muted">Swiss company intelligence</span>
        <span role="status" className="api-status">
          {status}
        </span>
      </header>
      <nav>
        {TABS.map(([key, label]) => (
          <button
            key={key}
            className={tab === key && !openUid ? "tab active" : "tab"}
            onClick={() => {
              setTab(key);
              setOpenUid(null);
            }}
          >
            {label}
          </button>
        ))}
      </nav>
      <main>
        {openUid ? (
          <CompanyProfile uid={openUid} onBack={() => setOpenUid(null)} />
        ) : (
          <>
            <div hidden={tab !== "leads"}>
              <Leads onOpenCompany={setOpenUid} />
            </div>
            <div hidden={tab !== "targets"}>
              <Targets onOpenCompany={setOpenUid} />
            </div>
            <div hidden={tab !== "company"}>
              <CompanySearch onOpenCompany={setOpenUid} />
            </div>
          </>
        )}
      </main>
      <footer className="muted">
        Sources: Zefix (Federal Commercial Registry Office, via LINDAS), SHAB/SOGC (SECO,
        amtsblattportal.ch), Swissmedic establishment licences (opendata.swiss).
      </footer>
    </div>
  );
}

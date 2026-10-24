import { useCallback, useEffect, useRef, useState } from "react";

import { getJson } from "./api";
import { DataFreshness } from "./components/DataFreshness";
import { ErrorBoundary } from "./components/ErrorBoundary";
import type { OpenCompany, OpenOptions } from "./lib/navigation";
import { CompanyProfile } from "./views/CompanyProfile";
import { CompanySearch } from "./views/CompanySearch";
import { Leads } from "./views/Leads";
import { MesLeads } from "./views/MesLeads";
import { Targets } from "./views/Targets";

type Health = { status: string; version: string };
type Tab = "mes" | "leads" | "targets" | "company";
type OpenProfile = { uid: string; options: OpenOptions };

const TABS: Array<[Tab, string]> = [
  ["mes", "MES leads"],
  ["leads", "Leads"],
  ["targets", "Investment targets"],
  ["company", "Company check"],
];
const tabLabel = (tab: Tab) => TABS.find(([key]) => key === tab)?.[1] ?? "";

export default function App() {
  const [tab, setTab] = useState<Tab>("mes");
  const [profile, setProfile] = useState<OpenProfile | null>(null);
  const [lastOpened, setLastOpened] = useState<string | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [offline, setOffline] = useState(false);
  const listScroll = useRef(0);

  const checkHealth = useCallback(() => {
    getJson<Health>("/api/health")
      .then((h) => {
        setHealth(h);
        setOffline(false);
      })
      .catch(() => setOffline(true));
  }, []);
  useEffect(checkHealth, [checkHealth]);

  const openCompany: OpenCompany = (uid, options = {}) => {
    listScroll.current = window.scrollY;
    setLastOpened(uid);
    setProfile({ uid, options });
    window.scrollTo({ top: 0 });
  };
  const closeProfile = () => {
    setProfile(null);
    // the list stayed mounted: return to where the user was and focus the company they opened
    requestAnimationFrame(() => {
      window.scrollTo({ top: listScroll.current });
      document
        .querySelector<HTMLElement>(`#panel-${tab} [data-uid="${lastOpened}"]`)
        ?.focus({ preventScroll: true });
    });
  };

  const views: Array<[Tab, React.ReactNode]> = [
    ["mes", <MesLeads key="mes" onOpenCompany={openCompany} openedUid={lastOpened} />],
    ["leads", <Leads key="leads" onOpenCompany={openCompany} openedUid={lastOpened} />],
    ["targets", <Targets key="targets" onOpenCompany={openCompany} openedUid={lastOpened} />],
    ["company", <CompanySearch key="company" onOpenCompany={openCompany} openedUid={lastOpened} />],
  ];

  return (
    <div className="app">
      <header>
        <h1>SyncSight</h1>
        <span className="muted">Swiss company intelligence</span>
        <span className="api-status">
          {!offline && <DataFreshness />}
          <span className="muted small">{health ? ` v${health.version}` : ""}</span>
        </span>
      </header>
      {offline && (
        <div role="alert" className="banner">
          Backend not reachable. Start SyncSight with start.command, then{" "}
          <button type="button" onClick={checkHealth}>
            Retry
          </button>
        </div>
      )}
      <div role="tablist" aria-label="Views" className="tabs">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            id={`tab-${key}`}
            type="button"
            role="tab"
            aria-selected={tab === key}
            aria-controls={`panel-${key}`}
            className={tab === key ? "tab active" : "tab"}
            onClick={() => {
              setTab(key);
              setProfile(null);
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <main>
        {/* list views stay mounted while a profile is open, so Back keeps filters and results */}
        <div hidden={profile !== null}>
          {views.map(([key, view]) => (
            <div
              key={key}
              id={`panel-${key}`}
              role="tabpanel"
              aria-labelledby={`tab-${key}`}
              hidden={tab !== key}
            >
              <ErrorBoundary name={tabLabel(key)}>{view}</ErrorBoundary>
            </div>
          ))}
        </div>
        {profile && (
          <ErrorBoundary name="Company profile">
            <CompanyProfile
              key={profile.uid}
              uid={profile.uid}
              options={profile.options}
              from={tabLabel(tab)}
              onBack={closeProfile}
            />
          </ErrorBoundary>
        )}
      </main>
      <footer className="muted small">
        Sources: Zefix (Federal Commercial Registry Office, via LINDAS), SHAB/SOGC and cantonal
        gazettes (SECO, amtsblattportal.ch), Swissmedic licences and medicines (opendata.swiss),
        Wikidata, company websites.
      </footer>
    </div>
  );
}

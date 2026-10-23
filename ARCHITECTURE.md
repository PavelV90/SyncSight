# SyncSight — Architecture

> Living document. Status: **MVP search** (2026-10-23). Every architecture decision goes into the [decision log](#decision-log).

## Overview

MVP = search, filters and scoring over free official Swiss data. **No LLM, CHF 0 running cost, runs locally** (Docker Compose), so all data stays on the developer's machine in Switzerland.

```
 Zefix (REST/LINDAS) ─┐
 SHAB/SOGC (API)     ─┼─► ingestion jobs (Python) ─► PostgreSQL 18 ─► FastAPI ─► React SPA
 Swissmedic (XLSX)   ─┘        parse, match on UID      facts + full-text     /api/*     search UI
```

## Components

| Layer | Tech | Code |
|---|---|---|
| Ingestion | Python 3.13, httpx2, defusedxml, openpyxl; one module per source; CLI `syncsight-ingest` | `backend/src/syncsight/ingestion/` |
| Storage | PostgreSQL 18, SQLAlchemy 2, Alembic; full-text search (`simple` config, multilingual) | `backend/src/syncsight/db/`, `backend/migrations/` |
| API | FastAPI: `/api/companies`, `/api/companies/{uid}`, `/api/leads`, `/api/targets` (OpenAPI docs at `/docs`) | `backend/src/syncsight/api/` |
| UI | React 19 + TypeScript + Vite (SPA): Leads, Investment targets, Company check | `frontend/` |
| Dev / CI | Docker Compose, uv, npm, GitHub Actions | `compose.yaml`, `.github/workflows/ci.yml` |

Entity key: the company **UID** (`CHE-xxx.xxx.xxx`). Sources without a UID (Swissmedic) are matched on name and address.

## MVP data sources

| Source | Access | Licence / legal basis | Rules we follow |
|---|---|---|---|
| [Zefix](https://www.zefix.admin.ch/ZefixPublicREST/v3/api-docs): name, UID, legal form, seat, purpose, capital, auditor, status Bulk: [LINDAS SPARQL](https://opendata.swiss/en/dataset/zefix-zentraler-firmenindex), one CSV query per canton (~796k active companies, 5 min). Details: REST (free credentials, not used yet) | OGD "open use, must provide the source"; [HRegV Art. 14](https://www.fedlex.admin.ch/eli/cc/2007/686/de#art_14), [OR Art. 936](https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de#art_936) | Attribute the source |
| [SHAB/SOGC](https://www.amtsblattportal.ch/api/v1/publications) notices: register changes, liquidations, bankruptcies | Public REST API: list by date range or keyword (a UID gives one company's history), then one XML per notice; 0.2 s between requests. Rubric HR only | Public register data; personal data generally accessible ([revDSG Art. 30(3)](https://www.fedlex.admin.ch/eli/cc/2022/491/de#art_30)); portal terms of use to be confirmed with SECO Notice text is never full-text indexed; no search by person name. HR notices stay public (register, [OR Art. 936](https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de#art_936)). Delete a notice once the portal withdraws it; bankruptcy-office notices (rubric KK, not ingested) only for 5 years ([VSHAB Art. 11](https://www.fedlex.admin.ch/eli/cc/2006/78/de#art_11)) |
| [Swissmedic establishment licences](https://opendata.swiss/en/dataset/betriebsbewilligungen): ~1,270 pharma sites, activities, last inspection, compliance | XLSX download, full snapshot each run; holders linked to companies by normalised name (postal code breaks ties) | OGD "open use" | Attribute the source |

Deferred: **company reports**. Only listed companies and bond issuers must publish accounts ([OR Art. 958e](https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de#art_958_e)). Copying reports wholesale risks [URG](https://www.fedlex.admin.ch/eli/cc/1993/1798_1798_1798/de#art_24_d) and [UWG Art. 5c](https://www.fedlex.admin.ch/eli/cc/1988/223_223_223/de#art_5). Links and individual facts are fine.

## MVP use cases

1. **Leads:** "Which Swissmedic-licensed drug manufacturers in BS, BL or AG changed board or management in the last 90 days?" (Swissmedic + Zefix + SHAB)
2. **Investment targets:** "Which companies founded since 2020 with 'medtech' in their purpose raised capital in the last 12 months?" (Zefix + SHAB)
3. **Health check:** "What changed at company X in the last 5 years: capital, auditor, seat, liquidation or bankruptcy?" (Zefix + SHAB timeline, every item linked to its notice)

"Health" means warning signs from register events. Private companies publish no financials.

How each one is answered:
1. **Leads:** licence sites in the chosen cantons with the chosen activity (default: manufacturing), joined to SHAB notices labelled `board` or `management` in the last N days.
2. **Targets:** full-text match on purpose. Founding date = the company's HR01 notice. A raise = a notice whose capital exceeds the capital stated in the company's previous notice.
3. **Health check:** company timeline filtered to `capital`, `auditor`, `seat`, `liquidation`, `bankruptcy`, `deletion`, showing capital before → after.

Change labels come from two places: structured XML flags (capital, seat, name, purpose, address, liquidation, bankruptcy, registration, deletion) and regex rules on the DE/FR/IT notice text (board, management, auditor). The text rules ignore the company name and purpose.

## Current state and next steps

Done:
- Skeleton per layer, Docker Compose, CI.
- Search API and UI for the three use cases.
- Ingestion (`syncsight-ingest`, see README):
  - Zefix: all 795,744 active companies.
  - SHAB: daily pull, plus per-company history.
  - Swissmedic: 1,271 sites, 949 of 997 holders linked.
- Tables `company`, `sogc_notice`, `swissmedic_site`.

Next:
1. Daily `zefix` + `shab` runs (cron or a scheduler container).
2. Measure precision of the text rules on a labelled sample, then refine them.
3. Retention job: delete notices the portal no longer serves.
4. Use case 2 only covers companies whose history is loaded. Widen it with HR01 backfill or Zefix REST.
5. Later: Zefix REST for founding date and capital of companies without SHAB history; LLM chat (D5); company reports (D9).

## Decision log

### D1 · 2026-10-22 · Private repository, no licence (visibility superseded by D10)
- **Context:** commercial product.
- **Options:** open source; private, all rights reserved.
- **Choice:** private GitHub repo `PavelV90/SyncSight`, no licence; Python `.gitignore` template (extended for Node).
- **Consequence:** no reuse by third parties without permission.

### D2 · 2026-10-22 · Zero running cost
- **Context:** founder requirement: the product must run 100 % free, on free data only.
- **Options:** paid Swiss cloud (Azure Switzerland North, Infomaniak); free tiers (Oracle Always Free, Supabase free); local-first.
- **Choice:** free/open-source software and free public data only.
- **Consequence:** no paid APIs, clouds or LLM tokens. Free tiers were rejected: Supabase caps the DB at 500 MB and pauses projects; Oracle reclaims idle VMs and needs a credit card.

### D3 · 2026-10-22 · Local-first hosting
- **Context:** D2 plus Swiss data residency.
- **Options:** Azure Switzerland North; Infomaniak; Oracle Always Free; local Docker.
- **Choice:** Docker Compose on the developer's machine.
- **Consequence:** CHF 0, and data stays in Switzerland. Single user, available only while the machine runs. Public hosting is an open decision.

### D4 · 2026-10-22 · Python 3.13 + FastAPI backend
- **Context:** ingestion, parsing and the API share one language and codebase.
- **Options:** FastAPI; Django.
- **Choice:** FastAPI, SQLAlchemy 2, Alembic, pydantic-settings; dependencies managed with uv.
- **Consequence:** async-ready API (streaming later). No built-in admin or auth: add when needed.

### D5 · 2026-10-22 · No LLM in the MVP
- **Context:** D2. No free hosted LLM is allowed for Swiss users (the Gemini free tier is barred for apps serving CH/EEA/UK users). A local 8B model is weak at reasoning.
- **Options:** paid API in a Swiss region; local Ollama (Qwen3 8B); none.
- **Choice:** none. The MVP is search, filters and rule-based scoring.
- **Consequence:** no chat UI yet. An LLM can be added later behind an OpenAI-compatible interface.

### D6 · 2026-10-22 · PostgreSQL 18 with built-in full-text search
- **Context:** structured facts plus text search over names and purposes; no embeddings without an LLM.
- **Options:** Postgres + pgvector; Postgres + Qdrant; Postgres full-text search only.
- **Choice:** Postgres full-text search, `simple` config (DE/FR/IT mixed, no stemming).
- **Consequence:** one database, no vector store yet. German compounds don't match partial words (e.g. "Medizintechnik" vs "medtech"). Add pgvector together with an LLM.

### D7 · 2026-10-22 · React + TypeScript + Vite SPA
- **Context:** app behind a login, no SEO need.
- **Options:** Vite SPA; Next.js.
- **Choice:** Vite SPA, React 19, Vitest.
- **Consequence:** static build with minimal ops. TypeScript pinned to 6.0 because typescript-eslint does not support 7 yet.

### D8 · 2026-10-22 · Tooling and CI
- **Context:** small team; checks must be cheap and identical locally and in CI.
- **Options:** pre-commit hooks; Makefile + CI.
- **Choice:** ruff (lint + format), strict mypy, pytest; ESLint, Prettier, Vitest; `make check`; GitHub Actions (free 2,000 min/month on private repos).
- **Consequence:** CI fails if Postgres-backed tests can't run (`SYNCSIGHT_REQUIRE_DB=1`). Local dev ports: DB 5433, API 8010, web 5173.

### D9 · 2026-10-22 · MVP data sources
- **Context:** D2 (free data only), plus revDSG, copyright and unfair-competition law.
- **Options:** Zefix, SHAB/SOGC, Swissmedic, UID register, company reports, other web scraping.
- **Choice:** Zefix, SHAB/SOGC, Swissmedic. Company reports deferred. UID register not used (public service allows restricted single queries; Zefix already provides the UID).
- **Consequence:** no financial statements for private companies. Retention and no-person-search rules apply to SHAB (see sources table). The SHAB portal terms need confirmation from SECO.

### D10 · 2026-10-22 · Public repository, still no licence
- **Context:** founder made the GitHub repo public.
- **Options:** keep private; public without licence; public with an open-source licence.
- **Choice:** public, no licence, so all rights stay reserved.
- **Consequence:** code is visible but not licensed for reuse. Never commit secrets (Zefix credentials go in `.env`, which is gitignored) or harvested data. GitHub Actions minutes are free on public repos.

### D11 · 2026-10-22 · Zefix bulk load via LINDAS, one query per canton
- **Context:** need all active companies with purpose and address. The Zefix REST API needs credentials and works per company.
- **Options:** Zefix REST; LINDAS with ORDER BY/OFFSET paging (60–80 s per 10k rows); LINDAS one CSV query per canton.
- **Choice:** one CSV query per canton, plus one for entities without a canton; upsert. After a full run, entities missing from it are marked `inactive`.
- **Consequence:** full load in about 5 minutes. LINDAS has no founding date, capital or history; those come from SHAB (later Zefix REST).

### D12 · 2026-10-22 · SHAB: daily pull plus targeted company histories
- **Context:** the list API returns metadata only. About 1,000 HR notices per day; 2.3M in the archive (since late 2019).
- **Options:** full archive backfill (days of requests); daily pull plus history only for companies of interest.
- **Choice:** daily pull by date range, plus full history per company via `keyword=<UID>`; 0.2 s between requests; skip stored notices.
- **Consequence:** polite load, at most about 5 requests/s. Founding date and capital history exist only for companies whose history was fetched or that changed after pulls started.

### D13 · 2026-10-22 · Swissmedic holders linked by exact normalised name
- **Context:** the licence list has no UID; holder names follow the commercial register.
- **Options:** fuzzy matching; exact normalised name with a postal-code tie-break; manual mapping.
- **Choice:** exact normalised name (case, quotes, spacing ignored); postal code decides between namesakes; otherwise unlinked.
- **Consequence:** precision over recall: 949 of 997 holders linked. The unlinked ones are mostly public bodies (not in the register) or names with extra address text.

### D14 · 2026-10-23 · Board, management and auditor changes from regex rules on notice text
- **Context:** the SHAB XML only flags structural changes. Changes of persons and auditors are in the free text (DE/FR/IT).
- **Options:** regex rules on register wording; ML/LLM classification (excluded by D5); no labels.
- **Choice:** case-insensitive regex per label, matched after removing the company name and purpose. Labels are stored with the structured flags; `reclassify` re-applies them.
- **Consequence:** cheap and explainable; precision not yet measured. A purpose change that names "Verwaltungsrat" outside the purpose field can still mislabel.

### D15 · 2026-10-23 · Definitions behind use cases 2 and 3
- **Context:** free data has no founding-date field and no financials.
- **Options:** Zefix REST (needs credentials); derive from SHAB notices.
- **Choice:** founding date = HR01 notice. Capital raise = notice capital above the previous notice's capital. Health = register events (capital, auditor, seat, liquidation, bankruptcy, deletion).
- **Consequence:** only companies registered since late 2019 (portal start) can have a founding date, which fits "founded since 2020". Results cover only companies whose history is loaded.

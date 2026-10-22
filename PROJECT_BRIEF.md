# SyncSight — Project Brief

## Vision
SyncSight is a corporate intelligence platform that maps, screens and aggregates the **entire Swiss company landscape**, and makes that knowledge queryable through a natural-language chat assistant.

## Users
- **Investors**: find and vet investment targets
- **Consultants**: discover warm leads (e.g. selling MES consulting for **Tulip** or **PharmaSuite**)
- **Business development managers**: find strategic partners

## Core capabilities
1. **Continuous data harvesting** across the Swiss market:
   - Corporate financials
   - Annual / yearly reports
   - Strategic roadmaps and future visions
   - Executive insights (interviews, statements, leadership changes)
2. **Aggregated knowledge base**: entity-resolved company profiles (structured data + documents).
3. **Conversational assistant (core UI)**: users ask in natural language to:
   - Evaluate the **financial health** of specific firms
   - Pinpoint **ideal investment targets**
   - Discover **warm consulting leads** (buying signals such as digitalization plans, new plants, GMP/quality initiatives, MES/MOM projects)
   - Identify **strategic partners** based on future/strategic alignment

## Working model
- Co-created by the founder (Pavel) and Claude as **lead software engineer and product architect**.
- Claude's scope: system architecture, data ingestion pipelines, conversational LLM framework.

## MVP scope (approved 2026-10-22)
- **No LLM** in the MVP: search, filters and scoring. The chat assistant comes later.
- **Sources:** Zefix (commercial register), SHAB/SOGC notices, Swissmedic establishment licences. Company reports deferred.
- **Use cases:**
  1. Leads: Swissmedic-licensed manufacturers (BS/BL/AG) with a board or management change in the last 90 days.
  2. Investment targets: companies founded since 2020 with "medtech" in their purpose that raised capital in the last 12 months.
  3. Health check: 5-year timeline of capital, auditor, seat, liquidation and bankruptcy events for a company.
- Details and rationale: `ARCHITECTURE.md`.

## Constraints and considerations (to be refined)
- **Zero cost:** only free/open-source software and free public data; no paid services (2026-10-22).
- Commercial product; the repo is **private**, all rights reserved (no license).
- Swiss/EU data protection (revDSG / GDPR); consider Swiss data residency.
- Respect source terms of use and robots.txt when harvesting; prefer official and open sources (e.g. Zefix / commercial register, SHAB/SOGC, company websites, published reports).
- Answers must be **source-cited** and traceable to underlying documents.

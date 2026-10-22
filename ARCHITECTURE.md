# SyncSight — Architecture

> Living document. Status: **not yet designed**. First design session pending.

## Planned components (draft)
1. **Ingestion layer**: connectors and crawlers per source, scheduling, raw document store.
2. **Processing layer**: parsing (PDF/HTML), extraction (financials, entities, signals), entity resolution against the commercial register (UID).
3. **Knowledge layer**: relational DB (structured facts) + vector index (documents) + optional graph (relationships).
4. **Intelligence layer**: scoring models (financial health, lead fit, partner alignment).
5. **Conversational layer**: LLM agent with tools (SQL/search/RAG), citations, guardrails.
6. **Application layer**: API + chat web UI, auth, multi-tenant accounts.

## Open questions
- Core stack (backend: Python likely; frontend: TBD)
- Cloud provider and Swiss data residency
- LLM provider and hosting
- MVP scope and first data sources

## Decision log
| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| 1 | 2026-10-22 | Private GitHub repo `PavelV90/SyncSight`, no license | Commercial product, all rights reserved |
| 2 | 2026-10-22 | Python `.gitignore` template | Backend/data pipelines likely in Python |

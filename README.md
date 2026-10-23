# SyncSight
Corporate intelligence platform that screens the (Swiss) business landscape, allowing the user to chat directly with interconnected market data to identify synergies between the user and the selected companies.

See `PROJECT_BRIEF.md` (what and why) and `ARCHITECTURE.md` (how, decision log).

## Run locally

Requires Docker. For running checks outside Docker: [uv](https://docs.astral.sh/uv/) and Node 24+.

On a Mac, double-click `start.command` (starts Docker Desktop if needed, then opens the app) and `stop.command`. Or from a terminal:

```bash
docker compose up --build
```

- Web: http://localhost:5173 (tabs: MES leads, Leads, Investment targets, Company check)
- API: http://localhost:8010/docs
- Postgres: `localhost:5433` (user/password `syncsight`)

## Load data

Start the database (`docker compose up -d db`), then from `backend/`:

```bash
uv run alembic upgrade head
```

```bash
uv run syncsight-ingest zefix
```

```bash
uv run syncsight-ingest swissmedic
```

```bash
uv run syncsight-ingest shab --since 2026-10-01
```

```bash
uv run syncsight-ingest shab-swissmedic
```

1. `zefix`: all active companies from Zefix via LINDAS, a few minutes. `--canton ZH` loads one canton.
2. `swissmedic`: licensed pharma sites, linked to companies by name.
3. `shab`: commercial-register notices in a date range (default: yesterday and today). `--uid CHE-…` fetches one company's full history.
4. `shab-swissmedic`: full notice history of every company linked to a Swissmedic licence. This takes hours, at about 5 requests per second.

MES signals (monthly):

```bash
uv run syncsight-ingest medicines && uv run syncsight-ingest permits
```

```bash
uv run syncsight-ingest websites && uv run syncsight-ingest crawl
```

`websites` finds and verifies company websites. `crawl` scans them, plus feeds and career pages, for MES keywords, politely: it respects robots.txt and waits 2 s between requests to the same host. Block domains with `SYNCSIGHT_CRAWL_BLOCKLIST='["example.ch"]'`.

After changing the notice text rules, run `uv run syncsight-ingest reclassify`.

Run `zefix` daily and `shab` daily to stay current. Sources and licences are listed in `ARCHITECTURE.md`.

## Checks

```bash
make install
```

```bash
docker compose up -d db
```

```bash
make check
```

Without a running database, the DB tests are skipped locally. CI always runs them.

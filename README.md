# SyncSight
Corporate intelligence platform that screens the (Swiss) business landscape, allowing the user to chat directly with interconnected market data to identify synergies between the user and the selected companies.

See `PROJECT_BRIEF.md` (what and why) and `ARCHITECTURE.md` (how, decision log).

## Run locally

Requires Docker. For running checks outside Docker: [uv](https://docs.astral.sh/uv/) and Node 24+.

```bash
docker compose up --build
```

- Web: http://localhost:5173
- API: http://localhost:8010/docs
- Postgres: `localhost:5433` (user/password `syncsight`)

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

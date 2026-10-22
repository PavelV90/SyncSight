"""FastAPI application entry point."""

from fastapi import FastAPI

from syncsight import __version__

app = FastAPI(title="SyncSight API", version=__version__)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}

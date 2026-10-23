"""FastAPI application entry point."""

from collections.abc import Iterator
from datetime import date, timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from syncsight import __version__
from syncsight.api import schemas
from syncsight.db import queries
from syncsight.db.models import Company
from syncsight.db.session import make_engine
from syncsight.ingestion.normalize import normalize_uid
from syncsight.ingestion.shab import PUBLIC_URL
from syncsight.ingestion.swissmedic import ACTIVITIES

app = FastAPI(title="SyncSight API", version=__version__)


@lru_cache
def _engine() -> Engine:
    return make_engine()


def get_session() -> Iterator[Session]:
    with Session(_engine()) as session:
        yield session


DbSession = Annotated[Session, Depends(get_session)]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/companies")
def search_companies(
    session: DbSession,
    q: Annotated[str, Query(min_length=2)],
    canton: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[schemas.CompanySummary]:
    """Full-text search over company names and purposes (use `or`, quotes, `-word`)."""
    uid = normalize_uid(q)
    if uid:
        company = session.get(Company, uid)
        return [schemas.CompanySummary.of(company)] if company else []
    return [
        schemas.CompanySummary.of(c) for c in queries.search_companies(session, q, canton, limit)
    ]


@app.get("/api/companies/{uid}")
def company_profile(
    session: DbSession,
    uid: str,
    years: Annotated[int, Query(ge=1, le=20)] = 5,
    health_only: bool = False,
) -> schemas.CompanyProfile:
    """Use case 3: company profile with its register timeline (health events on request)."""
    company = session.get(Company, normalize_uid(uid) or uid)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    since = date.today() - timedelta(days=365 * years)
    changes = queries.HEALTH_CHANGES if health_only else None
    timeline = queries.company_timeline(session, company.uid, since=since, changes=changes)
    summary = schemas.CompanySummary.of(company)
    address = ", ".join(p for p in (company.street, _place(company)) if p) or None
    return schemas.CompanyProfile(
        **summary.model_dump(),
        purpose=company.purpose,
        address=address,
        sites=[schemas.Site.of(s) for s in queries.company_sites(session, company.uid)],
        timeline=[
            schemas.Notice.of(e.notice, schemas.as_float(e.previous_capital)) for e in timeline
        ],
    )


@app.get("/api/leads")
def swissmedic_leads(
    session: DbSession,
    cantons: Annotated[list[str], Query()] = ["BS", "BL", "AG"],  # noqa: B006
    days: Annotated[int, Query(ge=1, le=3650)] = 90,
    activity: Annotated[list[int], Query()] = [1],  # noqa: B006
    changes: Annotated[list[str], Query()] = ["board", "management"],  # noqa: B006
) -> list[schemas.Lead]:
    """Use case 1: Swissmedic-licensed companies with board or management changes."""
    leads = queries.swissmedic_leads(
        session,
        cantons=cantons,
        since=date.today() - timedelta(days=days),
        activity_codes=activity,
        changes=changes,
    )
    return [
        schemas.Lead(
            company=schemas.CompanySummary.of(lead.company),
            site_cantons=lead.site_cantons,
            activities=[ACTIVITIES[c] for c in lead.activity_codes if c in ACTIVITIES],
            last_change=lead.notices[0].publication_date,
            notices=[schemas.Notice.of(n) for n in lead.notices],
        )
        for lead in leads
    ]


@app.get("/api/targets")
def investment_targets(
    session: DbSession,
    q: Annotated[str, Query(min_length=2)] = "medtech",
    founded_since: date = date(2020, 1, 1),
    raised_within_days: Annotated[int, Query(ge=1, le=3650)] = 365,
) -> list[schemas.Target]:
    """Use case 2: young companies matching `q` that raised capital recently."""
    targets = queries.investment_targets(
        session,
        query=q,
        founded_since=founded_since,
        raised_since=date.today() - timedelta(days=raised_within_days),
    )
    return [
        schemas.Target(
            company=schemas.CompanySummary.of(t.company),
            founded_on=t.founded_on,
            raised_on=t.raised_on,
            capital_before=float(t.capital_before),
            capital_after=float(t.capital_after),
            notice_url=PUBLIC_URL.format(id=t.notice_id),
        )
        for t in targets
    ]


def _place(company: Company) -> str | None:
    return " ".join(p for p in (company.postal_code, company.locality) if p) or None

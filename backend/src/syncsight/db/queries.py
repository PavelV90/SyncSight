"""Read queries behind the API: company search, timeline, leads and investment targets."""

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Subquery, func, select
from sqlalchemy.orm import Session

from syncsight.db.models import SEARCH_CONFIG, Company, SogcNotice, SwissmedicSite

# Register events that signal financial health (use case 3)
HEALTH_CHANGES = ("capital", "auditor", "seat", "liquidation", "bankruptcy", "deletion")


@dataclass(frozen=True)
class TimelineEntry:
    notice: SogcNotice
    previous_capital: Decimal | None


@dataclass(frozen=True)
class Lead:
    company: Company
    site_cantons: list[str]
    activity_codes: list[int]
    notices: list[SogcNotice]  # matching notices, newest first


@dataclass(frozen=True)
class Target:
    company: Company
    founded_on: date
    raised_on: date
    capital_before: Decimal
    capital_after: Decimal
    notice_id: str


def search_companies(
    session: Session, query: str, canton: str | None = None, limit: int = 20
) -> Sequence[Company]:
    """Full-text search over company name and purpose, best match first."""
    tsquery = func.websearch_to_tsquery(SEARCH_CONFIG, query)
    stmt = select(Company).where(Company.search_vector.op("@@")(tsquery))
    if canton:
        stmt = stmt.where(Company.canton == canton)
    stmt = stmt.order_by(func.ts_rank(Company.search_vector, tsquery).desc(), Company.name)
    return session.scalars(stmt.limit(limit)).all()


def company_timeline(
    session: Session,
    uid: str,
    since: date | None = None,
    changes: Collection[str] | None = None,
) -> list[TimelineEntry]:
    """Notices of one company, newest first, each with the capital stated before it."""
    previous_capital = func.lag(SogcNotice.capital_nominal).over(
        order_by=(SogcNotice.publication_date, SogcNotice.publication_number)
    )
    history = (
        select(SogcNotice.id, previous_capital.label("previous_capital"))
        .where(SogcNotice.company_uid == uid)
        .subquery()
    )
    stmt = (
        select(SogcNotice, history.c.previous_capital)
        .join(history, history.c.id == SogcNotice.id)
        .order_by(SogcNotice.publication_date.desc(), SogcNotice.publication_number.desc())
    )
    if since:
        stmt = stmt.where(SogcNotice.publication_date >= since)
    if changes:
        stmt = stmt.where(SogcNotice.changes.overlap(list(changes)))
    return [TimelineEntry(notice, previous) for notice, previous in session.execute(stmt)]


def company_sites(session: Session, uid: str) -> Sequence[SwissmedicSite]:
    stmt = select(SwissmedicSite).where(SwissmedicSite.company_uid == uid)
    return session.scalars(stmt.order_by(SwissmedicSite.site_name)).all()


def swissmedic_leads(
    session: Session,
    *,
    cantons: Collection[str],
    since: date,
    activity_codes: Collection[int],
    changes: Collection[str],
) -> list[Lead]:
    """Licensed companies with sites in `cantons` and matching register changes since `since`."""
    site_cantons: dict[str, set[str]] = {}
    site_activities: dict[str, set[int]] = {}
    for uid, canton, codes in session.execute(
        select(
            SwissmedicSite.company_uid, SwissmedicSite.site_canton, SwissmedicSite.activity_codes
        ).where(
            SwissmedicSite.company_uid.is_not(None),
            SwissmedicSite.site_canton.in_(cantons),
            SwissmedicSite.activity_codes.overlap(list(activity_codes)),
        )
    ):
        if uid and canton:
            site_cantons.setdefault(uid, set()).add(canton)
            site_activities.setdefault(uid, set()).update(codes)
    notices: dict[str, list[SogcNotice]] = {}
    for notice in session.scalars(
        select(SogcNotice)
        .where(
            SogcNotice.company_uid.in_(site_cantons),
            SogcNotice.publication_date >= since,
            SogcNotice.changes.overlap(list(changes)),
        )
        .order_by(SogcNotice.publication_date.desc(), SogcNotice.publication_number.desc())
    ):
        notices.setdefault(notice.company_uid or "", []).append(notice)
    companies = session.scalars(select(Company).where(Company.uid.in_(notices))).all()
    leads = [
        Lead(c, sorted(site_cantons[c.uid]), sorted(site_activities[c.uid]), notices[c.uid])
        for c in companies
    ]
    return sorted(leads, key=lambda lead: lead.notices[0].publication_date, reverse=True)


def investment_targets(
    session: Session, *, query: str, founded_since: date, raised_since: date
) -> list[Target]:
    """Companies matching `query`, registered since `founded_since`, with a capital increase
    published since `raised_since` (latest increase per company)."""
    founded = (
        select(SogcNotice.company_uid, func.min(SogcNotice.publication_date).label("founded_on"))
        .where(SogcNotice.changes.contains(["registration"]))
        .group_by(SogcNotice.company_uid)
        .subquery()
    )
    capitals = _capitals()
    tsquery = func.websearch_to_tsquery(SEARCH_CONFIG, query)
    rows = session.execute(
        select(
            Company,
            founded.c.founded_on,
            capitals.c.publication_date,
            capitals.c.previous,
            capitals.c.capital_nominal,
            capitals.c.id,
        )
        .join(founded, founded.c.company_uid == Company.uid)
        .join(capitals, capitals.c.company_uid == Company.uid)
        .where(
            Company.search_vector.op("@@")(tsquery),
            founded.c.founded_on >= founded_since,
            capitals.c.publication_date >= raised_since,
            capitals.c.capital_nominal > capitals.c.previous,
        )
        .order_by(capitals.c.publication_date.desc())
    ).all()
    targets: dict[str, Target] = {}
    for company, founded_on, raised_on, before, after, notice_id in rows:
        targets.setdefault(
            company.uid, Target(company, founded_on, raised_on, before, after, notice_id)
        )
    return list(targets.values())


def investment_targets_raises(
    session: Session, uids: Collection[str], since: date
) -> list[tuple[str, date, Decimal, Decimal, str]]:
    """(uid, date, capital before, capital after, notice id) of capital increases since `since`."""
    capitals = _capitals()
    rows = session.execute(
        select(
            capitals.c.company_uid,
            capitals.c.publication_date,
            capitals.c.previous,
            capitals.c.capital_nominal,
            capitals.c.id,
        ).where(
            capitals.c.company_uid.in_(list(uids)),
            capitals.c.publication_date >= since,
            capitals.c.capital_nominal > capitals.c.previous,
        )
    )
    return [(uid, on, before, after, notice_id) for uid, on, before, after, notice_id in rows]


def _capitals() -> Subquery:
    """Each notice's stated capital next to the capital stated in the company's previous notice."""
    return (
        select(
            SogcNotice.id,
            SogcNotice.company_uid,
            SogcNotice.publication_date,
            SogcNotice.capital_nominal,
            func.lag(SogcNotice.capital_nominal)
            .over(
                partition_by=SogcNotice.company_uid,
                order_by=(SogcNotice.publication_date, SogcNotice.publication_number),
            )
            .label("previous"),
        )
        .where(SogcNotice.capital_nominal.is_not(None))
        .subquery()
    )

"""Data freshness per source: rows, last load time, newest record, stale flag."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from syncsight.db.models import (
    BuildingPermit,
    Company,
    CompanyWebsite,
    Medicine,
    SogcNotice,
    SwissmedicSite,
    WebHit,
)
from syncsight.ingestion.zefix_lindas import SOURCE as ZEFIX_SOURCE


@dataclass(frozen=True)
class SourceStatus:
    key: str
    label: str
    rows: int
    last_loaded_at: datetime | None
    newest_record: date | None
    stale_after_days: int
    command: str  # syncsight-ingest subcommand that refreshes it

    @property
    def stale(self) -> bool:
        if self.last_loaded_at is None:
            return True
        age = datetime.now(UTC) - self.last_loaded_at
        return age > timedelta(days=self.stale_after_days)


# key, label, row filter, load-time column, newest-record column, stale after days, command
_SOURCES: list[tuple[str, str, Any, Any, Any, Any, int, str]] = [
    ("zefix", "Companies (Zefix)", Company, Company.source == ZEFIX_SOURCE,
     Company.last_seen_at, None, 7, "zefix"),
    ("shab", "Register notices (SHAB)", SogcNotice, None,
     SogcNotice.fetched_at, SogcNotice.publication_date, 7, "shab"),
    ("swissmedic", "Swissmedic licences", SwissmedicSite, None,
     SwissmedicSite.fetched_at, None, 45, "swissmedic"),
    ("medicines", "Authorised medicines", Medicine, None,
     Medicine.fetched_at, Medicine.first_authorised_on, 45, "medicines"),
    ("permits", "Building permits", BuildingPermit, None,
     BuildingPermit.fetched_at, BuildingPermit.publication_date, 45, "permits"),
    ("websites", "Company websites", CompanyWebsite, CompanyWebsite.url.is_not(None),
     CompanyWebsite.checked_at, None, 120, "websites"),
    ("web", "Website keyword hits", WebHit, None, WebHit.fetched_at, None, 45, "crawl"),
]  # fmt: skip


def source_status(session: Session) -> list[SourceStatus]:
    statuses = []
    for key, label, model, where, loaded, newest, stale_days, command in _SOURCES:
        columns = [func.count(), func.max(loaded)]
        if newest is not None:
            columns.append(func.max(newest))
        query = select(*columns).select_from(model)
        if where is not None:
            query = query.where(where)
        row = session.execute(query).one()
        newest_record = row[2] if newest is not None else None
        statuses.append(
            SourceStatus(key, label, row[0], row[1], newest_record, stale_days, command)
        )
    return statuses

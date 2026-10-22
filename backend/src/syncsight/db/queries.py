"""Read queries used by the API."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from syncsight.db.models import SEARCH_CONFIG, Company


def search_companies(session: Session, query: str, limit: int = 20) -> Sequence[Company]:
    """Full-text search over company name and purpose, best match first."""
    tsquery = func.websearch_to_tsquery(SEARCH_CONFIG, query)
    stmt = (
        select(Company)
        .where(Company.search_vector.op("@@")(tsquery))
        .order_by(func.ts_rank(Company.search_vector, tsquery).desc(), Company.name)
        .limit(limit)
    )
    return session.scalars(stmt).all()

"""Engine and session factory."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from syncsight.config import get_settings


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or get_settings().database_url, pool_pre_ping=True)


SessionFactory = sessionmaker(autoflush=False, expire_on_commit=False)

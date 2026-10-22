"""Alembic environment: online migrations against SYNCSIGHT_DATABASE_URL."""

from alembic import context
from sqlalchemy import create_engine

from syncsight.config import get_settings
from syncsight.db.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations() -> None:
    url = config.get_main_option("sqlalchemy.url") or get_settings().database_url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()

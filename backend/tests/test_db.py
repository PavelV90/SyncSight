import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from syncsight.db.models import Base, Company
from syncsight.db.queries import search_companies

pytestmark = pytest.mark.db


def test_full_text_search_matches_purpose(db_session: Session) -> None:
    db_session.add_all(
        [
            Company(
                uid="CHE-000.000.001",
                name="Alpenmed AG",
                purpose="Entwicklung von Medtech-Implantaten",
            ),
            Company(
                uid="CHE-000.000.002", name="Bergbeck GmbH", purpose="Herstellung von Backwaren"
            ),
        ]
    )
    db_session.flush()

    assert [c.name for c in search_companies(db_session, "medtech")] == ["Alpenmed AG"]


def test_migrations_match_models(db_engine: Engine) -> None:
    with db_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []

import pytest
from sqlalchemy.orm import Session

from syncsight.db.models import Company
from syncsight.db.queries import search_companies

pytestmark = pytest.mark.db


def test_full_text_search_matches_purpose(db_session: Session) -> None:
    db_session.add_all(
        [
            Company(uid="CHE-000.000.001", name="Alpenmed AG", purpose="Entwicklung von Medtech-Implantaten"),
            Company(uid="CHE-000.000.002", name="Bergbeck GmbH", purpose="Herstellung von Backwaren"),
        ]
    )
    db_session.flush()

    assert [c.name for c in search_companies(db_session, "medtech")] == ["Alpenmed AG"]

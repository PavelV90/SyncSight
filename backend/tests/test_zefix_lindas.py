from datetime import UTC, datetime

import httpx2
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncsight.db.models import Company
from syncsight.ingestion import zefix_lindas
from syncsight.ingestion.zefix_lindas import CompanyRecord, parse_csv

CSV = (
    "uid,name,legalForm,purpose,street,postalCode,locality,canton,municipality,municipalityName\n"
    "CHE000000001,Alpenmed AG,https://ld.admin.ch/ech/97/legalforms/0106,"
    '"Entwicklung von Medtech-Implantaten, Beratung",Hauptstrasse 1,4051,Basel,BS,'
    "https://ld.admin.ch/municipality/2701,Basel\n"
    "CHE000000001,Alpenmed AG,https://ld.admin.ch/ech/97/legalforms/0106,Duplikat,,,,BS,,\n"
    "not-a-uid,Broken GmbH,,,,,,BS,,\n"
    "CHE000000002,Bergbeck GmbH,,,,,,BS,,\n"
)


def test_build_query_partitions_by_canton() -> None:
    assert 'schema:addressRegion "ZH"' in zefix_lindas.build_query("ZH")
    assert "FILTER NOT EXISTS" in zefix_lindas.build_query(zefix_lindas.UNASSIGNED)
    with pytest.raises(ValueError, match="Unknown canton"):
        zefix_lindas.build_query("XX")


def test_parse_csv_normalises_and_deduplicates() -> None:
    records = parse_csv(CSV)

    assert [r.uid for r in records] == ["CHE-000.000.001", "CHE-000.000.002"]
    assert records[0] == CompanyRecord(
        uid="CHE-000.000.001",
        name="Alpenmed AG",
        legal_form="0106",
        purpose="Entwicklung von Medtech-Implantaten, Beratung",
        street="Hauptstrasse 1",
        postal_code="4051",
        locality="Basel",
        canton="BS",
        municipality_id=2701,
        seat="Basel",
    )
    assert records[1].legal_form is None and records[1].purpose is None


@pytest.mark.db
def test_run_loads_canton_and_updates_on_rerun(db_session: Session) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, text=CSV)

    client = httpx2.Client(transport=httpx2.MockTransport(handler))

    assert zefix_lindas.run(db_session, client, cantons=["BS"]) == 2
    assert requests[0].headers["Accept"] == "text/csv"
    company = db_session.get(Company, "CHE-000.000.001")
    assert company is not None
    assert (company.name_key, company.canton, company.status) == ("alpenmed ag", "BS", "active")

    renamed = [CompanyRecord(**{**vars(parse_csv(CSV)[0]), "name": "Alpenmed Holding AG"})]
    zefix_lindas.upsert_companies(db_session, renamed, seen_at=datetime.now(UTC))
    db_session.refresh(company)
    assert company.name == "Alpenmed Holding AG"


@pytest.mark.db
def test_mark_unseen_inactive(db_session: Session) -> None:
    before = datetime(2026, 1, 1, tzinfo=UTC)
    zefix_lindas.upsert_companies(db_session, parse_csv(CSV), seen_at=before)
    zefix_lindas.upsert_companies(db_session, parse_csv(CSV)[:1], seen_at=datetime.now(UTC))

    assert (
        zefix_lindas.mark_unseen_inactive(
            db_session, run_started_at=datetime(2026, 6, 1, tzinfo=UTC)
        )
        == 1
    )
    statuses = dict(db_session.execute(select(Company.uid, Company.status)).all())
    assert statuses == {"CHE-000.000.001": "active", "CHE-000.000.002": "inactive"}

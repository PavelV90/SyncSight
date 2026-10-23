"""The three MVP use cases, end to end through the API against Postgres."""

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from syncsight.api.main import app, get_session
from syncsight.db.models import Company, SogcNotice, SwissmedicSite

pytestmark = pytest.mark.db
TODAY = date.today()


def _company(uid: str, name: str, canton: str, purpose: str = "Handel") -> Company:
    return Company(
        uid=uid, name=name, name_key=name.lower(), canton=canton, purpose=purpose,
        legal_form="0106", status="active",
    )  # fmt: skip


def _notice(
    uid: str, days_ago: int, changes: list[str], capital: str | None = None, rubric: str = "HR02"
) -> SogcNotice:
    published = TODAY - timedelta(days=days_ago)
    number = f"{rubric}-{uid[-3:]}{days_ago:05d}"
    return SogcNotice(
        id=f"{uid}-{days_ago}", publication_number=number, publication_date=published,
        sub_rubric=rubric, company_uid=uid, changes=changes,
        capital_nominal=Decimal(capital) if capital else None, publication_text="…",
    )  # fmt: skip


def _site(uid: str, licence: str, canton: str, codes: list[int]) -> SwissmedicSite:
    return SwissmedicSite(
        licence_number=licence, site_number="1", holder_name="x", holder_name_key="x",
        site_name="Werk", site_canton=canton, activity_codes=codes, company_uid=uid,
    )  # fmt: skip


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    db_session.add_all(
        [
            _company("CHE-000.000.001", "Alpenpharma AG", "BS"),
            _site("CHE-000.000.001", "L1", "BS", [1, 4]),
            _notice("CHE-000.000.001", 10, ["board"]),
            _notice("CHE-000.000.001", 200, ["management"]),
            _company("CHE-000.000.002", "Rheinhandel AG", "BL"),
            _site("CHE-000.000.002", "L2", "BL", [4]),
            _notice("CHE-000.000.002", 5, ["board"]),
            _company("CHE-000.000.003", "Zugmed AG", "ZG", "Entwicklung von Medtech-Geräten"),
            _notice("CHE-000.000.003", 1500, ["registration"], "100000", rubric="HR01"),
            _notice("CHE-000.000.003", 400, ["seat"], "100000"),
            _notice("CHE-000.000.003", 30, ["capital"], "250000"),
            _company("CHE-000.000.004", "Altmed AG", "ZG", "Vertrieb von Medtech-Produkten"),
            _notice("CHE-000.000.004", 4000, ["registration"], "100000", rubric="HR01"),
            _notice("CHE-000.000.004", 20, ["capital"], "900000"),
        ]
    )
    db_session.flush()
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_leads_are_licensed_manufacturers_with_recent_board_changes(client: TestClient) -> None:
    leads = client.get("/api/leads", params={"cantons": ["BS", "BL", "AG"], "days": 90}).json()

    assert [lead["company"]["name"] for lead in leads] == ["Alpenpharma AG"]
    assert leads[0]["activities"] == ["Manufacturing", "Wholesale"]
    assert [n["changes"] for n in leads[0]["notices"]] == [["board"]]
    assert leads[0]["notices"][0]["url"].startswith("https://www.shab.ch/")


def test_targets_are_young_companies_that_raised_capital(client: TestClient) -> None:
    targets = client.get(
        "/api/targets", params={"q": "medtech", "founded_since": "2020-01-01"}
    ).json()

    assert [t["company"]["name"] for t in targets] == ["Zugmed AG"]
    assert (targets[0]["capital_before"], targets[0]["capital_after"]) == (100000.0, 250000.0)


def test_health_timeline_lists_register_events_with_capital_history(client: TestClient) -> None:
    profile = client.get("/api/companies/CHE000000003", params={"health_only": True}).json()

    assert profile["legal_form"] == "Aktiengesellschaft"
    assert [(n["changes"], n["previous_capital"], n["capital"]) for n in profile["timeline"]] == [
        (["capital"], 100000.0, 250000.0),
        (["seat"], 100000.0, 100000.0),
    ]


def test_company_search_by_text_and_uid(client: TestClient) -> None:
    by_text = client.get("/api/companies", params={"q": "medtech"}).json()
    by_uid = client.get("/api/companies", params={"q": "CHE-000.000.001"}).json()

    assert {c["name"] for c in by_text} == {"Zugmed AG", "Altmed AG"}
    assert [c["name"] for c in by_uid] == ["Alpenpharma AG"]
    assert client.get("/api/companies/CHE-999.999.999").status_code == 404

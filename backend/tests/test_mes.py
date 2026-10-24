"""MES-lead scoring end to end through the API against Postgres."""

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from syncsight.api.main import app, get_session
from syncsight.db.models import (
    BuildingPermit,
    Company,
    CompanyWebsite,
    SogcNotice,
    SwissmedicSite,
    SwissmedicSiteChange,
    WebHit,
)

pytestmark = pytest.mark.db
TODAY = date.today()


def _site(uid: str, licence: str, codes: list[int]) -> SwissmedicSite:
    return SwissmedicSite(
        licence_number=licence, site_number="1", holder_name="x", holder_name_key="x",
        site_canton="BS", activity_codes=codes, company_uid=uid,
    )  # fmt: skip


def _permit(uid: str, notice_id: str, description: str, days_ago: int = 30) -> BuildingPermit:
    return BuildingPermit(
        id=notice_id, company_uid=uid, publication_number=notice_id, sub_rubric="BP-BS10",
        publication_date=TODAY - timedelta(days=days_ago), description=description,
        applicant_name="x",
    )  # fmt: skip


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    uid_a, uid_b, uid_c = "CHE-000.000.001", "CHE-000.000.002", "CHE-000.000.003"
    db_session.add_all(
        [
            Company(uid=uid_a, name="Alpenpharma AG", status="active"),
            _site(uid_a, "L1", [1]),
            _permit(uid_a, "p1", "Neubau Produktionsgebäude", days_ago=30),
            _permit(uid_a, "p2", "Neubau Produktionslinie 2", days_ago=60),
            _permit(uid_a, "p3", "Ersatz Produktionskälte", days_ago=90),  # over the cap of two
            WebHit(company_uid=uid_a, url="https://a.ch/jobs/1", kind="career",
                   title="MES Engineer", keywords=["mes", "vendor:PharmaSuite"]),
            Company(uid=uid_b, name="Rheinchemie AG", status="active"),
            _site(uid_b, "L2", [3]),
            SwissmedicSiteChange(detected_on=TODAY, licence_number="L2", site_number="2",
                                 company_uid=uid_b, kind="site_added", detail="Neues Werk"),
            SogcNotice(id="n1", publication_number="HR02-1", publication_date=TODAY,
                       sub_rubric="HR02", company_uid=uid_b, changes=["management"],
                       capital_nominal=Decimal("100000")),
            Company(uid=uid_c, name="Grosshandel AG", status="active"),
            _site(uid_c, "L3", [4]),  # wholesale only: not an MES target
            _permit(uid_c, "p4", "Neubau Produktionsgebäude"),
        ]
    )  # fmt: skip
    db_session.flush()
    app.dependency_overrides[get_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_mes_leads_rank_manufacturers_by_capped_evidence(client: TestClient) -> None:
    leads = client.get("/api/mes-leads").json()

    assert [(lead["company"]["name"], lead["score"]) for lead in leads] == [
        ("Alpenpharma AG", 13),  # 2 production permits x 3 + MES 3 + hiring 2 + vendor 2
        ("Rheinchemie AG", 3),  # licence change 2 + management change 1
    ]
    assert leads[0]["vendors"] == ["PharmaSuite"]
    assert {e["kind"] for e in leads[0]["evidence"]} == {
        "permit_production", "web_mes", "web_hiring", "web_vendor",
    }  # fmt: skip
    assert leads[0]["evidence"][0]["url"].startswith("https://www.shab.ch/")


def test_min_score_filters_weak_leads(client: TestClient) -> None:
    leads = client.get("/api/mes-leads", params={"min_score": 5}).json()

    assert [lead["company"]["name"] for lead in leads] == ["Alpenpharma AG"]


def test_score_breakdown_and_points_per_item(client: TestClient) -> None:
    [lead, _] = client.get("/api/mes-leads").json()

    production = next(k for k in lead["breakdown"] if k["kind"] == "permit_production")
    assert production == {
        "kind": "permit_production", "items": 3, "counted": 2, "points_each": 3, "points": 6,
    }  # fmt: skip
    permit_points = [e["points"] for e in lead["evidence"] if e["kind"] == "permit_production"]
    assert sorted(permit_points) == [0, 3, 3]
    assert sum(k["points"] for k in lead["breakdown"]) == lead["score"]


def test_scoring_rules_are_published(client: TestClient) -> None:
    rules = {r["kind"]: r for r in client.get("/api/mes-scoring").json()}

    assert rules["permit_production"] == {"kind": "permit_production", "points": 3, "max_items": 2}


def test_profile_carries_mes_signals_and_website(client: TestClient, db_session: Session) -> None:
    db_session.add(
        CompanyWebsite(
            company_uid="CHE-000.000.001", url="https://www.alpenpharma.ch", source="manual"
        )
    )
    db_session.flush()

    profile = client.get("/api/companies/CHE-000.000.001").json()
    plain = client.get("/api/companies/CHE-000.000.003").json()

    assert profile["website"] == "https://www.alpenpharma.ch"
    assert profile["mes"]["score"] == 13
    assert plain["mes"] is None  # wholesale only: not an MES target


def test_newest_items_earn_the_points_when_a_kind_is_capped(client: TestClient) -> None:
    lead = client.get("/api/mes-leads").json()[0]

    permits = [e for e in lead["evidence"] if e["kind"] == "permit_production"]
    # three permits on different dates: the two newest count, the oldest is over the cap
    assert [e["on"] for e in permits] == sorted((e["on"] for e in permits), reverse=True)
    assert [e["points"] for e in permits] == [3, 3, 0]

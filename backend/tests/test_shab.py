import json
from datetime import date
from decimal import Decimal

import httpx2
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncsight.db.models import SogcNotice
from syncsight.ingestion import shab
from syncsight.ingestion.shab import parse_notice
from tests.conftest import FIXTURES_DIR

HR01 = (FIXTURES_DIR / "shab_hr01_registration.xml").read_bytes()
HR02 = (FIXTURES_DIR / "shab_hr02_capital_increase.xml").read_bytes()
HR03 = (FIXTURES_DIR / "shab_hr03_deletion.xml").read_bytes()


def test_parses_capital_increase_notice() -> None:
    notice = parse_notice(HR02)

    assert notice.id == "00000000-0000-0000-0000-000000000001"
    assert notice.publication_number == "HR02-0000000001"
    assert notice.publication_date == date(2026, 10, 22)
    assert notice.sub_rubric == "HR02"
    assert notice.cantons == "BS"
    assert notice.company_uid == "CHE-000.000.001"
    assert notice.company_name == "Beispiel Pharma AG"
    assert notice.capital_nominal == Decimal("500000.00")
    assert notice.changes == {"capital"}
    assert notice.publication_text == (
        "Beispiel Pharma AG, in Basel, CHE-000.000.001. Aktienkapital neu: CHF 500'000."
    )


def test_parses_registration_and_deletion() -> None:
    registration = parse_notice(HR01)
    deletion = parse_notice(HR03)

    assert registration.changes == {"registration"}
    assert registration.purpose == "Développement de dispositifs medtech."
    assert registration.company_seat == "Lausanne"
    assert deletion.changes == {"deletion"}
    assert deletion.company_uid == "CHE-000.000.003"
    assert deletion.legal_form == "0107"


def test_rejects_notice_without_id() -> None:
    with pytest.raises(ValueError, match="meta/id"):
        parse_notice(b"<publication><meta/></publication>")


def _fake_api(notices: dict[str, bytes], fetched: list[str]) -> httpx2.Client:
    """Amtsblattportal stand-in: list endpoint (paged) plus one XML per notice."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path.endswith("/xml"):
            notice_id = path.split("/")[-2]
            fetched.append(notice_id)
            return httpx2.Response(200, content=notices[notice_id])
        page = int(request.url.params["pageRequest.page"])
        size = int(request.url.params["pageRequest.size"])
        ids = sorted(notices)[page * size : (page + 1) * size]
        body = {"content": [{"meta": {"id": i}} for i in ids], "total": len(notices)}
        return httpx2.Response(200, text=json.dumps(body))

    return httpx2.Client(transport=httpx2.MockTransport(handler))


def test_list_notice_ids_follows_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shab, "PAGE_SIZE", 2)
    notices = {parse_notice(x).id: x for x in (HR01, HR02, HR03)}

    ids = list(shab.list_notice_ids(_fake_api(notices, []), since=date(2026, 10, 20)))

    assert ids == sorted(notices)


@pytest.mark.db
def test_run_stores_notices_and_skips_known(db_session: Session) -> None:
    notices = {parse_notice(x).id: x for x in (HR01, HR02, HR03)}
    fetched: list[str] = []
    client = _fake_api(notices, fetched)

    assert shab.run(db_session, client, since=date(2026, 10, 20), delay=0) == 3
    assert shab.run(db_session, client, since=date(2026, 10, 20), delay=0) == 0
    assert len(fetched) == 3

    stored = db_session.scalars(select(SogcNotice).order_by(SogcNotice.publication_date)).all()
    assert [(n.sub_rubric, n.changes) for n in stored] == [
        ("HR03", ["deletion"]),
        ("HR01", ["registration"]),
        ("HR02", ["capital"]),
    ]

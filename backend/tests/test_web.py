import httpx2
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncsight.db.models import Company, WebHit
from syncsight.ingestion import web
from syncsight.ingestion.crawler import Fetcher, Hit

COMPANY = Company(uid="CHE-123.456.789", name="Alpen Pharma AG")


def test_candidate_urls_from_name() -> None:
    assert web.candidate_urls("Alpen Pharma AG") == [
        "https://www.alpen.ch", "https://www.alpen.com",
        "https://www.alpenpharma.ch", "https://www.alpenpharma.com",
        "https://www.alpen-pharma.ch", "https://www.alpen-pharma.com",
    ]  # fmt: skip
    assert web.candidate_urls("AG") == []


def test_identifies_by_uid_or_registered_name() -> None:
    assert web.identifies("UID: CHE-123.456.789 MWST", COMPANY) == "uid"
    assert web.identifies("© 2026 Alpen  Pharma AG, Basel", COMPANY) == "name"
    assert web.identifies("Alpen Pharma Holding", COMPANY) is None


def test_verify_accepts_site_whose_imprint_shows_the_uid() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        pages = {
            "/": '<html><body>Welcome <a href="/impressum">Impressum</a></body></html>',
            "/impressum": "<html><body>Unternehmens-ID CHE123456789</body></html>",
        }
        if request.url.path in pages:
            return httpx2.Response(
                200, text=pages[request.url.path], headers={"content-type": "text/html"}
            )
        return httpx2.Response(404)

    fetcher = Fetcher(httpx2.Client(transport=httpx2.MockTransport(handler)), delay=0)

    assert web.verify(fetcher, "https://www.alpenpharma.ch/", COMPANY) == (
        "https://www.alpenpharma.ch/",
        "uid on https://www.alpenpharma.ch/impressum",
    )


@pytest.mark.db
def test_store_hits_upserts_by_url(db_session: Session) -> None:
    hit = Hit("https://www.alpenpharma.ch/news/1", "news", "MES", None, frozenset({"mes"}), "…MES…")
    web.store_hits(db_session, "CHE-123.456.789", [hit])
    web.store_hits(db_session, "CHE-123.456.789", [hit])

    rows = db_session.scalars(select(WebHit)).all()
    assert [(r.url, r.keywords) for r in rows] == [("https://www.alpenpharma.ch/news/1", ["mes"])]

"""Phase B: find company websites, then crawl them for MES-signal keywords.

Website sources, in order: Zefix (LINDAS schema:url), Wikidata (official website P856 of
the item with the company's Swiss UID P4829, CC0), or a domain guessed from the name
that is accepted only if the site shows the company's UID or exact registered name.
"""

import logging
import re
import unicodedata
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx2
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from syncsight.config import get_settings
from syncsight.db.models import Company, CompanyWebsite, WebHit
from syncsight.ingestion import http
from syncsight.ingestion.crawler import Fetcher, Hit, crawl_site, parse_html
from syncsight.ingestion.http import make_client
from syncsight.ingestion.normalize import name_key
from syncsight.ingestion.zefix_lindas import ENDPOINT as LINDAS_ENDPOINT

log = logging.getLogger(__name__)

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
RECHECK_AFTER = timedelta(days=90)
_GENERIC = {
    "ag", "sa", "gmbh", "sarl", "ltd", "llc", "inc", "sagl", "plc", "se", "kg", "co", "und",
    "et", "e", "in", "liquidation", "schweiz", "suisse", "svizzera", "switzerland", "swiss",
    "holding", "the", "de", "la", "le", "les", "der", "die", "das",
}  # fmt: skip
_IMPRINT = re.compile(r"impressum|imprint|legal|mentions|note legali|disclaimer|contact|kontakt")


def candidate_urls(company_name: str) -> list[str]:
    """Plausible homepages for a name: 'Alpen Pharma AG' -> www.alpen.ch, www.alpenpharma.ch, …"""
    ascii_name = unicodedata.normalize("NFKD", company_name).encode("ascii", "ignore").decode()
    tokens = [t for t in re.findall(r"[a-z0-9]+", ascii_name.lower()) if t not in _GENERIC]
    stems = (
        [tokens[0], "".join(tokens[:2]), "-".join(tokens[:2]), "".join(tokens[:3])]
        if tokens
        else []
    )
    unique = [s for i, s in enumerate(stems) if len(s) >= 3 and s not in stems[:i]]
    return [f"https://www.{stem}.{tld}" for stem in unique for tld in ("ch", "com")]


def identifies(text: str, company: Company) -> str | None:
    """'uid' or 'name' if the text identifies the company, else None."""
    digits = company.uid.replace("CHE-", "").replace(".", "")
    uid_pattern = rf"CHE[-\s]?{digits[:3]}[.\s]?{digits[3:6]}[.\s]?{digits[6:]}"
    if re.search(uid_pattern, text, re.IGNORECASE):
        return "uid"
    return "name" if name_key(company.name) in name_key(text) else None


def verify(fetcher: Fetcher, url: str, company: Company) -> tuple[str, str] | None:
    """(homepage URL, evidence) if the homepage or its imprint/contact page names the company."""
    response = fetcher.get(url)
    if response is None or "html" not in response.headers.get("content-type", ""):
        return None
    home = parse_html(str(response.url), response.text)
    if evidence := identifies(home.text, company):
        return home.url, f"{evidence} on homepage"
    imprint_links = [
        link for link in home.links if _IMPRINT.search(f"{link.url} {link.text}".lower())
    ]
    for link in imprint_links[:2]:
        page = fetcher.get(link.url)
        if page is not None and (
            evidence := identifies(parse_html(link.url, page.text).text, company)
        ):
            return home.url, f"{evidence} on {link.url}"
    return None


def lindas_websites(client: httpx2.Client, uids: Sequence[str]) -> dict[str, str]:
    values = " ".join(f'"{uid.replace("-", "").replace(".", "")}"' for uid in uids)
    query = (
        "PREFIX schema: <http://schema.org/> SELECT ?uid ?url WHERE { VALUES ?uid { "
        + values
        + " } ?id schema:value ?uid . ?c schema:identifier ?id ; schema:url ?url }"
    )
    rows = http.request(
        client, "POST", LINDAS_ENDPOINT, data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
    ).json()["results"]["bindings"]  # fmt: skip
    return {_uid(r["uid"]["value"]): r["url"]["value"] for r in rows}


def wikidata_websites(client: httpx2.Client, uids: Sequence[str]) -> dict[str, str]:
    values = " ".join(f'"{uid}"' for uid in uids)
    query = (
        f"SELECT ?uid ?url WHERE {{ VALUES ?uid {{ {values} }} ?i wdt:P4829 ?uid ; wdt:P856 ?url }}"
    )
    rows = http.request(
        client, "POST", WIKIDATA_ENDPOINT, data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
    ).json()["results"]["bindings"]  # fmt: skip
    return {r["uid"]["value"]: r["url"]["value"] for r in rows}


def resolve_websites(
    session: Session, client: httpx2.Client, uids: Sequence[str], workers: int = 8
) -> int:
    """Find websites for companies not checked in the last 90 days; returns websites found."""
    fresh_after = datetime.now(UTC) - RECHECK_AFTER
    checked = set(
        session.scalars(
            select(CompanyWebsite.company_uid).where(CompanyWebsite.checked_at >= fresh_after)
        )
    )
    todo = [uid for uid in uids if uid not in checked]
    found: dict[str, tuple[str | None, str, str | None]] = {}
    for start in range(0, len(todo), 200):
        batch = todo[start : start + 200]
        for uid, url in lindas_websites(client, batch).items():
            found[uid] = (url, "lindas", None)
        for uid, url in wikidata_websites(client, batch).items():
            found.setdefault(uid, (url, "wikidata", None))
    companies = [
        c
        for c in session.scalars(select(Company).where(Company.uid.in_(todo)))
        if c.uid not in found
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for company, result in zip(companies, pool.map(_guess, companies), strict=True):
            if result:
                found[company.uid] = (result[0], "verified-guess", result[1])
    for uid in todo:
        site_url, source, evidence = found.get(uid, (None, "none", None))
        row = {"company_uid": uid, "url": site_url, "source": source, "evidence": evidence,
               "checked_at": datetime.now(UTC)}  # fmt: skip
        stmt = insert(CompanyWebsite).values(row)
        session.execute(stmt.on_conflict_do_update(index_elements=["company_uid"], set_=row))
    session.commit()
    log.info("websites: %d of %d companies", len(found), len(todo))
    return len(found)


def crawl(session: Session, uids: Iterable[str], workers: int = 6) -> int:
    """Crawl the known websites of the given companies; returns keyword hits stored."""
    blocked = set(get_settings().crawl_blocklist)
    sites = [
        (uid, url)
        for uid, url in session.execute(
            select(CompanyWebsite.company_uid, CompanyWebsite.url).where(
                CompanyWebsite.company_uid.in_(list(uids)), CompanyWebsite.url.is_not(None)
            )
        )
        if url and not any(domain in url for domain in blocked)
    ]
    stored = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for (uid, _), hits in zip(
            sites, pool.map(_crawl_one, [url for _, url in sites]), strict=True
        ):
            store_hits(session, uid, hits)
            session.commit()
            stored += len(hits)
    log.info("web: %d keyword hits on %d sites", stored, len(sites))
    return stored


def store_hits(session: Session, company_uid: str, hits: Iterable[Hit]) -> None:
    for hit in hits:
        row = {
            "company_uid": company_uid, "url": hit.url, "kind": hit.kind, "title": hit.title,
            "published_on": hit.published_on, "keywords": sorted(hit.labels),
            "snippet": hit.snippet, "fetched_at": datetime.now(UTC),
        }  # fmt: skip
        stmt = insert(WebHit).values(row)
        session.execute(stmt.on_conflict_do_update(index_elements=["company_uid", "url"], set_=row))


def _guess(company: Company) -> tuple[str, str] | None:
    with make_client(timeout=20) as client:
        fetcher = Fetcher(client)
        for url in candidate_urls(company.name):
            if result := verify(fetcher, url, company):
                return result
    return None


def _crawl_one(url: str) -> list[Hit]:
    with make_client(timeout=30) as client:
        try:
            return crawl_site(Fetcher(client), url)
        except Exception:  # one broken site must not stop the run
            log.exception("web: crawl failed for %s", url)
            return []


def _uid(compact: str) -> str:
    return f"CHE-{compact[3:6]}.{compact[6:9]}.{compact[9:12]}"

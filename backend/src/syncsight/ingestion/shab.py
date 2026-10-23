"""SHAB/SOGC commercial-register notices (rubric HR) from the Amtsblattportal API.

API: https://www.amtsblattportal.ch/api/v1/publications (public, no login).
The list endpoint returns metadata only, so each notice's XML is fetched separately.
Notices name natural persons: we store them as the company event log, never index
the text for search, and never query by person name (see ARCHITECTURE.md).
"""

import html
import logging
import re
import time
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from xml.etree.ElementTree import Element

import httpx2
from defusedxml import ElementTree
from sqlalchemy import Select, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from syncsight.db.models import SogcNotice
from syncsight.ingestion import http
from syncsight.ingestion.normalize import normalize_uid

log = logging.getLogger(__name__)

API_URL = "https://www.amtsblattportal.ch/api/v1/publications"
PUBLIC_URL = "https://www.shab.ch/#!/search/publications/detail/{id}"
PAGE_SIZE = 2000  # API maximum

# <changements> child element -> change label
_SIMPLE_FLAGS = {
    "nameChanged": "name",
    "uidChanged": "uid",
    "legalStatusChanged": "legal_form",
    "seatChanged": "seat",
    "addressChanged": "address",
    "purposeChanged": "purpose",
    "others": "other",
}
# <changements> subtree -> change label, set if any flag inside is true
_NESTED_FLAGS = {
    "capitalChanged": "capital",
    "statusChanged/bankruptcy": "bankruptcy",
    "statusChanged/liquidation": "liquidation",
}
# <transaction> child element -> change label
_TRANSACTIONS = {"registration": "registration", "delete": "deletion"}
# Changes the XML does not flag, found in the notice text (DE/FR/IT wording of the registers).
# Matched after removing the company name and purpose, which may contain the same words.
_TEXT_RULES = {
    "board": re.compile(
        r"verwaltungsrat|stiftungsrat|conseil d.administration|conseil de fondation"
        r"|administrat(?:eur|rice)|consiglio d.amministrazione|consiglio di fondazione"
        r"|amministrat(?:ore|rice)",
        re.IGNORECASE,
    ),
    "management": re.compile(
        r"geschäftsführ|geschäftsleitung|direktor|gérant|directeur|directrice"
        r"|membre de la direction|gerente|diret(?:tore|trice)|direzione",
        re.IGNORECASE,
    ),
    "auditor": re.compile(
        r"revisionsstelle|organe de révision|ufficio di revisione", re.IGNORECASE
    ),
}
TEXT_LABELS = frozenset(_TEXT_RULES)


@dataclass(frozen=True)
class ShabNotice:
    id: str
    publication_number: str
    publication_date: date
    sub_rubric: str
    language: str | None
    cantons: str | None
    company_uid: str | None
    company_name: str | None
    company_seat: str | None
    legal_form: str | None
    purpose: str | None
    capital_nominal: Decimal | None
    changes: frozenset[str]
    publication_text: str | None


def parse_notice(xml: bytes) -> ShabNotice:
    root = ElementTree.fromstring(xml)
    content = root.find("content")
    commons = None
    if content is not None:
        commons = content.find("commonsNew")
        if commons is None:
            commons = content.find("commonsActual")
    company = commons.find("company") if commons is not None else None
    capital = _text(commons, "capital/nominal")
    cantons = [c.text for c in root.findall("meta/cantons") if c.text]
    text = plain_text(_text(content, "publicationText"))
    company_name = _text(company, "name")
    purpose = _text(commons, "purpose")
    changes = _changes(content.find("transaction") if content is not None else None)
    return ShabNotice(
        id=_required(root, "meta/id"),
        publication_number=_required(root, "meta/publicationNumber"),
        publication_date=date.fromisoformat(_required(root, "meta/publicationDate")[:10]),
        sub_rubric=_required(root, "meta/subRubric"),
        language=root.findtext("meta/language"),
        cantons=",".join(cantons) or None,
        company_uid=normalize_uid(_text(company, "uid")),
        company_name=company_name,
        company_seat=_text(company, "seat"),
        legal_form=_text(company, "legalForm"),
        purpose=purpose,
        capital_nominal=Decimal(capital) if capital else None,
        changes=changes | text_labels(text, company_name, purpose),
        publication_text=text,
    )


def text_labels(
    text: str | None, company_name: str | None = None, purpose: str | None = None
) -> frozenset[str]:
    """Board, management and auditor changes named in the notice text."""
    if not text:
        return frozenset()
    for known in (plain_text(purpose), company_name):
        if known:
            text = text.replace(known, " ")
    return frozenset(label for label, rule in _TEXT_RULES.items() if rule.search(text))


def reclassify(session: Session, batch_size: int = 5000) -> int:
    """Re-apply the text rules to stored notices (after a rule change); returns rows changed."""
    changed = 0
    query = select(
        SogcNotice.id,
        SogcNotice.changes,
        SogcNotice.publication_text,
        SogcNotice.company_name,
        SogcNotice.purpose,
    )
    for rows in session.execute(query).partitions(batch_size):
        for notice_id, changes, text, company_name, purpose in rows:
            new = (set(changes) - TEXT_LABELS) | text_labels(text, company_name, purpose)
            if new != set(changes):
                session.execute(
                    update(SogcNotice).where(SogcNotice.id == notice_id).values(changes=sorted(new))
                )
                changed += 1
    session.commit()
    return changed


def list_notice_ids(
    client: httpx2.Client,
    *,
    since: date | None = None,
    until: date | None = None,
    keyword: str | None = None,
    sub_rubrics: Sequence[str] = (),
) -> Iterator[str]:
    """IDs of published notices (default: rubric HR) by date range, keyword and sub-rubrics."""
    params: dict[str, Any] = {"publicationStates": "PUBLISHED", "pageRequest.size": PAGE_SIZE}
    if sub_rubrics:
        params["subRubrics"] = list(sub_rubrics)
    else:
        params["rubrics"] = "HR"
    if since:
        params["publicationDate.start"] = since.isoformat()
    if until:
        params["publicationDate.end"] = until.isoformat()
    if keyword:
        params["keyword"] = keyword
    page = 0
    while True:
        body = http.request(
            client, "GET", API_URL, params=params | {"pageRequest.page": page}
        ).json()
        for item in body.get("content", []):
            yield item["meta"]["id"]
        page += 1
        if page * PAGE_SIZE >= body.get("total", 0):
            return


def fetch_notice(client: httpx2.Client, notice_id: str) -> ShabNotice:
    return parse_notice(http.request(client, "GET", f"{API_URL}/{notice_id}/xml").content)


def upsert_notices(session: Session, notices: Iterable[ShabNotice]) -> int:
    rows = [asdict(n) | {"changes": sorted(n.changes)} for n in notices]
    if not rows:
        return 0
    stmt = insert(SogcNotice).values(rows)
    updated = {key: stmt.excluded[key] for key in rows[0] if key != "id"}
    session.execute(stmt.on_conflict_do_update(index_elements=["id"], set_=updated))
    return len(rows)


def run(
    session: Session,
    client: httpx2.Client,
    *,
    since: date | None = None,
    until: date | None = None,
    keyword: str | None = None,
    skip_known: bool = True,
    delay: float = 0.2,
    batch_size: int = 100,
) -> int:
    """Fetch and store notices; `delay` seconds between notice requests keeps the load polite."""
    known: set[str] = set()
    if skip_known:
        known = set(session.scalars(_known_ids_query(since, until)))
    batch: list[ShabNotice] = []
    total = 0
    for notice_id in list_notice_ids(client, since=since, until=until, keyword=keyword):
        if notice_id in known:
            continue
        batch.append(fetch_notice(client, notice_id))
        time.sleep(delay)
        if len(batch) >= batch_size:
            total += upsert_notices(session, batch)
            session.commit()
            batch.clear()
            log.info("shab: %d notices stored", total)
    total += upsert_notices(session, batch)
    session.commit()
    log.info("shab: done, %d new notices", total)
    return total


def _known_ids_query(since: date | None, until: date | None) -> Select[str]:
    query = select(SogcNotice.id)
    if since:
        query = query.where(SogcNotice.publication_date >= since)
    if until:
        query = query.where(SogcNotice.publication_date <= until)
    return query


def _changes(transaction: Element | None) -> frozenset[str]:
    if transaction is None:
        return frozenset()
    found = {label for tag, label in _TRANSACTIONS.items() if transaction.find(tag) is not None}
    changements = transaction.find("update/changements")
    if changements is not None:
        found |= {label for tag, label in _SIMPLE_FLAGS.items() if _any_true(changements.find(tag))}
        found |= {
            label for path, label in _NESTED_FLAGS.items() if _any_true(changements.find(path))
        }
    return frozenset(found)


def _any_true(element: Element | None) -> bool:
    return element is not None and any((e.text or "").strip() == "true" for e in element.iter())


def _text(element: Element | None, path: str) -> str | None:
    if element is None:
        return None
    value = element.findtext(path)
    return value.strip() or None if value else None


def plain_text(markup: str | None) -> str | None:
    """Notice fields carry HTML markup; keep readable text only."""
    if not markup:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    return re.sub(r"\s+", " ", text).strip() or None


def _required(root: Element, path: str) -> str:
    value = root.findtext(path)
    if not value:
        raise ValueError(f"SHAB notice is missing <{path}>")
    return value

"""Zefix core data of all active legal entities, via the LINDAS SPARQL endpoint.

Licence: OGD "open use, must provide the source" (Federal Commercial Registry Office).
One query per canton keeps responses small and avoids slow ORDER BY/OFFSET paging.
"""

import csv
import io
import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import httpx2
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from syncsight.db.models import Company
from syncsight.ingestion import http
from syncsight.ingestion.normalize import name_key, normalize_uid

log = logging.getLogger(__name__)

ENDPOINT = "https://lindas.admin.ch/query"
SOURCE = "zefix-lindas"
CANTONS = (
    "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR", "JU", "LU", "NE",
    "NW", "OW", "SG", "SH", "SO", "SZ", "TG", "TI", "UR", "VD", "VS", "ZG", "ZH",
)  # fmt: skip
UNASSIGNED = "--"  # partition for entities whose address has no canton

_QUERY = """
PREFIX schema: <http://schema.org/>
PREFIX admin: <https://schema.ld.admin.ch/>
SELECT ?uid ?name ?legalForm ?purpose ?street ?postalCode ?locality ?canton ?municipality
       ?municipalityName
WHERE {
  ?company a admin:ZefixOrganisation ; schema:legalName ?name ; schema:identifier ?id .
  ?id schema:name "CompanyUID" ; schema:value ?uid .
  %(partition)s
  OPTIONAL { ?company schema:additionalType ?legalForm }
  OPTIONAL { ?company schema:description ?purpose }
  OPTIONAL { ?company admin:municipality ?municipality .
             ?municipality schema:name ?municipalityName }
}
"""
_ADDRESS = """OPTIONAL { ?address schema:streetAddress ?street }
  OPTIONAL { ?address schema:postalCode ?postalCode }
  OPTIONAL { ?address schema:addressLocality ?locality }"""
_LEGAL_FORM = re.compile(r"/legalforms/(\d{4})$")
_MUNICIPALITY = re.compile(r"/municipality/(\d+)$")


@dataclass(frozen=True)
class CompanyRecord:
    uid: str
    name: str
    legal_form: str | None
    purpose: str | None
    street: str | None
    postal_code: str | None
    locality: str | None
    canton: str | None
    municipality_id: int | None
    seat: str | None


def build_query(canton: str) -> str:
    if canton == UNASSIGNED:
        partition = (
            "FILTER NOT EXISTS { ?company schema:address/schema:addressRegion ?anyCanton }\n"
            "  OPTIONAL { ?company schema:address ?address .\n  " + _ADDRESS + " }"
        )
    elif canton in CANTONS:
        partition = (
            f'?company schema:address ?address . ?address schema:addressRegion "{canton}" .\n'
            f'  BIND("{canton}" AS ?canton)\n  ' + _ADDRESS
        )
    else:
        raise ValueError(f"Unknown canton {canton!r}")
    return _QUERY % {"partition": partition}


def parse_csv(text: str) -> list[CompanyRecord]:
    """Parse a SPARQL CSV result; skips rows without a valid UID, keeps the first row per UID."""
    records: dict[str, CompanyRecord] = {}
    for row in csv.DictReader(io.StringIO(text)):
        uid = normalize_uid(row.get("uid"))
        if uid is None or uid in records:
            continue
        legal_form = _LEGAL_FORM.search(row.get("legalForm") or "")
        municipality = _MUNICIPALITY.search(row.get("municipality") or "")
        records[uid] = CompanyRecord(
            uid=uid,
            name=row["name"].strip(),
            legal_form=legal_form.group(1) if legal_form else None,
            purpose=row.get("purpose") or None,
            street=" ".join((row.get("street") or "").split()) or None,
            postal_code=row.get("postalCode") or None,
            locality=row.get("locality") or None,
            canton=row.get("canton") or None,
            municipality_id=int(municipality.group(1)) if municipality else None,
            seat=row.get("municipalityName") or None,
        )
    return list(records.values())


def fetch_canton(client: httpx2.Client, canton: str) -> list[CompanyRecord]:
    response = http.request(
        client,
        "POST",
        ENDPOINT,
        data={"query": build_query(canton)},
        headers={"Accept": "text/csv"},
    )
    return parse_csv(response.text)


def upsert_companies(
    session: Session, records: Iterable[CompanyRecord], seen_at: datetime, batch_size: int = 2000
) -> int:
    extra = {"status": "active", "source": SOURCE, "last_seen_at": seen_at}
    rows = [asdict(r) | extra | {"name_key": name_key(r.name)} for r in records]
    if not rows:
        return 0
    for start in range(0, len(rows), batch_size):
        stmt = insert(Company).values(rows[start : start + batch_size])
        updated = {key: stmt.excluded[key] for key in rows[0] if key != "uid"}
        session.execute(stmt.on_conflict_do_update(index_elements=["uid"], set_=updated))
    return len(rows)


def mark_unseen_inactive(session: Session, run_started_at: datetime) -> int:
    """After a full load: entities no longer listed by LINDAS are no longer active."""
    deactivated = session.scalars(
        update(Company)
        .where(Company.source == SOURCE, Company.status == "active")
        .where((Company.last_seen_at < run_started_at) | Company.last_seen_at.is_(None))
        .values(status="inactive")
        .returning(Company.uid)
    ).all()
    return len(deactivated)


def run(session: Session, client: httpx2.Client, cantons: Sequence[str] | None = None) -> int:
    """Load the given cantons (default: all, plus entities without canton) and commit per canton."""
    full_run = not cantons
    partitions = list(cantons) if cantons else [*CANTONS, UNASSIGNED]
    started_at = datetime.now(UTC)
    total = 0
    for canton in partitions:
        records = fetch_canton(client, canton)
        total += upsert_companies(session, records, seen_at=started_at)
        session.commit()
        log.info("zefix %s: %d companies", canton, len(records))
    if full_run:
        inactive = mark_unseen_inactive(session, started_at)
        session.commit()
        log.info("zefix: %d companies no longer active", inactive)
    return total

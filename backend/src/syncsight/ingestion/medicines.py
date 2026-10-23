"""Authorised medicinal products (Swissmedic open data, monthly), linked to holder companies.

Source: https://opendata.swiss/en/dataset/daten-von-human-und-tierarzneimitteln
(OGD "open use"). A recent first authorisation hints at a product launch.
"""

import io
import logging
import zipfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date

import httpx2
from defusedxml import ElementTree
from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from syncsight.db.models import Medicine
from syncsight.ingestion import http
from syncsight.ingestion.matching import link_by_name
from syncsight.ingestion.normalize import name_key

log = logging.getLogger(__name__)

DOWNLOAD_URL = "https://ogd.swissmedic.cloud/ogd-arzneimittel/Daten/OGD.zip"


@dataclass(frozen=True)
class MedicineRecord:
    authorisation_number: str
    product_name: str
    usage: str | None
    atc_code: str | None
    status: str | None
    first_authorised_on: date | None
    holder_name: str | None
    holder_postal_code: str | None


def parse_archive(content: bytes) -> list[MedicineRecord]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        holders = {
            row.findtext("PARTNER_NR"): (row.findtext("FIRMENNAME"), row.findtext("PLZ"))
            for row in ElementTree.fromstring(archive.read("OGD-Adressen.XML"))
        }
        products = ElementTree.fromstring(archive.read("OGD-Praeparate.XML"))
    records = []
    for row in products:
        holder_name, postal_code = holders.get(row.findtext("ZULASSUNGSINHABERIN"), (None, None))
        first = row.findtext("ERSTZULASSUNGSDATUM")
        records.append(
            MedicineRecord(
                authorisation_number=row.findtext("ZULASSUNGSNUMMER") or "",
                product_name=row.findtext("PRAEPARATENAME") or "",
                usage=row.findtext("VERWENDUNG"),
                atc_code=row.findtext("ATC_CODE"),
                status=row.findtext("ZULASSUNGSSTATUS"),
                first_authorised_on=date.fromisoformat(first) if first else None,
                holder_name=holder_name,
                holder_postal_code=postal_code,
            )
        )
    return [r for r in records if r.authorisation_number]


def replace_medicines(session: Session, records: Sequence[MedicineRecord]) -> int:
    session.execute(delete(Medicine))
    rows = [
        asdict(r) | {"holder_name_key": name_key(r.holder_name) if r.holder_name else None}
        for r in records
    ]
    for start in range(0, len(rows), 2000):
        session.execute(insert(Medicine).values(rows[start : start + 2000]))
    holders = {
        (r["holder_name_key"], r["holder_postal_code"]) for r in rows if r["holder_name_key"]
    }
    for (key, postal_code), uid in link_by_name(session, holders).items():
        session.execute(
            update(Medicine)
            .where(
                Medicine.holder_name_key == key,
                Medicine.holder_postal_code.is_not_distinct_from(postal_code),
            )
            .values(company_uid=uid)
        )
    return len(rows)


def run(session: Session, client: httpx2.Client) -> int:
    records = parse_archive(http.request(client, "GET", DOWNLOAD_URL).content)
    stored = replace_medicines(session, records)
    session.commit()
    log.info("medicines: %d products", stored)
    return stored

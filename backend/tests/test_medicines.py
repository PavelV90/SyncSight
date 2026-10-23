import io
import zipfile
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncsight.db.models import Company, Medicine
from syncsight.ingestion import medicines


def _archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "OGD-Adressen.XML",
            "<SMC><ADRESSEN><PARTNER_NR>1</PARTNER_NR><FIRMENNAME>Alpenpharma AG</FIRMENNAME>"
            "<PLZ>4058</PLZ></ADRESSEN></SMC>",
        )
        archive.writestr(
            "OGD-Praeparate.XML",
            "<SMC><PRAEPARAT><VERWENDUNG>HAM</VERWENDUNG><ZULASSUNGSNUMMER>70001</ZULASSUNGSNUMMER>"
            "<PRAEPARATENAME>Alpenol 10 mg, Tabletten</PRAEPARATENAME><ATC_CODE>N02BE</ATC_CODE>"
            "<ZULASSUNGSSTATUS>Z</ZULASSUNGSSTATUS><ZULASSUNGSINHABERIN>1</ZULASSUNGSINHABERIN>"
            "<ERSTZULASSUNGSDATUM>2026-03-01</ERSTZULASSUNGSDATUM></PRAEPARAT></SMC>",
        )
    return buffer.getvalue()


def test_parse_archive_joins_products_with_holders() -> None:
    [record] = medicines.parse_archive(_archive())

    assert record.product_name == "Alpenol 10 mg, Tabletten"
    assert record.first_authorised_on == date(2026, 3, 1)
    assert (record.holder_name, record.holder_postal_code) == ("Alpenpharma AG", "4058")


@pytest.mark.db
def test_replace_medicines_links_holder_company(db_session: Session) -> None:
    db_session.add(
        Company(uid="CHE-000.000.001", name="Alpenpharma AG", name_key="alpenpharma ag",
                postal_code="4058", status="active")
    )  # fmt: skip

    assert medicines.replace_medicines(db_session, medicines.parse_archive(_archive())) == 1
    assert db_session.scalars(select(Medicine.company_uid)).all() == ["CHE-000.000.001"]

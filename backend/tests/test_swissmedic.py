import io
from dataclasses import replace
from datetime import date

import pytest
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncsight.db.models import Company, SwissmedicSite, SwissmedicSiteChange
from syncsight.ingestion import swissmedic
from syncsight.ingestion.swissmedic import parse_workbook

HEADERS = [
    "Bewilligungsnummer\n\nNuméro d'autorisation",
    "Inhaberin Betriebsbewilligung - (gem. Handelsregister)\n\nTitulaire",
    "Strasse (Inhaberin)\n\nRue (siège)",
    "Hausnummer (Inhaberin)\n\nNuméro (siège)",
    "PLZ (Inhaberin)\n\nNPA (siège)",
    "Ort (Inhaberin)\n\nLieu (siège)",
    "Kanton (Inhaberin)\n\nCanton (siège)",
    "Gültig bis:\n\nvalable jusqu'au:",
    "Standort-Nummer\n\nNuméro du site",
    "Name (Standort)\n\nNom (Site)",
    "Strasse (Standort)\n\nRue (Site)",
    "Hausnummer (Standort)\n\nNuméro (site)",
    "PLZ (Standort)\n\nNPA (site)",
    "Ort (Standort)\n\nLieu (site)",
    "Kanton (Standort)\n\nCanton (site)",
    "Zertifikat Nummer\n\nNuméro du certificat",
    "Datum letzte Inspektion\n\nDate dernière inspection",
    "Compliance-Status Standort\n\nStatut conformité (site)",
    "1 Herstellung\n\n1 Fabrication",
    "2 Einfuhr\n\n2 Importation",
]


def _site(licence: str, holder: str, postal_code: str, site: float) -> list[object]:
    return [
        licence, holder, "Hauptstrasse", "1", postal_code, "Basel", "BS", "Indefinite",
        site, holder, "Werkweg", "2", postal_code, "Basel", "BS", "1000001",
        "30.07.2025", "COMPLIANT", "1 MANUFACTURE\n1.2 Non-sterile products", None,
    ]  # fmt: skip


def _workbook(*sites: list[object]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["Bewilligungsinhaberinnen (Arzneimittel inkl. Blut)"])
    sheet.append(["Bewilligungsinhaber / Titulaire de l'autorisation"])
    sheet.append(HEADERS)
    for site in sites:
        sheet.append(site)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parse_workbook_reads_sites_after_header_row() -> None:
    [record] = parse_workbook(_workbook(_site("500-1", "Alpenmed AG", "4051", 1102534.0)))

    assert record.licence_number == "500-1"
    assert record.site_number == "1102534"
    assert record.holder_name == "Alpenmed AG"
    assert record.holder_street == "Hauptstrasse 1"
    assert record.site_street == "Werkweg 2"
    assert record.last_inspection == date(2025, 7, 30)
    assert record.activity_codes == [1]
    assert record.activity_details == {"1": "1 MANUFACTURE\n1.2 Non-sterile products"}


def test_parse_workbook_requires_header_row() -> None:
    workbook = Workbook()
    buffer = io.BytesIO()
    workbook.save(buffer)
    with pytest.raises(ValueError, match="header row"):
        parse_workbook(buffer.getvalue())


@pytest.mark.db
def test_match_companies_by_name_then_postal_code(db_session: Session) -> None:
    db_session.add_all(
        [
            Company(uid="CHE-000.000.001", name="Alpenmed AG", name_key="alpenmed ag",
                    postal_code="4051", status="active"),
            Company(uid="CHE-000.000.002", name="Duplex AG", name_key="duplex ag",
                    postal_code="8001", status="active"),
            Company(uid="CHE-000.000.003", name="Duplex AG", name_key="duplex ag",
                    postal_code="4051", status="active"),
        ]
    )  # fmt: skip
    records = parse_workbook(
        _workbook(
            _site("500-1", "«Alpenmed» AG", "4051", 1.0),
            _site("500-2", "Duplex AG", "4051", 2.0),
            _site("500-3", "Unbekannt GmbH", "4051", 3.0),
        )
    )

    assert swissmedic.replace_sites(db_session, records) == 3
    assert swissmedic.match_companies(db_session) == 2
    links = dict(
        db_session.execute(select(SwissmedicSite.licence_number, SwissmedicSite.company_uid)).all()
    )
    assert links == {"500-1": "CHE-000.000.001", "500-2": "CHE-000.000.003", "500-3": None}
    assert swissmedic.matched_uids(db_session) == ["CHE-000.000.001", "CHE-000.000.003"]


@pytest.mark.db
def test_second_snapshot_records_changes(db_session: Session) -> None:
    first = parse_workbook(_workbook(_site("500-1", "Alpenmed AG", "4051", 1.0)))
    swissmedic.replace_sites(db_session, first)
    changed = replace(
        first[0], activity_codes=[1, 2], compliance_status="COMPLIANCE_MANAGEMENT_ACTION"
    )
    added = replace(first[0], site_number="2", site_name="Neues Werk")

    swissmedic.replace_sites(db_session, [changed, added])

    changes = db_session.scalars(
        select(SwissmedicSiteChange).order_by(SwissmedicSiteChange.kind)
    ).all()
    assert [(c.site_number, c.kind) for c in changes] == [
        ("1", "activity_added"),
        ("1", "compliance_changed"),
        ("2", "site_added"),
    ]
    assert changes[0].detail == "Alpenmed AG, Basel: Import"

"""Building-permit notices filed by target companies (cantonal gazettes on amtsblattportal.ch).

A new production building is a strong MES trigger. Notices are fetched per company
(keyword = registered name), and only company applicants are kept: natural persons
(applicants, architects, neighbours) are never parsed or stored (revDSG Art. 6).
Cantons publishing elsewhere (e.g. AG, GE, LU, SG, VD) are not covered.
"""

import logging
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from xml.etree.ElementTree import Element

import httpx2
from defusedxml import ElementTree
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from syncsight.db.models import BuildingPermit, Company
from syncsight.ingestion import http, shab
from syncsight.ingestion.normalize import name_key

log = logging.getLogger(__name__)

# Building-application sub-rubrics per gazette (planning and power-line notices excluded)
SUB_RUBRICS = (
    "AA-GR10", "AM-DA50", "BA-NW05", "BA-OW05", "BA-SH05", "BA-SO05", "BA-SZ05", "BA-VS05",
    "BP-AR10", "BP-BE10", "BP-BL05", "BP-BS10", "BP-TI10", "BP-ZG10", "BP-ZH01",
)  # fmt: skip
# "businessCase" format (e.g. BL, VS): element keys naming the applicant
_APPLICANT_KEYS = {"buildingContractor", "applicantParty"}
# Words that mark production, lab or cleanroom projects (DE/FR/IT/EN)
PRODUCTION_WORDS = re.compile(
    r"produktion|fabrik|herstellung|reinraum|labor|abfüll|pharma|gmp"
    r"|production|fabrication|usine|salle blanche|laboratoire"
    r"|produzione|fabbrica|laboratorio|cleanroom|manufactur",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PermitNotice:
    id: str
    publication_number: str
    publication_date: date
    sub_rubric: str
    cantons: str | None
    municipality: str | None
    description: str | None
    location: str | None
    applicants: tuple[str, ...]  # company names only


def parse_permit(xml: bytes) -> PermitNotice:
    root = ElementTree.fromstring(xml)
    content = root.find("content")
    if content is None:
        raise ValueError("Permit notice has no <content>")
    case = content.find("businessCase")
    if case is not None:
        description, location, municipality, applicants = _parse_business_case(case)
    else:
        description = shab.plain_text(content.findtext("projectDescription"))
        location = _address(content.find("projectLocation/address"))
        municipality = content.findtext("localization/municipalityId/term/de")
        applicants = tuple(
            name
            for company in content.findall("buildingContractor/legalEntity/multi/companies/company")
            if (name := (company.findtext("name") or "").strip())
        )
    cantons = [c.text for c in root.findall("meta/cantons") if c.text]
    return PermitNotice(
        id=_required(root, "meta/id"),
        publication_number=_required(root, "meta/publicationNumber"),
        publication_date=date.fromisoformat(_required(root, "meta/publicationDate")[:10]),
        sub_rubric=_required(root, "meta/subRubric"),
        cantons=",".join(cantons) or None,
        municipality=municipality or content.findtext("localization/municipalityId/term/de"),
        description=description or root.findtext("meta/title/de"),
        location=location,
        applicants=applicants,
    )


def applicant_for(notice: PermitNotice, company_name: str) -> str | None:
    """The applicant name if the company filed the notice."""
    key = name_key(company_name)
    return next((a for a in notice.applicants if name_key(a) == key), None)


def store(session: Session, notice: PermitNotice, company_uid: str, applicant: str) -> None:
    row = {
        "id": notice.id,
        "company_uid": company_uid,
        "publication_number": notice.publication_number,
        "publication_date": notice.publication_date,
        "sub_rubric": notice.sub_rubric,
        "cantons": notice.cantons,
        "municipality": notice.municipality,
        "description": notice.description,
        "location": notice.location,
        "applicant_name": applicant,
    }
    stmt = insert(BuildingPermit).values(row)
    session.execute(stmt.on_conflict_do_nothing(index_elements=["id", "company_uid"]))


def run(
    session: Session,
    client: httpx2.Client,
    companies: Iterable[str],
    *,
    since: date,
    delay: float = 0.2,
) -> int:
    """Look up permits filed since `since` by each company (UIDs); returns notices stored."""
    known = {
        (notice_id, uid)
        for notice_id, uid in session.execute(select(BuildingPermit.id, BuildingPermit.company_uid))
    }
    stored = 0
    for uid in companies:
        company = session.get(Company, uid)
        if company is None:
            continue
        for notice_id in shab.list_notice_ids(
            client, since=since, keyword=company.name, sub_rubrics=SUB_RUBRICS
        ):
            if (notice_id, uid) in known:
                continue
            xml = http.request(client, "GET", f"{shab.API_URL}/{notice_id}/xml").content
            time.sleep(delay)
            notice = parse_permit(xml)
            applicant = applicant_for(notice, company.name)
            if applicant:
                store(session, notice, uid, applicant)
                stored += 1
        session.commit()
        time.sleep(delay)
    log.info("permits: %d notices stored", stored)
    return stored


def _parse_business_case(
    case: Element,
) -> tuple[str | None, str | None, str | None, tuple[str, ...]]:
    description = shab.plain_text(case.findtext("primary/element/valueText/term/de"))
    location = municipality = None
    applicants: list[str] = []
    for element in case.findall("secondary/element"):
        key = element.findtext("key")
        term = element.findtext("term/de") or ""
        if key in _APPLICANT_KEYS and element.findtext("subject/selectType") == "legalPerson":
            if name := (element.findtext("subject/legalPerson/company/name") or "").strip():
                applicants.append(name)
        elif key == "parcel":
            location = shab.plain_text(element.findtext("valueText/term/de"))
        elif term == "Projektgemeinde":
            municipality = element.findtext("valueTextNeutral")
    return description, location, municipality, tuple(applicants)


def _address(address: Element | None) -> str | None:
    if address is None:
        return None
    street = " ".join(p for p in (address.findtext("street"), address.findtext("houseNumber")) if p)
    place = " ".join(p for p in (address.findtext("swissZipCode"), address.findtext("town")) if p)
    return ", ".join(p for p in (street, place) if p) or None


def _required(root: Element, path: str) -> str:
    value = root.findtext(path)
    if not value:
        raise ValueError(f"Permit notice is missing <{path}>")
    return value

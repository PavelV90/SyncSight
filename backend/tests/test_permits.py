import json
from datetime import date

import httpx2
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncsight.db.models import BuildingPermit, Company
from syncsight.ingestion import permits
from syncsight.ingestion.permits import PRODUCTION_WORDS, parse_permit

# Synthetic notices in the two Amtsblattportal formats. Fictional companies and places.
STRUCTURED = b"""<BP-BS10:publication xmlns:BP-BS10="https://amtsblattportal.ch/BP-BS10">
<meta><id>p1</id><subRubric>BP-BS10</subRubric><publicationNumber>BP-BS10-1</publicationNumber>
<publicationDate>2026-09-02</publicationDate><cantons>BS</cantons>
<title><de>Neu-, Um- und Anbauten: Werkstrasse 1, Basel</de></title></meta>
<content>
<localization><municipalityId><key>2701</key><term><de>Basel</de></term></municipalityId></localization>
<buildingContractor><legalEntity><selectType>company</selectType><multi><companies>
<company><name>Alpenpharma AG</name><legalForm>0106</legalForm></company>
</companies></multi></legalEntity></buildingContractor>
<projectDescription>Neubau Produktionsgeb&#228;ude (Bau 7)</projectDescription>
<projectLocation><address><street>Werkstrasse</street><houseNumber>1</houseNumber>
<swissZipCode>4058</swissZipCode><town>Basel</town></address></projectLocation>
</content></BP-BS10:publication>"""

BUSINESS_CASE = b"""<BA-VS05:publication xmlns:BA-VS05="https://amtsblattportal.ch/BA-VS05">
<meta><id>p2</id><subRubric>BA-VS05</subRubric><publicationNumber>BA-VS05-2</publicationNumber>
<publicationDate>2026-10-16</publicationDate><cantons>VS</cantons></meta>
<content>
<localization><municipalityId><key>6297</key><term><de>Visp</de></term></municipalityId></localization>
<businessCase><key>constructionProject</key>
<primary><element><valueText><term><de>Erweiterung Reinraum</de></term></valueText></element>
</primary>
<secondary>
<element><key>applicantParty</key><subject><selectType>legalPerson</selectType>
<legalPerson><company><name>Alpenpharma AG</name></company></legalPerson></subject></element>
<element><key>projectFramer</key><subject><selectType>naturalPerson</selectType>
<naturalPerson><firstName>Anna</firstName><officialName>Muster</officialName></naturalPerson>
</subject></element>
<element><key>parcel</key><valueText><term><de>Parzelle 12 - Rohrstrasse 5</de></term></valueText>
</element>
</secondary></businessCase>
</content></BA-VS05:publication>"""

PERSON_ONLY = BUSINESS_CASE.replace(b"<id>p2</id>", b"<id>p3</id>").replace(
    b"<selectType>legalPerson</selectType>\n<legalPerson><company><name>Alpenpharma AG</name>"
    b"</company></legalPerson>",
    b"<selectType>naturalPerson</selectType>\n<naturalPerson><officialName>Alpenpharma AG"
    b"</officialName></naturalPerson>",
)


def test_parses_structured_format() -> None:
    notice = parse_permit(STRUCTURED)

    assert notice.applicants == ("Alpenpharma AG",)
    assert notice.description == "Neubau Produktionsgebäude (Bau 7)"
    assert notice.location == "Werkstrasse 1, 4058 Basel"
    assert notice.municipality == "Basel"
    assert PRODUCTION_WORDS.search(notice.description or "")


def test_parses_business_case_format_and_skips_natural_persons() -> None:
    notice = parse_permit(BUSINESS_CASE)

    assert notice.applicants == ("Alpenpharma AG",)
    assert notice.description == "Erweiterung Reinraum"
    assert notice.location == "Parzelle 12 - Rohrstrasse 5"
    assert parse_permit(PERSON_ONLY).applicants == ()


def test_applicant_must_match_company_name() -> None:
    notice = parse_permit(STRUCTURED)

    assert permits.applicant_for(notice, "ALPENPHARMA AG") == "Alpenpharma AG"
    assert permits.applicant_for(notice, "Alpenpharma Holding AG") is None


@pytest.mark.db
def test_run_stores_only_notices_filed_by_the_company(db_session: Session) -> None:
    db_session.add(Company(uid="CHE-000.000.001", name="Alpenpharma AG", status="active"))
    notices = {"p1": STRUCTURED, "p2": BUSINESS_CASE, "p3": PERSON_ONLY}
    keywords: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/xml"):
            return httpx2.Response(200, content=notices[request.url.path.split("/")[-2]])
        keywords.append(request.url.params["keyword"])
        body = {"content": [{"meta": {"id": i}} for i in notices], "total": len(notices)}
        return httpx2.Response(200, text=json.dumps(body))

    client = httpx2.Client(transport=httpx2.MockTransport(handler))
    stored = permits.run(db_session, client, ["CHE-000.000.001"], since=date(2024, 10, 1), delay=0)

    assert stored == 2
    assert keywords == ["Alpenpharma AG"]
    rows = db_session.scalars(select(BuildingPermit).order_by(BuildingPermit.id)).all()
    assert [(r.id, r.description) for r in rows] == [
        ("p1", "Neubau Produktionsgebäude (Bau 7)"),
        ("p2", "Erweiterung Reinraum"),
    ]

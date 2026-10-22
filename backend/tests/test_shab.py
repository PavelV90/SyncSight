from datetime import date
from decimal import Decimal

import pytest

from syncsight.ingestion.shab import parse_notice
from tests.conftest import FIXTURES_DIR


def test_parses_capital_increase_notice() -> None:
    notice = parse_notice((FIXTURES_DIR / "shab_hr02_capital_increase.xml").read_bytes())

    assert notice.publication_number == "HR02-0000000001"
    assert notice.publication_date == date(2026, 10, 22)
    assert notice.sub_rubric == "HR02"
    assert notice.company_uid == "CHE-000.000.001"
    assert notice.company_name == "Beispiel Pharma AG"
    assert notice.capital_nominal == Decimal("500000.00")
    assert notice.changes == {"capital"}


def test_rejects_notice_without_publication_number() -> None:
    with pytest.raises(ValueError, match="publicationNumber"):
        parse_notice(b"<publication><meta/></publication>")

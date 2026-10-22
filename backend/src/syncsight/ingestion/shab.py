"""Parser for SHAB/SOGC commercial-register notices (Amtsblattportal XML export).

Source: https://www.amtsblattportal.ch/api/v1/publications/{id}/xml
Only structured change flags are read here; board and management changes live in
the free-text part of the notice and are parsed separately.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

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


@dataclass(frozen=True)
class ShabNotice:
    publication_number: str
    publication_date: date
    sub_rubric: str
    company_uid: str | None
    company_name: str | None
    capital_nominal: Decimal | None
    changes: frozenset[str]


def parse_notice(xml: bytes) -> ShabNotice:
    root = ElementTree.fromstring(xml)
    company = root.find("content/commonsNew/company")
    capital = root.findtext("content/commonsNew/capital/nominal")
    return ShabNotice(
        publication_number=_required(root, "meta/publicationNumber"),
        publication_date=date.fromisoformat(_required(root, "meta/publicationDate")),
        sub_rubric=_required(root, "meta/subRubric"),
        company_uid=company.findtext("uid") if company is not None else None,
        company_name=company.findtext("name") if company is not None else None,
        capital_nominal=Decimal(capital) if capital else None,
        changes=_changes(root.find("content/transaction/update/changements")),
    )


def _changes(changements: Element | None) -> frozenset[str]:
    if changements is None:
        return frozenset()
    found = {label for tag, label in _SIMPLE_FLAGS.items() if _any_true(changements.find(tag))}
    found |= {label for path, label in _NESTED_FLAGS.items() if _any_true(changements.find(path))}
    return frozenset(found)


def _any_true(element: Element | None) -> bool:
    return element is not None and any((e.text or "").strip() == "true" for e in element.iter())


def _required(root: Element, path: str) -> str:
    value = root.findtext(path)
    if not value:
        raise ValueError(f"SHAB notice is missing <{path}>")
    return value

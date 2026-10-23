"""Link records without a UID to companies by normalised name (postal code breaks ties)."""

from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from syncsight.db.models import Company

NameAndPlace = tuple[str, str | None]  # (name key, postal code)


def link_by_name(session: Session, holders: Iterable[NameAndPlace]) -> dict[NameAndPlace, str]:
    """UID for each (name key, postal code) that identifies exactly one active company."""
    holders = set(holders)
    candidates: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    for uid, key, postal_code in session.execute(
        select(Company.uid, Company.name_key, Company.postal_code).where(
            Company.name_key.in_({key for key, _ in holders}), Company.status == "active"
        )
    ):
        if key:
            candidates[key].append((uid, postal_code))
    links = {}
    for key, postal_code in holders:
        match = _pick(candidates.get(key, []), postal_code)
        if match:
            links[(key, postal_code)] = match
    return links


def _pick(candidates: list[tuple[str, str | None]], postal_code: str | None) -> str | None:
    if len(candidates) == 1:
        return candidates[0][0]
    same_place = [uid for uid, plz in candidates if plz and plz == postal_code]
    return same_place[0] if len(same_place) == 1 else None

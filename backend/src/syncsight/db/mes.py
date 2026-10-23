"""MES leads: licensed manufacturers ranked by transparent, capped signal points.

Every point is backed by one piece of evidence with a date and a source link, so a
consultant can check why a company ranks where it does.
"""

from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from syncsight.db.models import (
    BuildingPermit,
    Company,
    Medicine,
    SogcNotice,
    SwissmedicSite,
    SwissmedicSiteChange,
    WebHit,
)
from syncsight.db.queries import investment_targets_raises
from syncsight.ingestion.permits import is_production
from syncsight.ingestion.shab import PUBLIC_URL

MES_ACTIVITIES = (1, 3)  # manufacturing, API manufacturing
# signal kind -> (points per item, max items counted)
POINTS = {
    "web_mes": (3, 1),
    "web_hiring": (2, 1),
    "web_vendor": (2, 1),
    "permit_production": (3, 2),
    "permit_other": (1, 1),
    "licence_change": (2, 2),
    "web_expansion": (1, 1),
    "web_digital": (1, 1),
    "management_change": (1, 1),
    "capital_raise": (1, 1),
    "new_medicine": (1, 1),
}


@dataclass(frozen=True)
class Evidence:
    kind: str
    on: date | None
    title: str
    detail: str | None = None
    url: str | None = None


@dataclass
class MesLead:
    company: Company
    site_cantons: list[str]
    activity_codes: list[int]
    evidence: list[Evidence] = field(default_factory=list)
    vendors: set[str] = field(default_factory=set)

    @property
    def score(self) -> int:
        counts: dict[str, int] = defaultdict(int)
        for item in self.evidence:
            counts[item.kind] += 1
        return sum(POINTS[kind][0] * min(count, POINTS[kind][1]) for kind, count in counts.items())


def mes_leads(
    session: Session,
    *,
    months: int = 24,
    cantons: Collection[str] = (),
    min_score: int = 1,
) -> list[MesLead]:
    since = date.today() - timedelta(days=round(months * 30.44))
    leads = _targets(session, cantons)
    uids = list(leads)

    for permit in session.scalars(
        select(BuildingPermit).where(
            BuildingPermit.company_uid.in_(uids), BuildingPermit.publication_date >= since
        )
    ):
        production = is_production(permit.description)
        leads[permit.company_uid].evidence.append(
            Evidence(
                "permit_production" if production else "permit_other",
                permit.publication_date,
                f"Building permit: {permit.description}",
                ", ".join(p for p in (permit.location, permit.municipality) if p),
                PUBLIC_URL.format(id=permit.id),
            )
        )
    for change in session.scalars(
        select(SwissmedicSiteChange).where(
            SwissmedicSiteChange.company_uid.in_(uids),
            SwissmedicSiteChange.detected_on >= since,
            SwissmedicSiteChange.kind.in_(["site_added", "activity_added", "compliance_changed"]),
        )
    ):
        title = f"Swissmedic licence: {change.kind.replace('_', ' ')}"
        leads[change.company_uid or ""].evidence.append(
            Evidence("licence_change", change.detected_on, title, change.detail)
        )
    for uid, count, latest, names in session.execute(
        select(
            Medicine.company_uid,
            func.count(),
            func.max(Medicine.first_authorised_on),
            func.string_agg(Medicine.product_name, "; "),
        )
        .where(Medicine.company_uid.in_(uids), Medicine.first_authorised_on >= since)
        .group_by(Medicine.company_uid)
    ):
        leads[uid].evidence.append(
            Evidence("new_medicine", latest, f"{count} new medicine authorisation(s)", names[:300])
        )
    for notice in session.scalars(
        select(SogcNotice).where(
            SogcNotice.company_uid.in_(uids),
            SogcNotice.publication_date >= date.today() - timedelta(days=365),
            SogcNotice.changes.overlap(["board", "management"]),
        )
    ):
        roles = " and ".join(c for c in ("board", "management") if c in notice.changes)
        leads[notice.company_uid or ""].evidence.append(
            Evidence(
                "management_change", notice.publication_date, f"Register: {roles} change",
                url=PUBLIC_URL.format(id=notice.id),
            )
        )  # fmt: skip
    for uid, raised_on, before, after, notice_id in investment_targets_raises(session, uids, since):
        leads[uid].evidence.append(
            Evidence(
                "capital_raise", raised_on, "Register: capital increase",
                f"CHF {before:,.0f} → {after:,.0f}".replace(",", "'"),
                PUBLIC_URL.format(id=notice_id),
            )
        )  # fmt: skip
    for hit in session.scalars(select(WebHit).where(WebHit.company_uid.in_(uids))):
        if hit.published_on and hit.published_on < since:
            continue
        lead = leads[hit.company_uid]
        vendors = [k.split(":", 1)[1] for k in hit.keywords if k.startswith("vendor:")]
        lead.vendors.update(vendors)
        title = hit.title or hit.url
        for kind, applies in (
            ("web_hiring", hit.kind == "career" and ("mes" in hit.keywords or bool(vendors))),
            ("web_mes", "mes" in hit.keywords),
            ("web_vendor", bool(vendors)),
            ("web_expansion", "expansion" in hit.keywords),
            ("web_digital", "digital" in hit.keywords),
        ):
            if applies:
                lead.evidence.append(Evidence(kind, hit.published_on, title, hit.snippet, hit.url))

    ranked = [lead for lead in leads.values() if lead.score >= min_score]
    for lead in ranked:
        lead.evidence.sort(key=lambda e: e.on or date.min, reverse=True)
    return sorted(ranked, key=lambda lead: (lead.score, _latest(lead)), reverse=True)


def _targets(session: Session, cantons: Collection[str]) -> dict[str, MesLead]:
    query = select(SwissmedicSite).where(
        SwissmedicSite.company_uid.is_not(None),
        SwissmedicSite.activity_codes.overlap(list(MES_ACTIVITIES)),
    )
    if cantons:
        query = query.where(SwissmedicSite.site_canton.in_(cantons))
    sites: dict[str, list[SwissmedicSite]] = defaultdict(list)
    for site in session.scalars(query):
        sites[site.company_uid or ""].append(site)
    companies = session.scalars(select(Company).where(Company.uid.in_(list(sites))))
    return {
        c.uid: MesLead(
            c,
            sorted({s.site_canton for s in sites[c.uid] if s.site_canton}),
            sorted({code for s in sites[c.uid] for code in s.activity_codes}),
        )
        for c in companies
    }


def _latest(lead: MesLead) -> date:
    return max((e.on for e in lead.evidence if e.on), default=date.min)
